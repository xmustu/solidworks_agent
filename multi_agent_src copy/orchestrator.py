from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Callable
from typing import Any

try:
    from .agents import (
        AssemblyAgent,
        AssemblyPlanningAgent,
        PartModelingAgent,
        PartValidationAgent,
        RequirementAgent,
        extract_json_payload,
        extract_python_code,
    )
    from .config import AGENT_OUTPUT_ROOT
    from .executor import (
        execute_python_code,
        run_assembly_plan_checks,
        run_part_plan_checks,
    )
except ImportError:
    from agents import (
        AssemblyAgent,
        AssemblyPlanningAgent,
        PartModelingAgent,
        PartValidationAgent,
        RequirementAgent,
        extract_json_payload,
        extract_python_code,
    )
    from config import AGENT_OUTPUT_ROOT
    from executor import execute_python_code, run_assembly_plan_checks, run_part_plan_checks


def slugify(value: str, fallback: str) -> str:
    value = value.strip()
    value = re.sub(r"[^\w\-]+", "_", value, flags=re.UNICODE)
    value = re.sub(r"_+", "_", value).strip("_")
    return value or fallback


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class MultiAgentOrchestrator:
    def __init__(self, event_callback: Callable[[dict[str, Any]], None] | None = None) -> None:
        self.requirement_agent = RequirementAgent()
        self.assembly_planning_agent = AssemblyPlanningAgent()
        self.assembly_agent = AssemblyAgent()
        self.event_callback = event_callback

    def emit_event(self, event_type: str, **payload: Any) -> None:
        if self.event_callback is None:
            return
        event = {"type": event_type, **payload}
        self.event_callback(event)

    def emit_status(self, message: str) -> None:
        self.emit_event("status", message=message)

    def run_agent(self, agent_name: str, agent: Any, prompt: str) -> str:
        if self.event_callback is None:
            return agent.chat(prompt)

        self.emit_event("message_start", role="agent", agent_name=agent_name)
        for chunk in agent.stream_chat(prompt):
            self.emit_event("delta", content=chunk)
        self.emit_event("message_end")
        return agent.history[-1]["content"]

    def run(self) -> None:
        print("=== 多智能体 CAD 设计系统 ===")
        requirement_payload = self.collect_requirements()
        self.process_confirmed_requirement(requirement_payload)

    def process_confirmed_requirement(self, requirement_payload: dict[str, Any]) -> None:
        request_type = str(requirement_payload.get("request_type", "")).strip().lower()

        if request_type == "part":
            self.handle_part_request(requirement_payload)
            return

        if request_type == "assembly":
            self.handle_assembly_request(requirement_payload)
            return

        raise ValueError(f"Unsupported request_type: {request_type}")

    def collect_requirements(self) -> dict[str, Any]:
        print("\n[阶段 1] 需求分析（输入 'quit' 退出）")
        user_input = input("请输入您的设计需求：\n>> ").strip()

        while True:
            if user_input.lower() in {"quit", "exit"}:
                raise SystemExit(0)

            reply = self.run_agent("RequirementAgent", self.requirement_agent, user_input)
            print(f"\n[需求分析 Agent]\n{reply}\n")

            if "[CONFIRMED]" in reply:
                payload = extract_json_payload(reply)
                print(f">>> 已确认需求类型: {payload.get('request_type')}")
                return payload

            user_input = input(">> ").strip()

    def handle_part_request(self, requirement_payload: dict[str, Any]) -> None:
        workspace = self.create_single_part_workspace(requirement_payload)
        plan = self.build_single_part_plan(requirement_payload, workspace)
        write_json(Path(plan["workspace"]["plan_file"]), plan)

        print("\n[阶段 2] 单零件建模")
        self.emit_status("[阶段 2] 单零件建模")
        success = self.run_part_pipeline(
            full_plan=plan,
            part_spec=plan["part"],
            enable_static_validation=False,
        )
        if success:
            print("\n=== 单零件需求执行完成 ===")
        else:
            print("\n=== 单零件需求执行失败，请根据日志调整需求或知识库 ===")

    def handle_assembly_request(self, requirement_payload: dict[str, Any]) -> None:
        workspace = self.create_assembly_workspace(requirement_payload)
        print("\n[阶段 2] 装配规划")
        self.emit_status("[阶段 2] 装配规划")
        plan = self.generate_assembly_plan(requirement_payload, workspace)

        print("\n[阶段 3] 零件建模分发")
        self.emit_status("[阶段 3] 零件建模分发")
        part_results: list[dict[str, Any]] = []
        for index, part_spec in enumerate(plan["assembly"]["parts"], start=1):
            print(f"\n  -> 零件 {index}/{len(plan['assembly']['parts'])}: {part_spec['name']}")
            self.emit_status(f"[零件 {index}/{len(plan['assembly']['parts'])}] {part_spec['name']}")
            success = self.run_part_pipeline(
                full_plan=plan,
                part_spec=part_spec,
                enable_static_validation=True,
            )
            part_results.append(
                {
                    "part_id": part_spec["part_id"],
                    "name": part_spec["name"],
                    "success": success,
                    "model_file": part_spec["workspace"]["model_file"],
                }
            )
            if not success:
                print("\n=== 零件建模未全部完成，停止装配阶段 ===")
                return

        print("\n[阶段 4] 装配生成与执行")
        self.emit_status("[阶段 4] 装配生成与执行")
        assembly_success = self.run_assembly_pipeline(plan, part_results)
        if assembly_success:
            print("\n=== 装配需求执行完成 ===")
        else:
            print("\n=== 装配阶段失败，请查看输出目录日志 ===")

    def create_single_part_workspace(self, requirement_payload: dict[str, Any]) -> dict[str, str]:
        name = slugify(requirement_payload.get("name", "part"), "part")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        root_dir = AGENT_OUTPUT_ROOT / f"{name}-{timestamp}"
        part_dir = root_dir / "part"
        json_dir = root_dir / "json"
        logs_dir = root_dir / "logs"

        for directory in (root_dir, part_dir, json_dir, logs_dir):
            directory.mkdir(parents=True, exist_ok=True)

        return {
            "root_dir": str(root_dir),
            "part_dir": str(part_dir),
            "json_dir": str(json_dir),
            "logs_dir": str(logs_dir),
        }

    def build_single_part_plan(
        self,
        requirement_payload: dict[str, Any],
        workspace: dict[str, str],
    ) -> dict[str, Any]:
        part_id = slugify(requirement_payload.get("name", "part"), "part")
        part_name = requirement_payload.get("name", "Part")
        part_dir = Path(workspace["part_dir"])
        plan = {
            "request_type": "part",
            "name": part_name,
            "summary": requirement_payload.get("summary", ""),
            "key_requirements": requirement_payload.get("key_requirements", []),
            "assumptions": requirement_payload.get("assumptions", []),
            "requested_outputs": requirement_payload.get("requested_outputs", []),
            "interfaces": requirement_payload.get("interfaces", []),
            "workspace": {
                **workspace,
                "plan_file": str(Path(workspace["json_dir"]) / "part_request.json"),
            },
            "part": {
                "part_id": part_id,
                "name": part_name,
                "function": requirement_payload.get("summary", ""),
                "shape": "根据需求分析结果由建模智能体细化",
                "key_dimensions": requirement_payload.get("key_requirements", []),
                "material_or_notes": "; ".join(requirement_payload.get("assumptions", [])),
                "interfaces": {
                    "faces": [],
                    "axes": [],
                    "points": [],
                },
                "standalone_modeling_instructions": requirement_payload.get("key_requirements", []),
                "workspace": {
                    "part_dir": str(part_dir),
                    "code_file": str(part_dir / f"{part_id}_model.py"),
                    "model_file": str(part_dir / f"{part_id}.SLDPRT"),
                    "log_file": str(Path(workspace["logs_dir"]) / f"{part_id}_model.log"),
                    "spec_file": str(Path(workspace["json_dir"]) / f"{part_id}_spec.json"),
                },
            },
        }
        write_json(
            Path(plan["part"]["workspace"]["spec_file"]),
            {
                "request_type": "part",
                "part_context": {
                    "name": plan["name"],
                    "summary": plan["summary"],
                    "key_requirements": plan["key_requirements"],
                    "assumptions": plan["assumptions"],
                    "requested_outputs": plan["requested_outputs"],
                    "interfaces": plan["interfaces"],
                },
                "part": plan["part"],
            },
        )
        return plan

    def create_assembly_workspace(self, requirement_payload: dict[str, Any]) -> dict[str, str]:
        assembly_name = slugify(requirement_payload.get("name", "assembly"), "assembly")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        root_dir = AGENT_OUTPUT_ROOT / f"{assembly_name}-{timestamp}"
        parts_dir = root_dir / "parts"
        assembly_dir = root_dir / "assembly"
        json_dir = root_dir / "json"
        logs_dir = root_dir / "logs"

        for directory in (root_dir, parts_dir, assembly_dir, json_dir, logs_dir):
            directory.mkdir(parents=True, exist_ok=True)

        return {
            "root_dir": str(root_dir),
            "parts_dir": str(parts_dir),
            "assembly_dir": str(assembly_dir),
            "json_dir": str(json_dir),
            "logs_dir": str(logs_dir),
        }

    def generate_assembly_plan(
        self,
        requirement_payload: dict[str, Any],
        workspace: dict[str, str],
    ) -> dict[str, Any]:
        prompt = self.build_assembly_plan_prompt(requirement_payload, workspace)
        current_prompt = prompt

        for attempt in range(1, 4):
            print(f"  [装配规划尝试 {attempt}/3] 生成装配规划 JSON")
            self.emit_status(f"[装配规划尝试 {attempt}/3] 生成装配规划 JSON")
            response = self.run_agent("AssemblyPlanningAgent", self.assembly_planning_agent, current_prompt)

            try:
                plan = extract_json_payload(response)
            except ValueError:
                current_prompt = self.build_assembly_plan_retry_prompt(
                    requirement_payload=requirement_payload,
                    workspace=workspace,
                    model_response=response,
                    validation_errors=[
                        "上一次输出不是可严格解析的 JSON。",
                        "请只输出一个合法 JSON 对象，不要附带解释、前后缀、Markdown 说明或多余文本。",
                    ],
                )
                continue

            validation_errors = self.validate_assembly_plan_payload(plan)
            if validation_errors:
                current_prompt = self.build_assembly_plan_retry_prompt(
                    requirement_payload=requirement_payload,
                    workspace=workspace,
                    model_response=response,
                    validation_errors=validation_errors,
                )
                continue

            plan = self.enrich_assembly_plan(plan, workspace)
            write_json(Path(plan["assembly"]["workspace"]["plan_file"]), plan)
            return plan

        raise ValueError("AssemblyPlanningAgent failed to return a valid assembly planning JSON after retries.")

    def build_assembly_plan_prompt(
        self,
        requirement_payload: dict[str, Any],
        workspace: dict[str, str],
    ) -> str:
        assembly_output = {
            "code_file": str(Path(workspace["assembly_dir"]) / "assembly_build.py"),
            "model_file": str(
                Path(workspace["assembly_dir"])
                / f"{slugify(requirement_payload.get('name', 'assembly'), 'assembly')}.SLDASM"
            ),
            "log_file": str(Path(workspace["logs_dir"]) / "assembly.log"),
        }

        return (
            "请根据下面的装配需求和预先创建好的工作空间，直接输出严格合法的 JSON 装配规划。\n\n"
            "【已确认的装配需求】\n"
            f"{json.dumps(requirement_payload, ensure_ascii=False, indent=2)}\n\n"
            "【预先创建的工作空间】\n"
            f"{json.dumps({**workspace, 'plan_file': str(Path(workspace['json_dir']) / 'assembly_plan.json'), 'assembly_output': assembly_output}, ensure_ascii=False, indent=2)}\n\n"
            "要求：\n"
            "1. 输入即使不是标准 JSON 语义，也要正常分析并完成规划。\n"
            "2. 输出必须是一个可直接被 json.loads 解析的 JSON 对象。\n"
            "3. 如果装配中存在多个相同零件，`parts` 中只保留唯一零件定义，通过 `instances` 表达多个实例；不要把重复件展开成多个重复 part。\n"
            "4. 相同几何但接口用途不同的实例，仍然优先复用同一个 part，并在实例层写清接口使用方式。\n"
            "5. 不要输出解释、标题、注释、Markdown 代码块或额外文本。\n"
            "6. 输出前请自行检查 JSON 合法性和字段完整性。\n"
        )

    def build_assembly_plan_retry_prompt(
        self,
        requirement_payload: dict[str, Any],
        workspace: dict[str, str],
        model_response: str,
        validation_errors: list[str],
    ) -> str:
        return (
            self.build_assembly_plan_prompt(requirement_payload, workspace)
            + "\n【上一次输出】\n"
            + model_response
            + "\n\n【必须修复的问题】\n- "
            + "\n- ".join(validation_errors)
            + "\n\n请基于同一需求重新输出完整 JSON，且只输出最终 JSON。"
        )

    def validate_assembly_plan_payload(self, plan: dict[str, Any]) -> list[str]:
        issues: list[str] = []

        if not isinstance(plan, dict):
            return ["顶层输出必须是 JSON 对象。"]

        if plan.get("request_type") != "assembly":
            issues.append("顶层字段 `request_type` 必须是 `assembly`。")

        assembly = plan.get("assembly")
        if not isinstance(assembly, dict):
            issues.append("必须包含对象类型的 `assembly` 字段。")
            return issues

        required_assembly_fields = [
            "name",
            "summary",
            "workspace",
            "global_coordinate_system",
            "design_rules",
            "parts",
            "instances",
            "assembly_sequence",
            "constraints",
            "assembly_output",
        ]
        for field in required_assembly_fields:
            if field not in assembly:
                issues.append(f"`assembly.{field}` 缺失。")

        parts = assembly.get("parts")
        part_ids: set[str] = set()
        if not isinstance(parts, list) or not parts:
            issues.append("`assembly.parts` 必须是非空数组。")
        else:
            required_part_fields = [
                "part_id",
                "name",
                "function",
                "shape",
                "key_dimensions",
                "material_or_notes",
                "quantity",
                "instance_ids",
                "interfaces",
                "assembly_relation_notes",
                "workspace",
                "standalone_modeling_instructions",
            ]
            for index, part in enumerate(parts, start=1):
                if not isinstance(part, dict):
                    issues.append(f"`assembly.parts[{index}]` 必须是对象。")
                    continue

                for field in required_part_fields:
                    if field not in part:
                        issues.append(f"`assembly.parts[{index}].{field}` 缺失。")

                part_id = part.get("part_id")
                if isinstance(part_id, str) and part_id:
                    if part_id in part_ids:
                        issues.append(f"`assembly.parts[{index}].part_id` 重复：{part_id}")
                    part_ids.add(part_id)

                interfaces = part.get("interfaces", {})
                if not isinstance(interfaces, dict):
                    issues.append(f"`assembly.parts[{index}].interfaces` 必须是对象。")
                else:
                    for key in ("faces", "axes", "points"):
                        if key not in interfaces:
                            issues.append(f"`assembly.parts[{index}].interfaces.{key}` 缺失。")
                        elif not isinstance(interfaces.get(key), list):
                            issues.append(f"`assembly.parts[{index}].interfaces.{key}` 必须是数组。")

                if "quantity" in part and not isinstance(part.get("quantity"), int):
                    issues.append(f"`assembly.parts[{index}].quantity` 必须是整数。")

                if "instance_ids" in part and not isinstance(part.get("instance_ids"), list):
                    issues.append(f"`assembly.parts[{index}].instance_ids` 必须是数组。")

        instances = assembly.get("instances")
        instance_ids: set[str] = set()
        instances_by_part: dict[str, list[str]] = {}
        if not isinstance(instances, list) or not instances:
            issues.append("`assembly.instances` 必须是非空数组。")
        else:
            required_instance_fields = [
                "instance_id",
                "part_id",
                "name",
                "instance_role",
                "placement_notes",
                "interface_usage",
            ]
            for index, instance in enumerate(instances, start=1):
                if not isinstance(instance, dict):
                    issues.append(f"`assembly.instances[{index}]` 必须是对象。")
                    continue

                for field in required_instance_fields:
                    if field not in instance:
                        issues.append(f"`assembly.instances[{index}].{field}` 缺失。")

                instance_id = instance.get("instance_id")
                if isinstance(instance_id, str) and instance_id:
                    if instance_id in instance_ids:
                        issues.append(f"`assembly.instances[{index}].instance_id` 重复：{instance_id}")
                    instance_ids.add(instance_id)

                part_id = instance.get("part_id")
                if isinstance(part_id, str) and part_id:
                    if part_ids and part_id not in part_ids:
                        issues.append(f"`assembly.instances[{index}].part_id` 未在 `assembly.parts` 中定义：{part_id}")
                    if isinstance(instance_id, str) and instance_id:
                        instances_by_part.setdefault(part_id, []).append(instance_id)

                interface_usage = instance.get("interface_usage", {})
                if not isinstance(interface_usage, dict):
                    issues.append(f"`assembly.instances[{index}].interface_usage` 必须是对象。")
                else:
                    for key in ("faces", "axes", "points"):
                        if key not in interface_usage:
                            issues.append(f"`assembly.instances[{index}].interface_usage.{key}` 缺失。")
                        elif not isinstance(interface_usage.get(key), list):
                            issues.append(f"`assembly.instances[{index}].interface_usage.{key}` 必须是数组。")

            for index, part in enumerate(parts or [], start=1):
                part_id = part.get("part_id")
                declared_instance_ids = part.get("instance_ids", [])
                if isinstance(part_id, str) and isinstance(declared_instance_ids, list):
                    actual_instance_ids = instances_by_part.get(part_id, [])
                    if set(declared_instance_ids) != set(actual_instance_ids):
                        issues.append(
                            f"`assembly.parts[{index}].instance_ids` 与 `assembly.instances` 中引用该 part 的实例不一致。"
                        )
                    quantity = part.get("quantity")
                    if isinstance(quantity, int) and quantity != len(actual_instance_ids):
                        issues.append(
                            f"`assembly.parts[{index}].quantity` 应等于该 part 对应的实例数量 {len(actual_instance_ids)}。"
                        )

        constraints = assembly.get("constraints")
        if constraints is not None and not isinstance(constraints, list):
            issues.append("`assembly.constraints` 必须是数组。")
        elif isinstance(constraints, list):
            required_constraint_fields = [
                "source_instance_id",
                "source_part_id",
                "source_interface",
                "target_instance_id",
                "target_part_id",
                "target_interface",
                "relation",
                "alignment",
                "offset_mm",
                "notes",
            ]
            for index, constraint in enumerate(constraints, start=1):
                if not isinstance(constraint, dict):
                    issues.append(f"`assembly.constraints[{index}]` 必须是对象。")
                    continue
                for field in required_constraint_fields:
                    if field not in constraint:
                        issues.append(f"`assembly.constraints[{index}].{field}` 缺失。")
                source_instance_id = constraint.get("source_instance_id")
                if source_instance_id not in instance_ids:
                    issues.append(f"`assembly.constraints[{index}].source_instance_id` 未在 `assembly.instances` 中定义。")
                target_instance_id = constraint.get("target_instance_id")
                if target_instance_id != "GROUND" and target_instance_id not in instance_ids:
                    issues.append(f"`assembly.constraints[{index}].target_instance_id` 未在 `assembly.instances` 中定义。")

        sequence = assembly.get("assembly_sequence")
        if sequence is not None and not isinstance(sequence, list):
            issues.append("`assembly.assembly_sequence` 必须是数组。")

        design_rules = assembly.get("design_rules")
        if design_rules is not None and not isinstance(design_rules, list):
            issues.append("`assembly.design_rules` 必须是数组。")

        global_coordinate_system = assembly.get("global_coordinate_system")
        if global_coordinate_system is not None and not isinstance(global_coordinate_system, dict):
            issues.append("`assembly.global_coordinate_system` 必须是对象。")

        return issues

    def enrich_assembly_plan(self, plan: dict[str, Any], workspace: dict[str, str]) -> dict[str, Any]:
        if plan.get("request_type") != "assembly":
            raise ValueError("AssemblyPlanningAgent returned a non-assembly plan.")

        assembly = plan.setdefault("assembly", {})
        assembly_name = slugify(assembly.get("name", "assembly"), "assembly")
        assembly_workspace = {
            **workspace,
            "plan_file": str(Path(workspace["json_dir"]) / "assembly_plan.json"),
        }
        assembly["workspace"] = assembly_workspace
        assembly.setdefault("summary", "")
        assembly.setdefault("global_coordinate_system", {})
        assembly.setdefault("design_rules", [])
        assembly.setdefault("instances", [])
        assembly.setdefault("assembly_sequence", [])
        assembly.setdefault("constraints", [])
        assembly["assembly_output"] = {
            "code_file": str(Path(workspace["assembly_dir"]) / "assembly_build.py"),
            "model_file": str(Path(workspace["assembly_dir"]) / f"{assembly_name}.SLDASM"),
            "log_file": str(Path(workspace["logs_dir"]) / "assembly.log"),
        }

        part_specs = assembly.get("parts", [])
        existing_instances = assembly.get("instances", [])
        instance_map: dict[str, list[dict[str, Any]]] = {}
        for instance in existing_instances:
            if not isinstance(instance, dict):
                continue
            instance_id = slugify(instance.get("instance_id") or instance.get("name", "instance"), "instance")
            part_id = slugify(instance.get("part_id", "part"), "part")
            instance["instance_id"] = instance_id
            instance["part_id"] = part_id
            interface_usage = instance.get("interface_usage")
            if not isinstance(interface_usage, dict):
                interface_usage = {}
            instance["interface_usage"] = {
                "faces": list(interface_usage.get("faces", []) or []),
                "axes": list(interface_usage.get("axes", []) or []),
                "points": list(interface_usage.get("points", []) or []),
            }
            instance_map.setdefault(part_id, []).append(instance)

        for part in part_specs:
            part_id = slugify(part.get("part_id") or part.get("name", "part"), "part")
            part_name = part.get("name", part_id)
            part_dir = Path(workspace["parts_dir"]) / part_id
            part_dir.mkdir(parents=True, exist_ok=True)

            part_workspace = {
                "part_dir": str(part_dir),
                "code_file": str(part_dir / f"{part_id}_model.py"),
                "model_file": str(part_dir / f"{part_id}.SLDPRT"),
                "log_file": str(Path(workspace["logs_dir"]) / f"{part_id}_model.log"),
                "spec_file": str(Path(workspace["json_dir"]) / f"{part_id}_spec.json"),
            }
            part["part_id"] = part_id
            part["name"] = part_name
            part_instances = instance_map.get(part_id, [])
            fallback_instance_ids = part.get("instance_ids", [])
            if not isinstance(fallback_instance_ids, list):
                fallback_instance_ids = []
            normalized_instance_ids = [
                slugify(instance_id, f"{part_id}_instance") for instance_id in fallback_instance_ids if instance_id
            ]
            if not part_instances and normalized_instance_ids:
                part_instances = [
                    {
                        "instance_id": instance_id,
                        "part_id": part_id,
                        "name": instance_id,
                        "instance_role": f"{part_name} 实例",
                        "placement_notes": "",
                        "interface_usage": {"faces": [], "axes": [], "points": []},
                    }
                    for instance_id in normalized_instance_ids
                ]
                instance_map[part_id] = part_instances
            part["quantity"] = int(part.get("quantity") or max(len(part_instances), 1))
            part["instance_ids"] = [instance["instance_id"] for instance in part_instances] or normalized_instance_ids or [part_id]
            part["workspace"] = part_workspace
            part["interfaces"] = part.get("interfaces", {"faces": [], "axes": [], "points": []})
            part["standalone_modeling_instructions"] = part.get("standalone_modeling_instructions", [])
            write_json(
                Path(part_workspace["spec_file"]),
                {
                    "request_type": "assembly_part",
                    "assembly_context": {
                        "name": assembly.get("name", ""),
                        "summary": assembly.get("summary", ""),
                        "global_coordinate_system": assembly.get("global_coordinate_system", {}),
                        "design_rules": assembly.get("design_rules", []),
                        "instances": part_instances,
                        "assembly_sequence": assembly.get("assembly_sequence", []),
                    },
                    "part": part,
                },
            )

        if not assembly["instances"]:
            synthesized_instances: list[dict[str, Any]] = []
            for part in part_specs:
                for instance_id in part.get("instance_ids", []) or []:
                    synthesized_instances.append(
                        {
                            "instance_id": instance_id,
                            "part_id": part["part_id"],
                            "name": instance_id,
                            "instance_role": f"{part['name']} 实例",
                            "placement_notes": "",
                            "interface_usage": {"faces": [], "axes": [], "points": []},
                        }
                    )
            assembly["instances"] = synthesized_instances

        return plan

    def run_part_pipeline(
        self,
        full_plan: dict[str, Any],
        part_spec: dict[str, Any],
        enable_static_validation: bool,
        max_retries: int = 3,
    ) -> bool:
        part_agent = PartModelingAgent()
        validation_agent = PartValidationAgent() if enable_static_validation else None

        current_prompt = self.build_part_prompt(full_plan, part_spec, None)
        for attempt in range(1, max_retries + 1):
            print(f"    [建模尝试 {attempt}/{max_retries}] 生成 {part_spec['name']} 代码")
            self.emit_status(f"[建模尝试 {attempt}/{max_retries}] 生成 {part_spec['name']} 代码")
            response = self.run_agent("PartModelingAgent", part_agent, current_prompt)
            code = extract_python_code(response)

            workdir = Path(part_spec["workspace"]["part_dir"])
            script_name = Path(part_spec["workspace"]["code_file"]).name
            execution = execute_python_code(code, workdir=workdir, script_name=script_name)
            write_text(Path(part_spec["workspace"]["log_file"]), execution.log)
            self.emit_event("execution_log", title=f"{part_spec['name']} 执行日志", content=execution.log)

            if not execution.success:
                summary = execution.log.splitlines()[-1] if execution.log.splitlines() else execution.log
                print(f"    [执行失败] {summary}")
                self.emit_status(f"[执行失败] {summary}")
                current_prompt = self.build_part_prompt(full_plan, part_spec, execution.log)
                continue

            print("    [执行成功] 开始静态校验" if enable_static_validation else "    [执行成功] 动态校验通过")
            self.emit_status("    [执行成功] 开始静态校验" if enable_static_validation else "    [执行成功] 动态校验通过")
            if not enable_static_validation:
                return True

            deterministic_issues = run_part_plan_checks(full_plan, part_spec, code)
            validator_feedback = self.validate_part_code(
                validation_agent=validation_agent,
                full_plan=full_plan,
                part_spec=part_spec,
                code=code,
                deterministic_issues=deterministic_issues,
            )
            if validator_feedback["pass"]:
                print("    [静态校验通过]")
                self.emit_status("[静态校验通过]")
                return True

            feedback = validator_feedback.get("feedback", "静态校验未通过")
            print(f"    [静态校验失败] {feedback}")
            self.emit_status(f"[静态校验失败] {feedback}")
            current_prompt = self.build_part_prompt(full_plan, part_spec, feedback)

        return False

    def validate_part_code(
        self,
        validation_agent: PartValidationAgent | None,
        full_plan: dict[str, Any],
        part_spec: dict[str, Any],
        code: str,
        deterministic_issues: list[str],
    ) -> dict[str, Any]:
        if validation_agent is None:
            return {"pass": not deterministic_issues, "feedback": "; ".join(deterministic_issues)}

        prompt = json.dumps(
            {
                "full_plan": full_plan,
                "part_spec": part_spec,
                "generated_code": code,
                "deterministic_issues": deterministic_issues,
            },
            ensure_ascii=False,
            indent=2,
        )

        response = self.run_agent("PartValidationAgent", validation_agent, prompt)
        try:
            validation = extract_json_payload(response)
        except ValueError:
            validation = {
                "pass": False,
                "feedback": "静态校验 agent 未返回可解析 JSON，请重新生成并明确路径、接口和方向关系。",
            }

        hard_issues = [issue for issue in deterministic_issues if issue.startswith("HARD:")]
        soft_issues = [issue for issue in deterministic_issues if not issue.startswith("HARD:")]

        if hard_issues:
            merged_feedback = validation.get("feedback", "")
            validation["pass"] = False
            validation["feedback"] = "; ".join([*hard_issues, merged_feedback]).strip("; ")
            return validation

        if soft_issues:
            merged_feedback = validation.get("feedback", "")
            if validation.get("pass", False):
                validation["feedback"] = "; ".join([merged_feedback, *soft_issues]).strip("; ")
            else:
                validation["feedback"] = "; ".join([*soft_issues, merged_feedback]).strip("; ")
        return validation

    def build_part_prompt(
        self,
        full_plan: dict[str, Any],
        part_spec: dict[str, Any],
        retry_feedback: str | None,
    ) -> str:
        payload = {
            "task": "请为下面的零件生成完整可执行 Python 建模代码；如果该零件会被多个实例复用，也只建模一次通用零件模板。",
            "full_plan_summary": full_plan,
            "part_spec": part_spec,
        }
        if retry_feedback:
            payload["retry_feedback"] = retry_feedback
            payload["instruction"] = "请基于反馈完整重写代码，不要只给差异片段。"
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def run_assembly_pipeline(
        self,
        plan: dict[str, Any],
        part_results: list[dict[str, Any]],
        max_retries: int = 3,
    ) -> bool:
        current_prompt = self.build_assembly_prompt(plan, part_results, None)
        assembly_output = plan["assembly"]["assembly_output"]

        for attempt in range(1, max_retries + 1):
            print(f"  [装配尝试 {attempt}/{max_retries}] 生成装配代码")
            self.emit_status(f"[装配尝试 {attempt}/{max_retries}] 生成装配代码")
            response = self.run_agent("AssemblyAgent", self.assembly_agent, current_prompt)
            code = extract_python_code(response)

            workdir = Path(plan["assembly"]["workspace"]["assembly_dir"])
            script_name = Path(assembly_output["code_file"]).name
            execution = execute_python_code(code, workdir=workdir, script_name=script_name)
            write_text(Path(assembly_output["log_file"]), execution.log)
            self.emit_event("execution_log", title="装配执行日志", content=execution.log)

            if not execution.success:
                summary = execution.log.splitlines()[-1] if execution.log.splitlines() else execution.log
                print(f"  [装配执行失败] {summary}")
                self.emit_status(f"[装配执行失败] {summary}")
                current_prompt = self.build_assembly_prompt(plan, part_results, execution.log)
                continue

            issues = run_assembly_plan_checks(plan, code)
            if not issues:
                print("  [装配执行成功]")
                self.emit_status("[装配执行成功]")
                return True

            feedback = "; ".join(issues)
            print(f"  [装配静态检查失败] {feedback}")
            self.emit_status(f"[装配静态检查失败] {feedback}")
            current_prompt = self.build_assembly_prompt(plan, part_results, feedback)

        return False

    def build_assembly_prompt(
        self,
        plan: dict[str, Any],
        part_results: list[dict[str, Any]],
        retry_feedback: str | None,
    ) -> str:
        payload = {
            "task": "请根据装配规划和已完成的零件输出，生成完整可执行 Python 装配代码；对于重复件要复用同一个零件文件并按 instance_id 插入多个组件实例。",
            "assembly_plan": plan,
            "part_results": part_results,
        }
        if retry_feedback:
            payload["retry_feedback"] = retry_feedback
            payload["instruction"] = "请基于反馈完整重写装配代码，不要只给差异片段。"
        return json.dumps(payload, ensure_ascii=False, indent=2)
