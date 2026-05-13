from __future__ import annotations

import json
import base64
import re
import threading
from pathlib import Path
from typing import Any

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    from .config import KNOWLEDGE_BASE_ROOT, MODEL_NAME, OPENROUTER_API_KEY, OPENROUTER_BASE_URL
except ImportError:
    from config import KNOWLEDGE_BASE_ROOT, MODEL_NAME, OPENROUTER_API_KEY, OPENROUTER_BASE_URL

client = None
client_lock = threading.Lock()


def get_client():
    global client
    if client is not None:
        return client

    with client_lock:
        if client is not None:
            return client

        if OpenAI is None:
            raise RuntimeError(
                "缺少 `openai` 依赖，无法初始化多智能体模型客户端。"
                "请先安装 openai 包后再运行 multi_agent_src。"
            )
        client = OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=OPENROUTER_API_KEY,
        )
        # client = OpenAI(
        #     base_url="https://ark.cn-beijing.volces.com/api/v3",
        #     api_key=os.getenv("ARK_API_KEY"),
        # )

        # client = OpenAI(
        # # 如果没有配置环境变量，请用阿里云百炼API Key替换：api_key="sk-xxx"
        # api_key=os.getenv("DASHSCOPE_API_KEY"),
        # base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        # )

    return client


def load_kb(agent_name: str) -> str:
    kb_dir = KNOWLEDGE_BASE_ROOT / agent_name
    if not kb_dir.exists():
        return f"Knowledge base directory not found: {kb_dir}"

    contents: list[str] = []
    for path in sorted(kb_dir.rglob("*")):
        if not path.is_file() or path.name.startswith("."):
            continue
        text = path.read_text(encoding="utf-8")
        contents.append(f"# {path.relative_to(kb_dir).as_posix()}\n{text}")

    if not contents:
        return f"Knowledge base directory is currently empty: {kb_dir}"
    return "\n\n".join(contents)


def extract_python_code(text: str) -> str:
    match = re.search(r"```python\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.strip()


def extract_json_payload(text: str) -> dict[str, Any]:
    candidates = re.findall(r"```json\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    candidates.append(text)

    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            snippet = candidate[start : end + 1]
            try:
                return json.loads(snippet)
            except json.JSONDecodeError:
                continue

    raise ValueError("Unable to extract valid JSON payload from model response.")


TOOL_ACTION_CONTRACT = """

Tool action contract:
- Prefer local edits over regenerating an entire file when a previous attempt exists.
- When you need workspace context, output exactly one JSON object:
  {"thought":"short reason","next_action":{"tool":"read_file","args":{"path":"..."}}}
- Available tools: read_file(path), write_file(path, content), run_python(script_path),
  run_solidworks_pipeline(script_path, screenshot_dir, screenshot_base_name), list_dir(path),
  search_in_kb(query), load_previous_attempt(part_id), summarize_log(log).
- After a tool result is returned, either request another tool or provide the final code.
- If you write a file, write the complete current file content to the requested path.
"""


class BaseAgent:
    def __init__(self, system_prompt: str, temperature: float = 0.2, max_history_messages: int = 20):
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_history_messages = max_history_messages
        self.state_summary = ""
        self.short_term_memory: list[str] = []
        self._dialogue: list[dict[str, str]] = []
        self.history = [{"role": "system", "content": system_prompt}]

    def chat(self, user_input: str) -> str:
        self._append_message("user", user_input)
        response = get_client().chat.completions.create(
            model=MODEL_NAME,
            messages=self._build_messages(),
            temperature=self.temperature,
            extra_body={"enable_thinking":False},
        )
        reply = response.choices[0].message.content or ""
        self._append_message("assistant", reply)
        return reply

    def stream_chat(self, user_input: str):
        self._append_message("user", user_input)
        stream = get_client().chat.completions.create(
            model=MODEL_NAME,
            messages=self._build_messages(),
            temperature=self.temperature,
            extra_body={"enable_thinking": False},
            stream=True,
        )

        chunks: list[str] = []
        for event in stream:
            if not event.choices:
                continue
            delta = getattr(event.choices[0].delta, "content", None)
            if not delta:
                continue
            chunks.append(delta)
            yield delta

        reply = "".join(chunks)
        self._append_message("assistant", reply)

    def chat_with_images(self, user_input: str, image_paths: list[str]) -> str:
        content: list[dict[str, Any]] = [{"type": "text", "text": user_input}]
        for image_path in image_paths:
            path = Path(image_path)
            if not path.is_file():
                continue
            suffix = path.suffix.lower().lstrip(".") or "png"
            if suffix == "jpg":
                suffix = "jpeg"
            payload = base64.b64encode(path.read_bytes()).decode("ascii")
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/{suffix};base64,{payload}"},
                }
            )

        self._dialogue.append({"role": "user", "content": user_input})
        messages: list[dict[str, Any]] = self._build_messages()[:-1]
        messages.append({"role": "user", "content": content})
        try:
            response = get_client().chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=self.temperature,
                extra_body={"enable_thinking": False},
            )
            reply = response.choices[0].message.content or ""
        except Exception as exc:
            reply = self.chat(
                user_input
                + "\n\n[Image feedback fallback] The current model/API could not consume screenshot images directly. "
                + f"Use the screenshot file paths and execution log in the payload for a text-only judgment. Error: {exc}"
            )
            return reply
        self._append_message("assistant", reply)
        return reply

    def remember(self, note: str) -> None:
        note = str(note).strip()
        if not note:
            return
        self.short_term_memory.append(note)
        self.short_term_memory = self.short_term_memory[-8:]
        self._refresh_history()

    def _append_message(self, role: str, content: str) -> None:
        self._dialogue.append({"role": role, "content": content})
        self._compact_dialogue()
        self._refresh_history()

    def _compact_dialogue(self) -> None:
        if len(self._dialogue) <= self.max_history_messages:
            return

        overflow = self._dialogue[: -self.max_history_messages]
        self._dialogue = self._dialogue[-self.max_history_messages :]
        summary_bits: list[str] = []
        for message in overflow[-6:]:
            content = message.get("content", "").strip().replace("\n", " ")
            if content:
                summary_bits.append(f"{message.get('role', 'unknown')}: {content[:500]}")
        if summary_bits:
            self.state_summary = ("Previous context summary:\n" + "\n".join(summary_bits))[-4000:]

    def _memory_message(self) -> dict[str, str] | None:
        chunks: list[str] = []
        if self.state_summary:
            chunks.append(self.state_summary)
        if self.short_term_memory:
            chunks.append("Short-term work memory:\n- " + "\n- ".join(self.short_term_memory))
        if not chunks:
            return None
        return {"role": "system", "content": "\n\n".join(chunks)}

    def _build_messages(self) -> list[dict[str, str]]:
        messages = [{"role": "system", "content": self.system_prompt}]
        memory = self._memory_message()
        if memory is not None:
            messages.append(memory)
        messages.extend(self._dialogue)
        return messages

    def _refresh_history(self) -> None:
        self.history = self._build_messages()


class RequirementAgent(BaseAgent):
    def __init__(self) -> None:
        kb = load_kb("requirement_agent")
        system_prompt = (
            "你是工业设计需求分析智能体。"
            "你的职责是通过多轮对话澄清用户需求，并判断需求类型是 `part`（单零件）还是 `assembly`（装配体）。\n"
            "能力边界：支持基于拉伸、旋转、切除、孔、阵列、基准面/基准轴、常规装配配合的零件和装配；"
            "不支持复杂自由曲面、柔性机构、高级仿真。\n"
            "工作规则：\n"
            "1. 信息不足时继续追问，尤其是名称、功能、关键尺寸、连接/配合关系、接口要求、保存目标。\n"
            "2. 只要用户明确表达的是单个零件，就判定为 `part`；涉及多个零件及其配合关系时判定为 `assembly`。\n"
            "3. 当你认为信息足够继续后续建模时，先给出一段简短中文确认，再输出 `[CONFIRMED]`。\n"
            "4. `[CONFIRMED]` 后必须紧跟一个 JSON 代码块，字段必须包含：\n"
            '{'
            '"request_type":"part 或 assembly",'
            '"name":"对象名称",'
            '"summary":"精炼需求摘要",'
            '"key_requirements":["关键要求"],'
            '"assumptions":["默认假设，没有则空数组"],'
            '"requested_outputs":["用户要求的交付物"],'
            '"interfaces":["已明确的接口、装配面、装配轴、连接关系，没有则空数组"]'
            '}\n'
            "5. 除非确认，否则不要输出 JSON。\n"
            "6. 注意，在用户没有确认前，千万千万不能在输出中出现任何形式的 `[CONFIRMED]` 标签！！！！！"
            f"参考知识库：\n{kb}"
        )
        super().__init__(system_prompt=system_prompt, temperature=0.3, max_history_messages=60)


class AssemblyPlanningAgent(BaseAgent):
    def __init__(self) -> None:
        kb = load_kb("assembly_planning_agent")
        system_prompt = (
            "你是装配规划智能体，负责把已经确认的装配需求转成严格的结构化 JSON。"
            "你的输入可能是自然语言、半结构化文本、对话摘要或 JSON；即使输入不是 JSON，你也必须正常理解并完成规划。"
            "你必须只输出 JSON，不要输出解释。\n"
            "输出目标：给出完整装配规划，其中每个唯一几何零件都能单独拿到自己的 JSON 子对象后独立建模；"
            "如果装配体里有多个相同零件，必须优先复用同一个零件定义，通过实例层表达重复出现和不同装配接口使用方式。\n"
            "JSON 顶层结构必须是：\n"
            '{'
            '"request_type":"assembly",'
            '"assembly":{'
            '"name":"装配体名称",'
            '"summary":"装配目标",'
            '"workspace":{},'
            '"global_coordinate_system":{"origin":"","x_direction":"","y_direction":"","z_direction":""},'
            '"design_rules":["全局规则"],'
            '"parts":['
            '{'
            '"part_id":"snake_case_id",'
            '"name":"零件名称",'
            '"function":"功能",'
            '"shape":"形状描述",'
            '"key_dimensions":["关键尺寸"],'
            '"material_or_notes":"材料或工艺备注",'
            '"quantity":1,'
            '"instance_ids":["使用该零件模型的实例 id"],'
            '"interfaces":{'
            '"faces":[{"name":"","purpose":"","normal_direction_relation":""}],'
            '"axes":[{"name":"","purpose":"","direction_relation":""}],'
            '"points":[{"name":"","purpose":"","location_hint":""}]'
            '},'
            '"assembly_relation_notes":["该零件与外界或其他零件的关系"],'
            '"workspace":{},'
            '"standalone_modeling_instructions":["该零件单独建模必须满足的要求"]'
            '}'
            '],'
            '"instances":['
            '{'
            '"instance_id":"snake_case_instance_id",'
            '"part_id":"引用 parts 中的 part_id",'
            '"name":"实例名称",'
            '"instance_role":"该实例在装配中的角色",'
            '"placement_notes":"该实例相对装配体或其他零件的位置/用途说明",'
            '"interface_usage":{"faces":["本实例实际使用的面接口"],"axes":["本实例实际使用的轴接口"],"points":["本实例实际使用的点接口"]}'
            '}'
            '],'
            '"assembly_sequence":["装配顺序"],'
            '"constraints":['
            '{'
            '"source_instance_id":"",'
            '"source_part_id":"",'
            '"source_interface":"",'
            '"target_instance_id":"GROUND 或其他 instance_id",'
            '"target_part_id":"GROUND 或其他 part_id",'
            '"target_interface":"",'
            '"relation":"coincident/concentric/parallel/distance/fix",'
            '"alignment":"aligned/opposed/na",'
            '"offset_mm":0,'
            '"notes":""'
            '}'
            '],'
            '"assembly_output":{}'
            '}'
            '}\n'
            "要求：\n"
            "1. `parts` 只保留唯一几何零件；相同外形、相同建模方式的重复件不得重复建模，必须合并为一个 `part`，再用 `instances` 表达多个装配实例。\n"
            "2. 如果多个实例几何相同但对外装配接口用途不同，仍然优先复用同一个 `part`；在该 `part` 中提供这些实例需要的接口并在 `instances[].interface_usage` 中说明各实例分别实际使用哪些接口。\n"
            "3. 接口命名必须明确、稳定，便于后续建模和装配代码直接引用。\n"
            "4. `direction_relation` 或 `normal_direction_relation` 必须说明接口方向与零件局部方向/装配全局方向的关系。\n"
            "5. `constraints` 必须按实例引用，确保重复零件在装配时可以区分到具体实例。\n"
            "6. 如果尺寸不全，可给出合理工程假设并写入对应字段。\n"
            "7. `workspace` 与 `assembly_output` 会由外部提供，你必须保留并复用传入路径。\n"
            "8. 输出前必须自行检查 JSON 是否可被严格解析，字段是否完整、括号和引号是否闭合；如果你发现不合法，必须先在内部修正，再输出最终 JSON。\n"
            f"参考知识库：\n{kb}"
        )
        super().__init__(system_prompt=system_prompt, temperature=0.1, max_history_messages=12)


class PartModelingAgent(BaseAgent):
    def __init__(self) -> None:
        kb = load_kb("part_modeling_agent")
        system_prompt = (
            "你是零件建模智能体。"
            "你会收到一个零件 JSON，以及必要时收到完整装配规划摘要。"
            "你的任务是输出可执行的 Python 建模代码，并保存零件到指定的 `model_file` 路径。"
            "要求：\n"
            "1. 只输出 Python 代码，使用 ```python 代码块``` 包裹。\n"
            "2. 代码必须保存到输入 JSON 指定的目标文件位置；如果工作区已固定，允许使用相对路径、路径变量或等价拼接方式，不要求硬编码完整绝对路径。\n"
            "3. 如果该零件被多个实例复用，你仍然只生成一次通用零件模型，不要按实例重复建模。\n"
            "4. 必须在代码中体现接口名称，且要覆盖该零件被所有实例复用时需要的接口，便于后续装配引用。\n"
            "5. 优先写清晰、稳定、可重试的代码；必要时打印关键步骤日志。\n"
            f"参考知识库：\n{kb}"
        )
        system_prompt += TOOL_ACTION_CONTRACT
        super().__init__(system_prompt=system_prompt, temperature=0.2, max_history_messages=10)


class PartValidationAgent(BaseAgent):
    def __init__(self) -> None:
        kb = load_kb("part_validation_agent")
        system_prompt = (
            "你是零件静态校验智能体。"
            "你会拿到完整装配规划、单个零件 JSON、生成代码，以及程序侧的规则检查结果。"
            "你必须只输出 JSON："
            '{"pass": true 或 false, "feedback": "一句到两句的简短意见,导致失败的原因，以及正确的零件信息以及保存路径"}\n'
            "校验重点：\n"
            "1. 局部的代码零件是否与完整装配体规划中要求的一致。\n"
            "2. 零件接口名称、方向关系、保存路径是否覆盖。\n"
            "3. 是否有明显导致后续装配失败的静态问题。\n"
            "4. 关于保存路径，只要代码最终保存到规定工作区下的正确目标位置，即使通过相对路径、变量或路径拼接实现，也可视为正确，不要求完整绝对路径字面量必须直接出现。\n"
            "5. 如果输入中带有截图，请检查模型是否出现不连续实体、明显悬空/脱节几何、特征缺失、比例异常；发现这类问题必须 pass=false 并要求重新生成或局部修复。\n"
            "如果问题轻微但不影响继续，可判定 pass=true 并在 feedback 中提示。"
            f"参考知识库：\n{kb}"
        )
        super().__init__(system_prompt=system_prompt, temperature=0.1, max_history_messages=12)


class RequirementReviewAgent(BaseAgent):
    def __init__(self) -> None:
        system_prompt = (
            "你是CAD需求可行性软评审智能体。你只输出JSON："
            '{"pass": true/false, "severity": "ok/warning/fatal", '
            '"feedback": "评审意见", '
            '"comments_for_next_agent": ["给建模/规划智能体的注意事项或自动修正建议"]}。'
            "评审默认不能阻断流程；除非需求在物理或拓扑上无法通过合理工程假设修正，才输出 severity=fatal。"
            "可通过默认值、改解释、局部尺寸调整解决的问题必须输出 severity=warning，并在 comments_for_next_agent 中给出可执行修正建议。"
            "不要把“孔半径”误判为“孔位分布半径”；例如'螺栓孔半径0.0035m'表示孔自身半径，孔位分布半径若缺失应建议默认取核心外围合理半径。"
            "零件需求要判断几何是否合理、是否容易生成不连续实体、关键尺寸/特征是否冲突。"
            "装配需求要判断组件职责、自由度、连接关系和约束表达是否足够合理。"
        )
        super().__init__(system_prompt=system_prompt, temperature=0.1, max_history_messages=8)


class AssemblyPlanReviewAgent(BaseAgent):
    def __init__(self) -> None:
        system_prompt = (
            "你是SolidWorks装配规划协议软评审智能体。你只输出JSON："
            '{"pass": true/false, "severity": "ok/warning/fatal", '
            '"feedback": "评审意见", '
            '"comments_for_next_agent": ["给零件建模或装配代码智能体的建议"]}。'
            "默认以通过为主：能通过补充建议、合理默认约束或局部修正解决的问题，必须输出 pass=true 且 severity=warning。"
            "你的主要任务是把建议添加到装配JSON的 review_comments 中，帮助后续零件建模和装配代码生成。"
            "只有当装配协议完全无法用当前SolidWorks库中的 coincident/concentric/parallel/distance/fix 等约束表达，"
            "或组件/实例关系根本矛盾且无法合理假设修正时，才输出 pass=false 且 severity=fatal。"
            "重点检查零件拆分、instance/part复用、约束可实现性、运动学自由度和静态装配特性，并给出可执行建议。"
        )
        super().__init__(system_prompt=system_prompt, temperature=0.1, max_history_messages=8)


class AssemblyAgent(BaseAgent):
    def __init__(self) -> None:
        kb = load_kb("assembly_agent")
        system_prompt = (
            "你是装配代码生成智能体。"
            "你会收到完整装配规划 JSON，以及已经成功生成的零件输出路径。"
            "你的任务是生成可执行的 Python 装配代码，并保存到指定的装配输出路径。"
            "要求：\n"
            "1. 只输出 Python 代码，使用 ```python 代码块``` 包裹。\n"
            "2. 必须严格使用规划中的零件文件、实例列表、装配顺序和配合关系。\n"
            "3. 对于重复零件，必须复用同一个零件文件并在装配中利用add_component插入多个实例，不要假设每个实例对应一个独立零件文件。\n"
            "4. 约束和组件缓存应优先以 `instance_id -> comp_name` 建立映射，再结合 `part_id -> model_file` 解析零件来源。\n"
            "5. 保存装配时只要最终落到规定工作区下的目标位置即可，允许使用相对路径、变量或路径拼接，不要求硬编码完整绝对路径。\n"
            "6. 对关键装配步骤打印简短日志，便于失败时回退重试。\n"
            f"参考知识库：\n{kb}"
        )
        system_prompt += TOOL_ACTION_CONTRACT
        super().__init__(system_prompt=system_prompt, temperature=0.2, max_history_messages=10)
