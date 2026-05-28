from __future__ import annotations

import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Callable
from typing import Any
from uuid import uuid4

try:
    from .agent_tools import AgentToolExecutor
    from .agents import (
        AssemblyAgent,
        AssemblyPlanningAgent,
        AssemblyPlanReviewAgent,
        PartModelingAgent,
        PartValidationAgent,
        RequirementAgent,
        RequirementReviewAgent,
        extract_json_payload,
        extract_python_code,
    )
    from .config import AGENT_OUTPUT_ROOT
    from .executor import (
        execute_python_code,
        format_execution_failure_summary,
        run_assembly_plan_checks,
        run_part_plan_checks,
    )
    from .pipeline_state import DEFAULT_STATE_POLICIES, PipelineState, StatePolicy
except ImportError:
    from agent_tools import AgentToolExecutor
    from agents import (
        AssemblyAgent,
        AssemblyPlanningAgent,
        AssemblyPlanReviewAgent,
        PartModelingAgent,
        PartValidationAgent,
        RequirementAgent,
        RequirementReviewAgent,
        extract_json_payload,
        extract_python_code,
    )
    from config import AGENT_OUTPUT_ROOT
    from executor import (
        execute_python_code,
        format_execution_failure_summary,
        run_assembly_plan_checks,
        run_part_plan_checks,
    )


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
        self.requirement_review_agent = RequirementReviewAgent()
        self.assembly_planning_agent = AssemblyPlanningAgent()
        self.assembly_plan_review_agent = AssemblyPlanReviewAgent()
        self.assembly_agent = AssemblyAgent()
        self.event_callback = event_callback
        self.state_policies: dict[PipelineState, StatePolicy] = DEFAULT_STATE_POLICIES
        self.current_state = PipelineState.REQUIREMENT_CLARIFYING
        self.state_lock = threading.Lock()
        self.previous_attempts: dict[str, list[dict[str, Any]]] = {}
        self.previous_attempts_lock = threading.Lock()
        self.part_parallelism_limit = PART_PARALLELISM_LIMIT
        self.last_run_context: dict[str, Any] | None = None
        self.review_history: list[dict[str, Any]] = []

    def emit_event(self, event_type: str, **payload: Any) -> None:
        if self.event_callback is None:
            return
        event = {"type": event_type, **payload}
        self.event_callback(event)

    def emit_status(self, message: str) -> None:
        self.emit_event("status", message=message)

    def set_state(self, state: PipelineState, **context: Any) -> None:
        with self.state_lock:
            self.current_state = state
        policy = self.state_policies[state]
        self.emit_event(
            "state",
            state=state.value,
            inputs=list(policy.inputs),
            success_state=policy.success_state.value,
            failure_state=policy.failure_state.value,
            max_retries=policy.max_retries,
            fallback_state=policy.fallback_state.value if policy.fallback_state else None,
            context=context,
        )
        self.emit_status(f"[STATE] {state.value}")

    def run_agent(self, agent_name: str, agent: Any, prompt: str) -> str:
        if self.event_callback is None:
            return agent.chat(prompt)

        message_id = uuid4().hex
        self.emit_event("message_start", role="agent", agent_name=agent_name, message_id=message_id)
        for chunk in agent.stream_chat(prompt):
            self.emit_event("delta", content=chunk, message_id=message_id)
        self.emit_event("message_end", message_id=message_id)
        return agent.history[-1]["content"]

    def run_agent_with_tools(
        self,
        agent_name: str,
        agent: Any,
        prompt: str,
        tool_executor: AgentToolExecutor,
        max_tool_steps: int = 8,
    ) -> str:
        current_prompt = prompt
        latest_response = ""

        for step in range(1, max_tool_steps + 1):
            latest_response = self.run_agent(agent_name, agent, current_prompt)
            action = self.extract_tool_action(latest_response)
            if action is None:
                return latest_response

            tool_name = str(action.get("tool", ""))
            self.emit_status(f"[TOOL {step}/{max_tool_steps}] {agent_name} -> {tool_name}")
            result = tool_executor.execute(action)
            agent.remember(f"{tool_name}: {'ok' if result.success else 'failed'} - {result.content[:500]}")
            current_prompt = json.dumps(
                {
                    "tool_result": result.to_payload(),
                    "instruction": (
                        "Use the tool result to continue. If more context is needed, output the next "
                        "JSON tool action. If the file is ready, either call write_file with the final "
                        "complete content or return the final Python code."
                    ),
                },
                ensure_ascii=False,
                indent=2,
            )

        return latest_response

    def extract_tool_action(self, response: str) -> dict[str, Any] | None:
        try:
            payload = extract_json_payload(response)
        except ValueError:
            return None

        action = payload.get("next_action") if isinstance(payload, dict) else None
        if not isinstance(action, dict):
            return None
        if not action.get("tool"):
            return None
        if not isinstance(action.get("args", {}), dict):
            action["args"] = {}
        return action

    def make_tool_executor(self, workspace_root: str | Path) -> AgentToolExecutor:
        root = Path(workspace_root)
        return AgentToolExecutor(
            workspace_roots=[root],
            knowledge_base_root=Path(__file__).resolve().parent / "knowledge_base",
            previous_attempts=self.previous_attempts,
            event_callback=self.event_callback,
        )

    def run(self) -> None:
        print("=== 多智能体 CAD 设计系统 ===")
        requirement_payload = self.collect_requirements()
        self.process_confirmed_requirement(requirement_payload)

    def process_confirmed_requirement(self, requirement_payload: dict[str, Any]) -> None:
        request_type = str(requirement_payload.get("request_type", "")).strip().lower()

        if request_type == "part":
            self.run_part_state_machine(requirement_payload)
            return

        if request_type == "assembly":
            self.run_assembly_state_machine(requirement_payload)
            return

        raise ValueError(f"Unsupported request_type: {request_type}")

    def can_handle_followup_modification(self, user_message: str) -> bool:
        if not self.last_run_context or self.last_run_context.get("request_type") != "part":
            return False
        text = user_message.strip().lower()
        modification_markers = [
            "修改",
            "调整",
            "改",
            "加",
            "增加",
            "减少",
            "缩小",
            "放大",
            "变",
            "优化",
            "倒角",
            "圆角",
            "孔",
            "厚度",
            "长度",
            "宽度",
            "高度",
            "move",
            "modify",
            "change",
            "adjust",
            "add",
            "remove",
            "larger",
            "smaller",
        ]
        new_design_markers = ["新建", "重新设计一个", "另做", "新的零件", "new part", "new assembly"]
        return any(marker in text for marker in modification_markers) and not any(
            marker in text for marker in new_design_markers
        )

    def process_followup_modification(self, user_message: str) -> bool:
        if not self.last_run_context or self.last_run_context.get("request_type") != "part":
            return False
        plan = self.last_run_context.get("plan")
        part_spec = self.last_run_context.get("part_spec")
        if not isinstance(plan, dict) or not isinstance(part_spec, dict):
            return False

        self.emit_status("[小幅修改] 复用当前零件工作目录，直接进入零件修改智能体")
        part_spec.setdefault("standalone_modeling_instructions", [])
        part_spec["standalone_modeling_instructions"] = [
            *list(part_spec.get("standalone_modeling_instructions") or []),
            *self.recent_review_comments(),
            f"Follow-up modification request: {user_message}",
        ]
        review_context = "\n".join(f"- {comment}" for comment in self.recent_review_comments())
        success = self.run_part_pipeline(
            full_plan=plan,
            part_spec=part_spec,
            enable_static_validation=True,
            initial_feedback=(
                f"User follow-up modification request: {user_message}\n"
                f"Recent review comments to preserve:\n{review_context or '(none)'}"
            ),
        )
        self.last_run_context = {
            "request_type": "part",
            "plan": plan,
            "part_spec": part_spec,
            "success": success,
        }
        self.write_review_history(plan.get("workspace"))
        self.set_state(PipelineState.DONE if success else PipelineState.FAILED_FATAL, request_type="part_modification")
        return True

    def review_requirement_payload(self, requirement_payload: dict[str, Any]) -> dict[str, Any]:
        prompt = json.dumps(
            {
                "requirement_payload": requirement_payload,
                "recent_review_history": self.review_history[-5:],
                "review_goal": "Soft-check CAD feasibility and prepare downstream comments. Only severity=fatal should block generation.",
                "severity_policy": {
                    "ok": "No meaningful issue; continue.",
                    "warning": "Issue can be solved by a reasonable engineering assumption or local dimension adjustment; continue and pass comments downstream.",
                    "fatal": "Issue cannot be solved without asking the user because it contradicts the design intent or makes modeling impossible.",
                },
                "interpretation_rules": [
                    "Treat bolt/hole radius as the radius of the hole itself, not the polar placement radius, unless the text explicitly says placement/distribution radius.",
                    "If a dimension conflict can be resolved by preserving semantic intent, provide a concrete correction in comments_for_next_agent and use severity=warning.",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        response = self.run_agent("RequirementReviewAgent", self.requirement_review_agent, prompt)
        try:
            review = extract_json_payload(response)
        except ValueError:
            review = {
                "pass": False,
                "severity": "warning",
                "feedback": "Requirement review did not return parseable JSON.",
                "comments_for_next_agent": [],
            }
        severity = str(review.get("severity") or ("ok" if review.get("pass") else "warning")).lower()
        if severity not in {"ok", "warning", "fatal"}:
            severity = "warning"
        review["severity"] = severity
        if severity in {"ok", "warning"}:
            review["pass"] = True
        comments = review.get("comments_for_next_agent", [])
        if comments:
            requirement_payload.setdefault("review_comments", comments)
        self.record_review("requirement", review, {"request_type": requirement_payload.get("request_type")})
        return review

    def review_assembly_plan_payload(self, plan: dict[str, Any]) -> dict[str, Any]:
        prompt = json.dumps(
            {
                "assembly_plan": plan,
                "recent_review_history": self.review_history[-5:],
                "review_goal": "Soft-review the assembly protocol before part modeling. Prefer pass=true with actionable comments.",
                "severity_policy": {
                    "ok": "No meaningful issue; continue.",
                    "warning": "Issue can be solved by comments, reasonable defaults, or local planning adjustment; continue and store comments in assembly.review_comments.",
                    "fatal": "Only use when current SolidWorks constraints cannot express the plan or the part/instance relation is irreconcilable.",
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        response = self.run_agent("AssemblyPlanReviewAgent", self.assembly_plan_review_agent, prompt)
        try:
            review = extract_json_payload(response)
        except ValueError:
            review = {
                "pass": True,
                "severity": "warning",
                "feedback": "Assembly plan review did not return parseable JSON.",
                "comments_for_next_agent": [],
            }
        severity = str(review.get("severity") or ("ok" if review.get("pass") else "warning")).lower()
        if severity not in {"ok", "warning", "fatal"}:
            severity = "warning"
        review["severity"] = severity
        if severity in {"ok", "warning"}:
            review["pass"] = True
        comments = review.get("comments_for_next_agent", [])
        if comments:
            plan.setdefault("assembly", {}).setdefault("review_comments", comments)
        self.record_review("assembly_plan", review, {"name": plan.get("assembly", {}).get("name")})
        return review

    def record_review(self, scope: str, review: dict[str, Any], context: dict[str, Any] | None = None) -> None:
        entry = {
            "scope": scope,
            "context": context or {},
            "review": review,
            "comments_for_next_agent": list(review.get("comments_for_next_agent", []) or []),
        }
        self.review_history.append(entry)
        self.review_history = self.review_history[-20:]

    def write_review_history(self, workspace: dict[str, str] | None) -> None:
        if not workspace:
            return
        json_dir = workspace.get("json_dir")
        if not json_dir:
            return
        write_json(Path(json_dir) / "reviews.json", {"reviews": self.review_history})

    def recent_review_comments(self) -> list[str]:
        comments: list[str] = []
        for entry in self.review_history[-8:]:
            comments.extend(entry.get("comments_for_next_agent", []) or [])
        return comments[-20:]

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
        self.run_part_state_machine(requirement_payload)

    def run_part_state_machine(self, requirement_payload: dict[str, Any]) -> None:
        self.set_state(PipelineState.REQUIREMENT_CLARIFYING, request_type="part")
        self.set_state(PipelineState.PLAN_GENERATING, request_type="part")
        review = self.review_requirement_payload(requirement_payload)
        self.emit_event("review_result", scope="requirement", **review)
        if review.get("severity") == "fatal":
            self.set_state(PipelineState.FAILED_RECOVERABLE, request_type="part", review=review)
            raise ValueError(f"Part requirement review failed: {review.get('feedback')}")
        workspace = self.create_single_part_workspace(requirement_payload)
        plan = self.build_single_part_plan(requirement_payload, workspace)
        write_json(Path(plan["workspace"]["plan_file"]), plan)
        self.write_review_history(plan["workspace"])

        print("\n[阶段 2] 单零件建模")
        self.emit_status("[阶段 2] 单零件建模")
        self.set_state(PipelineState.PART_MODELING, part_id=plan["part"]["part_id"])
        success = self.run_part_pipeline(
            full_plan=plan,
            part_spec=plan["part"],
            enable_static_validation=True,
        )
        self.last_run_context = {
            "request_type": "part",
            "plan": plan,
            "part_spec": plan["part"],
            "success": success,
        }
        self.write_review_history(plan["workspace"])
        if success:
            self.set_state(PipelineState.DONE, request_type="part")
            print("\n=== 单零件需求执行完成 ===")
            part_workspace = plan["part"]["workspace"]
            # 通过结构化事件把生成的文件路径透传给上游（例如 cautod_fastapi）
            self.emit_event(
                "pipeline_result",
                request_type="part",
                part_id=str(plan["part"].get("part_id", "")),
                model_file=str(part_workspace["model_file"]),
                code_file=str(part_workspace["code_file"]),
                log_file=str(part_workspace["log_file"]),
            )
        else:
            print("\n=== 单零件需求执行失败，请根据日志调整需求或知识库 ===")

    def handle_assembly_request(self, requirement_payload: dict[str, Any]) -> None:
        self.run_assembly_state_machine(requirement_payload)

    def run_assembly_state_machine(self, requirement_payload: dict[str, Any]) -> None:
        self.set_state(PipelineState.REQUIREMENT_CLARIFYING, request_type="assembly")
        self.set_state(PipelineState.PLAN_GENERATING, request_type="assembly")
        review = self.review_requirement_payload(requirement_payload)
        self.emit_event("review_result", scope="requirement", **review)
        if review.get("severity") == "fatal":
            self.set_state(PipelineState.FAILED_RECOVERABLE, request_type="assembly", review=review)
            raise ValueError(f"Assembly requirement review failed: {review.get('feedback')}")
        workspace = self.create_assembly_workspace(requirement_payload)
        print("\n[阶段 2] 装配规划")
        self.emit_status("[阶段 2] 装配规划")
        plan = self.generate_assembly_plan(requirement_payload, workspace)
        self.write_review_history(plan["assembly"]["workspace"])

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
                    "code_file": part_spec["workspace"]["code_file"],
                    "log_file": part_spec["workspace"]["log_file"],
                }
            )
            print("\n=== 零件建模未全部完成，停止装配阶段 ===")
            return

        print("\n[阶段 4] 装配生成与执行")
        self.emit_status("[阶段 4] 装配生成与执行")
        self.set_state(PipelineState.ASSEMBLY_MODELING, parts=len(part_results))
        assembly_success = self.run_assembly_pipeline(plan, part_results)
        if assembly_success:
            self.set_state(PipelineState.DONE, request_type="assembly")
            print("\n=== 装配需求执行完成 ===")
            assembly_output = plan["assembly"]["assembly_output"]
            self.emit_event(
                "pipeline_result",
                request_type="assembly",
                assembly_model_file=str(assembly_output["model_file"]),
                assembly_code_file=str(assembly_output["code_file"]),
                assembly_log_file=str(assembly_output["log_file"]),
                parts=[
                    {
                        "part_id": pr.get("part_id"),
                        "model_file": pr.get("model_file"),
                        "code_file": pr.get("code_file"),
                        "log_file": pr.get("log_file"),
                    }
                    for pr in part_results
                    if pr.get("success")
                ],
            )
        else:
            print("\n=== 装配阶段失败，请查看输出目录日志 ===")
        self.last_run_context = {
            "request_type": "assembly",
            "plan": plan,
            "part_results": part_results,
            "success": assembly_success,
        }
        self.write_review_history(plan["assembly"]["workspace"])

    def create_single_part_workspace(self, requirement_payload: dict[str, Any]) -> dict[str, str]:
        name = slugify(requirement_payload.get("name", "part"), "part")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        root_dir = AGENT_OUTPUT_ROOT / f"{name}-{timestamp}"
        part_dir = root_dir / "part"
        json_dir = root_dir / "json"
        logs_dir = root_dir / "logs"
        screenshots_dir = root_dir / "screenshots"

        for directory in (root_dir, part_dir, json_dir, logs_dir, screenshots_dir):
            directory.mkdir(parents=True, exist_ok=True)

        return {
            "root_dir": str(root_dir),
            "part_dir": str(part_dir),
            "json_dir": str(json_dir),
            "logs_dir": str(logs_dir),
            "screenshots_dir": str(screenshots_dir),
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
                "standalone_modeling_instructions": [
                    *list(requirement_payload.get("key_requirements", []) or []),
                    *list(requirement_payload.get("review_comments", []) or []),
                ],
                "workspace": {
                    "part_dir": str(part_dir),
                    "code_file": str(part_dir / f"{part_id}_model.py"),
                    "model_file": str(part_dir / f"{part_id}.SLDPRT"),
                    "log_file": str(Path(workspace["logs_dir"]) / f"{part_id}_model.log"),
                    "screenshot_dir": str(Path(workspace["screenshots_dir"]) / part_id),
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
        screenshots_dir = root_dir / "screenshots"

        for directory in (root_dir, parts_dir, assembly_dir, json_dir, logs_dir, screenshots_dir):
            directory.mkdir(parents=True, exist_ok=True)

        return {
            "root_dir": str(root_dir),
            "parts_dir": str(parts_dir),
            "assembly_dir": str(assembly_dir),
            "json_dir": str(json_dir),
            "logs_dir": str(logs_dir),
            "screenshots_dir": str(screenshots_dir),
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
            plan_review = self.review_assembly_plan_payload(plan)
            self.emit_event("review_result", scope="assembly_plan", **plan_review)
            if plan_review.get("severity") == "fatal":
                current_prompt = self.build_assembly_plan_retry_prompt(
                    requirement_payload=requirement_payload,
                    workspace=workspace,
                    model_response=response,
                    validation_errors=[
                        f"Assembly plan review failed: {plan_review.get('feedback', '')}",
                        *list(plan_review.get("comments_for_next_agent", []) or []),
                    ],
                )
                continue
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
            "screenshot_dir": str(Path(workspace["screenshots_dir"]) / "assembly"),
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
                "screenshot_dir": str(Path(workspace["screenshots_dir"]) / part_id),
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
                        "review_comments": assembly.get("review_comments", []),
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

    def run_parts_parallel(
        self,
        full_plan: dict[str, Any],
        part_specs: list[dict[str, Any]],
        max_workers: int = PART_PARALLELISM_LIMIT,
    ) -> list[dict[str, Any]]:
        worker_count = max(1, min(max_workers, PART_PARALLELISM_LIMIT, len(part_specs) or 1))
        self.emit_status(f"[零件并行] 启动 {len(part_specs)} 个零件任务，并行上限 {worker_count}")
        self.emit_event(
            "parallel_parts_start",
            total=len(part_specs),
            max_workers=worker_count,
            part_ids=[part.get("part_id") for part in part_specs],
        )

        results_by_index: dict[int, dict[str, Any]] = {}
        with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="part-agent") as executor:
            future_to_context = {
                executor.submit(
                    self.run_part_pipeline,
                    full_plan=full_plan,
                    part_spec=part_spec,
                    enable_static_validation=True,
                ): (index, part_spec)
                for index, part_spec in enumerate(part_specs)
            }

            for future in as_completed(future_to_context):
                index, part_spec = future_to_context[future]
                part_id = part_spec["part_id"]
                try:
                    success = future.result()
                    error = None
                except Exception as exc:
                    success = False
                    error = str(exc)
                    self.emit_event("error", error=f"Part {part_id} failed with exception: {exc}")

                result = {
                    "part_id": part_id,
                    "name": part_spec["name"],
                    "success": success,
                    "model_file": part_spec["workspace"]["model_file"],
                }
                if error:
                    result["error"] = error
                results_by_index[index] = result
                self.emit_event("parallel_part_done", **result)
                self.emit_status(
                    f"[零件并行] {part_spec['name']} {'完成' if success else '失败'} "
                    f"({len(results_by_index)}/{len(part_specs)})"
                )

        ordered_results = [results_by_index[index] for index in range(len(part_specs))]
        self.emit_event("parallel_parts_end", results=ordered_results)
        return ordered_results

    def run_part_pipeline(
        self,
        full_plan: dict[str, Any],
        part_spec: dict[str, Any],
        enable_static_validation: bool,
        max_retries: int = 5,
        initial_feedback: str | None = None,
    ) -> bool:
        part_agent = PartModelingAgent()
        validation_agent = PartValidationAgent() if enable_static_validation else None
        workspace_root = (
            full_plan.get("workspace", {}).get("root_dir")
            or full_plan.get("assembly", {}).get("workspace", {}).get("root_dir")
            or part_spec["workspace"]["part_dir"]
        )
        tool_executor = self.make_tool_executor(workspace_root)

        current_prompt = self.build_part_prompt(full_plan, part_spec, initial_feedback)
        for attempt in range(1, max_retries + 1):
            print(f"    [建模尝试 {attempt}/{max_retries}] 生成 {part_spec['name']} 代码")
            self.emit_status(f"[建模尝试 {attempt}/{max_retries}] 生成 {part_spec['name']} 代码")
            response = self.run_agent_with_tools("PartModelingAgent", part_agent, current_prompt, tool_executor)
            code_file = Path(part_spec["workspace"]["code_file"])
            response_code = extract_python_code(response)
            if "```python" in response.lower() or (response_code and not response.strip().startswith("{")):
                code = response_code
            elif code_file.exists():
                code = code_file.read_text(encoding="utf-8", errors="replace")
            else:
                code = extract_python_code(response)

            workdir = Path(part_spec["workspace"]["part_dir"])
            script_name = Path(part_spec["workspace"]["code_file"]).name
            write_text(workdir / script_name, code)
            self.set_state(PipelineState.PART_EXECUTING, part_id=part_spec["part_id"], attempt=attempt)
            execution = tool_executor.execute(
                {
                    "tool": "run_solidworks_pipeline",
                    "args": {
                        "script_path": str(workdir / script_name),
                        "screenshot_dir": part_spec["workspace"].get("screenshot_dir") or str(workdir / "screenshots"),
                        "screenshot_base_name": f"{part_spec['part_id']}_attempt_{attempt}",
                    },
                }
            )
            write_text(Path(part_spec["workspace"]["log_file"]), execution.content)
            self.emit_event("execution_log", title=f"{part_spec['name']} 执行与截图日志", content=execution.content)

            self.record_attempt(part_spec["part_id"], attempt, code, execution.content, execution.success)

            if not execution.success:
                summary = format_execution_failure_summary(execution.log)
                print(f"    [执行失败] {summary}")
                self.emit_status(f"[执行失败] {summary}")
                part_agent.remember(f"Attempt {attempt} failed. Edit the existing file instead of regenerating from scratch.")
                current_prompt = self.build_part_prompt(full_plan, part_spec, execution.content)
                continue

            print("    [执行成功] 开始静态校验" if enable_static_validation else "    [执行成功] 动态校验通过")
            self.emit_status("    [执行成功] 开始静态校验" if enable_static_validation else "    [执行成功] 动态校验通过")
            if not enable_static_validation:
                return True

            self.set_state(PipelineState.PART_VALIDATING, part_id=part_spec["part_id"], attempt=attempt)
            deterministic_issues = run_part_plan_checks(full_plan, part_spec, code)
            validator_feedback = self.validate_part_code(
                validation_agent=validation_agent,
                full_plan=full_plan,
                part_spec=part_spec,
                code=code,
                deterministic_issues=deterministic_issues,
                execution_result=execution.to_payload(),
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

    def record_attempt(self, part_id: str, attempt: int, code: str, log: str, success: bool) -> None:
        with self.previous_attempts_lock:
            attempts = self.previous_attempts.setdefault(str(part_id), [])
            attempts.append(
                {
                    "attempt": attempt,
                    "success": success,
                    "code_excerpt": code[-4000:],
                    "log_summary": "\n".join(log.splitlines()[-30:]),
                }
            )
            self.previous_attempts[str(part_id)] = attempts[-5:]

    def validate_part_code(
        self,
        validation_agent: PartValidationAgent | None,
        full_plan: dict[str, Any],
        part_spec: dict[str, Any],
        code: str,
        deterministic_issues: list[str],
        execution_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if validation_agent is None:
            return {"pass": not deterministic_issues, "feedback": "; ".join(deterministic_issues)}

        prompt = json.dumps(
            {
                "full_plan": full_plan,
                "part_spec": part_spec,
                "generated_code": code,
                "deterministic_issues": deterministic_issues,
                "execution_result": execution_result or {},
                "screenshot_files": (execution_result or {}).get("data", {}).get("screenshots", []),
            },
            ensure_ascii=False,
            indent=2,
        )

        screenshot_files = (execution_result or {}).get("data", {}).get("screenshots", [])
        if screenshot_files:
            response = validation_agent.chat_with_images(prompt, list(screenshot_files))
        else:
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
            "mode": "tool_first_local_edit",
            "tool_protocol": {
                "response_shape": {"thought": "...", "next_action": {"tool": "read_file", "args": {"path": "..."}}},
                "available_tools": [
                    "read_file(path)",
                    "write_file(path, content)",
                    "run_python(script_path)",
                    "run_solidworks_pipeline(script_path, screenshot_dir, screenshot_base_name)",
                    "list_dir(path)",
                    "search_in_kb(query)",
                    "load_previous_attempt(part_id)",
                    "summarize_log(log)",
                ],
            },
            "local_edit_policy": "If code_file already exists or retry_feedback is present, inspect/read the existing file and change only the necessary parts before writing the complete updated file.",
            "execution_policy": "After code generation the orchestrator will run: clear SolidWorks -> execute code -> capture screenshots under a SolidWorks lock. Feedback includes execution log and screenshot files.",
            "task": "请为下面的零件生成完整可执行 Python 建模代码；如果该零件会被多个实例复用，也只建模一次通用零件模板。",
            "full_plan_summary": full_plan,
            "part_spec": part_spec,
            "code_file": part_spec.get("workspace", {}).get("code_file"),
        }
        if retry_feedback:
            payload["retry_feedback"] = retry_feedback
            payload["instruction"] = "请基于反馈完整重写代码，不要只给差异片段。"
        if retry_feedback:
            payload["instruction"] = "Prefer a local edit of the existing code_file. Use read_file/load_previous_attempt first when useful, then write_file the complete corrected file."
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def run_assembly_pipeline(
        self,
        plan: dict[str, Any],
        part_results: list[dict[str, Any]],
        max_retries: int = 5,
    ) -> bool:
        current_prompt = self.build_assembly_prompt(plan, part_results, None)
        assembly_output = plan["assembly"]["assembly_output"]
        tool_executor = self.make_tool_executor(plan["assembly"]["workspace"]["root_dir"])

        for attempt in range(1, max_retries + 1):
            print(f"  [装配尝试 {attempt}/{max_retries}] 生成装配代码")
            self.emit_status(f"[装配尝试 {attempt}/{max_retries}] 生成装配代码")
            response = self.run_agent_with_tools("AssemblyAgent", self.assembly_agent, current_prompt, tool_executor)
            code_file = Path(assembly_output["code_file"])
            response_code = extract_python_code(response)
            if "```python" in response.lower() or (response_code and not response.strip().startswith("{")):
                code = response_code
            elif code_file.exists():
                code = code_file.read_text(encoding="utf-8", errors="replace")
            else:
                code = extract_python_code(response)

            workdir = Path(plan["assembly"]["workspace"]["assembly_dir"])
            script_name = Path(assembly_output["code_file"]).name
            write_text(workdir / script_name, code)
            self.set_state(PipelineState.ASSEMBLY_EXECUTING, attempt=attempt)
            execution = tool_executor.execute(
                {
                    "tool": "run_solidworks_pipeline",
                    "args": {
                        "script_path": str(workdir / script_name),
                        "screenshot_dir": assembly_output.get("screenshot_dir") or str(workdir / "screenshots"),
                        "screenshot_base_name": f"assembly_attempt_{attempt}",
                    },
                }
            )
            write_text(Path(assembly_output["log_file"]), execution.content)
            self.emit_event("execution_log", title="装配执行与截图日志", content=execution.content)

            if not execution.success:
                summary = format_execution_failure_summary(execution.log)
                print(f"  [装配执行失败] {summary}")
                self.emit_status(f"[装配执行失败] {summary}")
                current_prompt = self.build_assembly_prompt(plan, part_results, execution.content)
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
            "mode": "tool_first_local_edit",
            "tool_protocol": {
                "response_shape": {"thought": "...", "next_action": {"tool": "read_file", "args": {"path": "..."}}},
                "available_tools": [
                    "read_file(path)",
                    "write_file(path, content)",
                    "run_python(script_path)",
                    "run_solidworks_pipeline(script_path, screenshot_dir, screenshot_base_name)",
                    "list_dir(path)",
                    "search_in_kb(query)",
                    "load_previous_attempt(part_id)",
                    "summarize_log(log)",
                ],
            },
            "local_edit_policy": "If assembly code already exists or retry_feedback is present, inspect/read the existing file and change only the necessary parts before writing the complete updated file.",
            "execution_policy": "After code generation the orchestrator will run: clear SolidWorks -> execute code -> capture screenshots under a SolidWorks lock. Feedback includes execution log and screenshot files.",
            "code_file": plan.get("assembly", {}).get("assembly_output", {}).get("code_file"),
            "assembly_plan": plan,
            "part_results": part_results,
        }
        if retry_feedback:
            payload["retry_feedback"] = retry_feedback
            payload["instruction"] = "请基于反馈完整重写装配代码，不要只给差异片段。"
        if retry_feedback:
            payload["instruction"] = "Prefer a local edit of the existing assembly code_file. Use read_file first when useful, then write_file the complete corrected file."
        return json.dumps(payload, ensure_ascii=False, indent=2)
