from __future__ import annotations

import os
import subprocess
import sys
import threading
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass
class ToolResult:
    success: bool
    tool: str
    content: str
    data: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "tool": self.tool,
            "content": self.content,
            "data": self.data,
        }


SOLIDWORKS_CALL_LOCK = threading.Lock()


class AgentToolExecutor:
    def __init__(
        self,
        workspace_roots: list[Path],
        knowledge_base_root: Path,
        previous_attempts: dict[str, list[dict[str, Any]]] | None = None,
        event_callback: Callable[[dict[str, Any]], None] | None = None,
        max_payload_chars: int = 12000,
    ) -> None:
        self.workspace_roots = [root.resolve() for root in workspace_roots]
        self.knowledge_base_root = knowledge_base_root.resolve()
        self.previous_attempts = previous_attempts if previous_attempts is not None else {}
        self.event_callback = event_callback
        self.max_payload_chars = max_payload_chars

    def execute(self, action: dict[str, Any]) -> ToolResult:
        tool = str(action.get("tool", "")).strip()
        args = action.get("args") or {}
        if not isinstance(args, dict):
            return self._error(tool, "Tool args must be an object.")

        handlers = {
            "read_file": self.read_file,
            "write_file": self.write_file,
            "run_python": self.run_python,
            "list_dir": self.list_dir,
            "search_in_kb": self.search_in_kb,
            "load_previous_attempt": self.load_previous_attempt,
            "summarize_log": self.summarize_log,
            "run_solidworks_pipeline": self.run_solidworks_pipeline,
        }
        handler = handlers.get(tool)
        if handler is None:
            return self._error(tool, f"Unknown tool: {tool}")

        try:
            result = handler(**args)
        except TypeError as exc:
            result = self._error(tool, f"Invalid args for {tool}: {exc}")
        except Exception:
            result = self._error(tool, f"Tool crashed:\n{traceback.format_exc()}")

        if self.event_callback is not None:
            self.event_callback(
                {
                    "type": "tool_result",
                    "tool": tool,
                    "success": result.success,
                    "content": result.content[: self.max_payload_chars],
                    "data": result.data,
                }
            )
        return result

    def read_file(self, path: str) -> ToolResult:
        file_path = self._resolve_allowed_path(path, must_exist=True)
        if not file_path.is_file():
            return self._error("read_file", f"Not a file: {file_path}")
        text = self._truncate(file_path.read_text(encoding="utf-8", errors="replace"))
        return ToolResult(True, "read_file", text, {"path": str(file_path)})

    def write_file(self, path: str, content: str) -> ToolResult:
        file_path = self._resolve_allowed_path(path, must_exist=False)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(str(content), encoding="utf-8")
        return ToolResult(
            True,
            "write_file",
            f"Wrote {len(str(content))} chars to {file_path}",
            {"path": str(file_path), "bytes": file_path.stat().st_size},
        )

    def run_python(self, script_path: str) -> ToolResult:
        file_path = self._resolve_allowed_path(script_path, must_exist=True)
        if not file_path.is_file():
            return self._error("run_python", f"Not a Python script: {file_path}")

        result = self._run_python_script(file_path)
        log = result["stdout"] if result["returncode"] == 0 else (result["stderr"] or result["stdout"])
        if not log:
            log = "Execution Successful. (No console output)"
        return ToolResult(
            result["returncode"] == 0,
            "run_python",
            self._truncate(log),
            {"path": str(file_path), "returncode": result["returncode"]},
        )

    def run_solidworks_pipeline(
        self,
        script_path: str,
        screenshot_dir: str,
        screenshot_base_name: str = "active_model",
        width: int = 1600,
        height: int = 1200,
        delay: float = 0.3,
    ) -> ToolResult:
        file_path = self._resolve_allowed_path(script_path, must_exist=True)
        shot_dir = self._resolve_allowed_path(screenshot_dir, must_exist=False)
        if not file_path.is_file():
            return self._error("run_solidworks_pipeline", f"Not a Python script: {file_path}")

        with SOLIDWORKS_CALL_LOCK:
            clear_result = self._run_inline_python(
                """
from pysw import SldWorksApp

swapp = SldWorksApp(close_before_task=True)
print("SolidWorks initialized with close_before_task=True")
""",
                cwd=file_path.parent,
            )
            execute_result = self._run_python_script(file_path)
            shot_dir.mkdir(parents=True, exist_ok=True)
            screenshot_result = self._run_inline_python(
                f"""
from pathlib import Path
from pysw import SldWorksApp

swapp = SldWorksApp(close_before_task=False)
print("SolidWorks initialized with close_before_task=False")

sw_app = SldWorksApp()
out_dir = r{str(shot_dir)!r}
Path(out_dir).mkdir(parents=True, exist_ok=True)
shots = sw_app.capture_active_model_views(
    output_dir=out_dir,
    base_name={str(screenshot_base_name)!r},
    width={int(width)},
    height={int(height)},
    delay={float(delay)},
)
print("===== Screenshot Result =====")
if not shots:
    print("No screenshots were generated. Confirm SOLIDWORKS has an active part or assembly.")
else:
    for shot in shots:
        print(shot)
""",
                cwd=shot_dir,
            )

        screenshots = [
            str(path)
            for path in sorted(shot_dir.glob(f"{screenshot_base_name}*"))
            if path.is_file()
        ]
        success = (
            clear_result["returncode"] == 0
            and execute_result["returncode"] == 0
            and screenshot_result["returncode"] == 0
            and bool(screenshots)
        )
        content = "\n\n".join(
            [
                "===== Clear SolidWorks =====",
                self._format_process_result(clear_result),
                "===== Execute Script =====",
                self._format_process_result(execute_result),
                "===== Capture Screenshots =====",
                self._format_process_result(screenshot_result),
                "===== Screenshot Files =====",
                "\n".join(screenshots) if screenshots else "(none)",
            ]
        )
        return ToolResult(
            success,
            "run_solidworks_pipeline",
            self._truncate(content),
            {
                "script_path": str(file_path),
                "screenshot_dir": str(shot_dir),
                "screenshots": screenshots,
                "clear_returncode": clear_result["returncode"],
                "execute_returncode": execute_result["returncode"],
                "screenshot_returncode": screenshot_result["returncode"],
            },
        )

    def list_dir(self, path: str) -> ToolResult:
        dir_path = self._resolve_allowed_path(path, must_exist=True)
        if not dir_path.is_dir():
            return self._error("list_dir", f"Not a directory: {dir_path}")
        entries = []
        for child in sorted(dir_path.iterdir(), key=lambda item: item.name.lower()):
            entries.append(
                {
                    "name": child.name,
                    "path": str(child),
                    "type": "dir" if child.is_dir() else "file",
                    "bytes": child.stat().st_size if child.is_file() else None,
                }
            )
        return ToolResult(True, "list_dir", self._truncate(str(entries)), {"path": str(dir_path), "entries": entries})

    def search_in_kb(self, query: str) -> ToolResult:
        terms = [term.lower() for term in str(query).split() if term.strip()]
        if not terms:
            return self._error("search_in_kb", "query must contain at least one term.")

        matches: list[dict[str, str]] = []
        for path in sorted(self.knowledge_base_root.rglob("*")):
            if not path.is_file() or path.name.startswith("."):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            lowered = text.lower()
            if not all(term in lowered for term in terms):
                continue
            first_index = min(lowered.find(term) for term in terms if lowered.find(term) != -1)
            start = max(0, first_index - 300)
            end = min(len(text), first_index + 700)
            matches.append({"path": str(path), "snippet": text[start:end].strip()})
            if len(matches) >= 5:
                break

        content = "\n\n".join(f"# {item['path']}\n{item['snippet']}" for item in matches)
        return ToolResult(True, "search_in_kb", self._truncate(content or "No matches."), {"matches": matches})

    def load_previous_attempt(self, part_id: str) -> ToolResult:
        attempts = self.previous_attempts.get(str(part_id), [])
        if not attempts:
            return ToolResult(True, "load_previous_attempt", "No previous attempts.", {"part_id": part_id, "attempts": []})
        latest = attempts[-1]
        return ToolResult(True, "load_previous_attempt", self._truncate(str(latest)), {"part_id": part_id, "latest": latest})

    def summarize_log(self, log: str) -> ToolResult:
        lines = str(log).splitlines()
        important = [
            line
            for line in lines
            if any(marker in line.lower() for marker in ("error", "exception", "traceback", "failed", "warn"))
        ]
        selected = important[-20:] if important else lines[-20:]
        summary = "\n".join(selected).strip() or "(empty log)"
        return ToolResult(True, "summarize_log", self._truncate(summary), {"line_count": len(lines)})

    def _resolve_allowed_path(self, raw_path: str, must_exist: bool) -> Path:
        path = Path(str(raw_path)).expanduser()
        if not path.is_absolute():
            path = self.workspace_roots[0] / path
        resolved = path.resolve()
        allowed_roots = [*self.workspace_roots, self.knowledge_base_root]
        if not any(self._is_relative_to(resolved, root) for root in allowed_roots):
            raise ValueError(f"Path is outside allowed roots: {resolved}")
        if must_exist and not resolved.exists():
            raise FileNotFoundError(str(resolved))
        return resolved

    def _is_relative_to(self, path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False

    def _truncate(self, text: str) -> str:
        if len(text) <= self.max_payload_chars:
            return text
        return text[: self.max_payload_chars] + "\n...[truncated]"

    def _safe_decode(self, payload: bytes) -> str:
        if not payload:
            return ""
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError:
            return payload.decode("gbk", errors="replace")

    def _run_python_script(self, script_path: Path) -> dict[str, Any]:
        custom_env = os.environ.copy()
        custom_env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(script_path.parent),
            capture_output=True,
            env=custom_env,
        )
        return {
            "returncode": result.returncode,
            "stdout": self._safe_decode(result.stdout).strip(),
            "stderr": self._safe_decode(result.stderr).strip(),
        }

    def _run_inline_python(self, code: str, cwd: Path) -> dict[str, Any]:
        custom_env = os.environ.copy()
        custom_env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(cwd),
            capture_output=True,
            env=custom_env,
        )
        return {
            "returncode": result.returncode,
            "stdout": self._safe_decode(result.stdout).strip(),
            "stderr": self._safe_decode(result.stderr).strip(),
        }

    def _format_process_result(self, result: dict[str, Any]) -> str:
        stdout = result.get("stdout") or ""
        stderr = result.get("stderr") or ""
        return f"returncode={result.get('returncode')}\nSTDOUT:\n{stdout or '(empty)'}\nSTDERR:\n{stderr or '(empty)'}"

    def _error(self, tool: str, message: str) -> ToolResult:
        return ToolResult(False, tool or "unknown", message, {})
