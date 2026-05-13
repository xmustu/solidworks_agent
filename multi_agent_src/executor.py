from __future__ import annotations

import ast
import os
import subprocess
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ExecutionResult:
    success: bool
    log: str
    script_path: Path


def _syntax_error_context(source: str, lineno: int | None) -> str:
    lines_list = source.splitlines()
    ln = (lineno or 1) - 1
    ctx_start = max(0, ln - 2)
    ctx_end = min(len(lines_list), ln + 3)
    return "\n".join(f"{i + 1:4d} | {lines_list[i]}" for i in range(ctx_start, ctx_end))


def format_execution_failure_summary(log: str, *, max_len: int = 700) -> str:
    """从完整执行日志抽取短摘要，避免 orchestrator 只取最后一行丢失 File/line 信息。"""
    text = (log or "").strip()
    if not text:
        return "执行失败（无日志）"
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    key_lines: list[str] = []
    for ln in lines:
        if 'File "' in ln and ", line " in ln:
            s = ln.strip()
            if s not in key_lines:
                key_lines.append(s)
    for ln in lines:
        low = ln.lower()
        if any(
            x in low
            for x in (
                "syntaxerror",
                "indentationerror",
                "taberror",
                "modulenotfounderror",
                "nameerror",
                "typeerror",
            )
        ):
            s = ln.strip()
            if s not in key_lines:
                key_lines.append(s)
    if not key_lines:
        key_lines = lines[-min(5, len(lines)) :]
    out = " | ".join(key_lines)
    if len(out) > max_len:
        out = out[: max_len - 1] + "…"
    return out


def execute_python_code(code: str, workdir: Path, script_name: str) -> ExecutionResult:
    workdir.mkdir(parents=True, exist_ok=True)
    script_path = workdir / script_name

    try:
        with script_path.open("w", encoding="utf-8") as file:
            if not code.startswith("# -*- coding: utf-8 -*-"):
                file.write("# -*- coding: utf-8 -*-\n")
            file.write(code)

        full_source = script_path.read_text(encoding="utf-8")
        try:
            ast.parse(full_source)
        except SyntaxError as se:
            ctx = _syntax_error_context(full_source, se.lineno)
            return ExecutionResult(
                success=False,
                log=(
                    f"语法错误（子进程未启动）: {se}\n"
                    f"--- 行 {se.lineno or '?'} 附近 ---\n{ctx}\n"
                    f"--- 脚本 ---\n{script_path}"
                ),
                script_path=script_path,
            )

        custom_env = os.environ.copy()
        custom_env["PYTHONIOENCODING"] = "utf-8"
        extra_pp = os.environ.get("PYSWASSEM_PYTHONPATH", "").strip()
        if extra_pp:
            prev = (custom_env.get("PYTHONPATH") or "").strip()
            custom_env["PYTHONPATH"] = os.pathsep.join([p for p in (extra_pp, prev) if p])

        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(workdir),
            capture_output=True,
            env=custom_env,
        )

        def safe_decode(payload: bytes) -> str:
            if not payload:
                return ""
            try:
                return payload.decode("utf-8")
            except UnicodeDecodeError:
                return payload.decode("gbk", errors="replace")

        stdout = safe_decode(result.stdout).strip()
        stderr = safe_decode(result.stderr).strip()

        if result.returncode == 0:
            return ExecutionResult(
                success=True,
                log=stdout or "Execution Successful. (No console output)",
                script_path=script_path,
            )

        blocks: list[str] = []
        if stderr:
            blocks.append("--- stderr ---\n" + stderr)
        if stdout:
            blocks.append("--- stdout ---\n" + stdout)
        error_log = "\n\n".join(blocks) if blocks else f"(no stderr/stdout) exit={result.returncode}"
        error_log = f"Execution Failed (exit={result.returncode}):\n{error_log}\n--- script ---\n{script_path}"

        # 子进程仍报语法错时，再解析一次文件给出稳定行号（应对编码/拼接差异）
        try:
            ast.parse(full_source)
        except SyntaxError as se2:
            error_log += (
                f"\n\n--- ast.parse(磁盘文件) ---\n{se2}\n"
                f"{_syntax_error_context(full_source, se2.lineno)}"
            )

        return ExecutionResult(
            success=False,
            log=error_log,
            script_path=script_path,
        )
    except Exception:
        return ExecutionResult(
            success=False,
            log=f"System Error during subprocess call:\n{traceback.format_exc()}",
            script_path=script_path,
        )


def run_basic_python_checks(code: str) -> list[str]:
    issues: list[str] = []
    try:
        ast.parse(code)
    except SyntaxError as exc:
        issues.append(f"HARD: Python 语法错误: line {exc.lineno}, offset {exc.offset}, {exc.msg}")
    return issues


def code_uses_save_path(code: str, expected_path: str) -> bool:
    normalized_code = code.replace("\\\\", "\\")
    normalized_path = expected_path.replace("\\\\", "\\")
    filename = Path(expected_path).name
    parent = str(Path(expected_path).parent).replace("\\\\", "\\")

    if normalized_path and normalized_path in normalized_code:
        return True

    has_save_call = "save_as(" in normalized_code
    mentions_filename = filename and filename in normalized_code
    mentions_parent = parent and parent in normalized_code
    mentions_path_variable = any(
        token in normalized_code
        for token in ("model_file", "model_path", "save_path", "output_path", "target_path")
    )
    uses_path_join = "os.path.join" in normalized_code or "Path(" in normalized_code

    return has_save_call and mentions_filename and (mentions_parent or mentions_path_variable or uses_path_join)


def run_part_plan_checks(full_plan: dict[str, Any], part_spec: dict[str, Any], code: str) -> list[str]:
    issues = run_basic_python_checks(code)

    workspace = part_spec.get("workspace", {})
    model_file = workspace.get("model_file", "")
    if model_file and not code_uses_save_path(code, model_file):
        issues.append("WARN: 代码中未能明确识别到 part_spec.workspace.model_file 对应的保存路径。")

    part_name = part_spec.get("name", "")
    if part_name and part_name not in code:
        issues.append("WARN: 代码中未显式体现零件名称，后续排查日志会较困难。")

    interface_names: list[str] = []
    interfaces = part_spec.get("interfaces", {})
    for category in ("faces", "axes", "points"):
        for item in interfaces.get(category, []) or []:
            name = item.get("name")
            if name:
                interface_names.append(name)

    if interface_names and not any(name in code for name in interface_names):
        issues.append("WARN: 代码中没有体现任何规划接口名称，可能无法支撑后续装配引用。")

    assembly_name = (
        full_plan.get("assembly", {}).get("name")
        if full_plan.get("request_type") == "assembly"
        else full_plan.get("name")
    )
    if assembly_name and assembly_name not in code:
        issues.append("WARN: 代码中未包含装配或任务名称，建议补充到日志或文件名相关代码中。")

    return issues


def run_assembly_plan_checks(plan: dict[str, Any], code: str) -> list[str]:
    issues = run_basic_python_checks(code)

    assembly = plan.get("assembly", {})
    assembly_output = assembly.get("assembly_output", {})
    model_file = assembly_output.get("model_file", "")
    if model_file and not code_uses_save_path(code, model_file):
        issues.append("WARN: 装配代码中未能明确识别到 assembly_output.model_file 对应的保存路径。")

    for part in assembly.get("parts", []):
        model_path = part.get("workspace", {}).get("model_file", "")
        if model_path and not code_uses_save_path(code, model_path) and Path(model_path).name not in code:
            issues.append(f"WARN: 装配代码中未显式使用零件路径: {model_path}")

    return issues
