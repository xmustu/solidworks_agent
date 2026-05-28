from __future__ import annotations

import json
import logging
import os
import queue
import sys
import threading
import time
import traceback
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4


def _configure_logging() -> logging.Logger:
    log = logging.getLogger("solidworks_agent.web_demo")
    if log.handlers:
        return log
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    log.propagate = False
    return log


LOG = _configure_logging()

try:
    from .agents import extract_json_payload
    from .orchestrator import MultiAgentOrchestrator
except ImportError:
    from agents import extract_json_payload
    from orchestrator import MultiAgentOrchestrator


WEB_ROOT = Path(__file__).resolve().parent / "web"
SESSION_LOCK = threading.Lock()
SESSIONS: dict[str, "DemoConversationSession"] = {}


class DemoConversationSession:
    def __init__(self):
        self.event_queue: queue.Queue[dict] = queue.Queue()
        self.orchestrator = MultiAgentOrchestrator(event_callback=self.push_event)
        self.stage = "requirement"

    def push_event(self, event: dict):
        et = event.get("type") if isinstance(event, dict) else None
        LOG.debug("push_event type=%s keys=%s", et, list(event.keys()) if isinstance(event, dict) else None)
        self.event_queue.put(event)

    def iter_turn_events(self, user_message: str):
        if self.stage == "requirement":
            if self.orchestrator.can_handle_followup_modification(user_message):
                self.stage = "executing"
                yield {
                    "type": "status",
                    "message": "检测到这是基于当前零件的小幅修改，将复用上一轮工作目录并直接进入零件修改智能体。",
                }
                yield from self._run_followup_modification(user_message)
                self.stage = "requirement"
                yield {
                    "type": "status",
                    "message": "本轮修改流程已完成，可以继续输入新需求或继续修改当前模型。",
                }
                return

            message_id = uuid4().hex
            yield {"type": "message_start", "role": "agent", "agent_name": "RequirementAgent", "message_id": message_id}
            for chunk in self.orchestrator.requirement_agent.stream_chat(user_message):
                yield {"type": "delta", "content": chunk, "message_id": message_id}
            yield {"type": "message_end", "message_id": message_id}

            latest_reply = self.orchestrator.requirement_agent.history[-1]["content"]
            if "[CONFIRMED]" not in latest_reply:
                LOG.info("requirement_not_confirmed_no_pipeline")
                return

            try:
                requirement_payload = extract_json_payload(latest_reply)
            except ValueError:
                LOG.warning(
                    "requirement_json_parse_failed reply_preview=%r",
                    latest_reply[:800],
                )
                yield {
                    "type": "status",
                    "message": "需求分析阶段已确认，但确认消息中的 JSON 无法解析，后续流程未启动。",
                }
                return

            LOG.info(
                "requirement_confirmed request_type=%s",
                requirement_payload.get("request_type"),
            )
            self.stage = "executing"
            yield from self._run_pipeline(requirement_payload)
            self.stage = "requirement"
            yield {
                "type": "status",
                "message": "本轮自动流程已完成，可以继续输入新需求或补充修改内容，系统会重新判断需要调用的智能体。",
            }
            return

        if self.stage == "executing":
            LOG.info("turn_blocked stage=executing")
            yield {
                "type": "status",
                "message": "当前任务仍在执行中，请等待本轮自动流程完成。",
            }
            return

        if self.stage == "finished":
            self.stage = "requirement"
            yield {
                "type": "status",
                "message": "当前会话已回到需求判断阶段，请继续输入需求。",
            }

    def _run_pipeline(self, requirement_payload: dict):
        sentinel = {"type": "_pipeline_done"}

        def worker():
            try:
                LOG.info("pipeline_worker_start payload_keys=%s", list(requirement_payload.keys()))
                self.orchestrator.process_confirmed_requirement(requirement_payload)
            except Exception as exc:
                self.push_event({"type": "error", "error": str(exc)})
            finally:
                self.push_event(sentinel)

        threading.Thread(target=worker, daemon=True).start()

        while True:
            event = self.event_queue.get()
            if event is sentinel or event.get("type") == "_pipeline_done":
                break
            yield event

    def _run_followup_modification(self, user_message: str):
        sentinel = {"type": "_pipeline_done"}

        def worker():
            try:
                handled = self.orchestrator.process_followup_modification(user_message)
                if not handled:
                    self.push_event({"type": "status", "message": "未找到可复用的当前零件，将回到需求分析。"})
            except Exception as exc:
                self.push_event({"type": "error", "error": str(exc)})
            finally:
                self.push_event(sentinel)

        threading.Thread(target=worker, daemon=True).start()

        while True:
            event = self.event_queue.get()
            if event is sentinel or event.get("type") == "_pipeline_done":
                break
            yield event


def get_or_create_session(session_id: str | None) -> tuple[str, DemoConversationSession]:
    if not session_id:
        session_id = uuid4().hex

    with SESSION_LOCK:
        session = SESSIONS.get(session_id)
        if session is None:
            session = DemoConversationSession()
            SESSIONS[session_id] = session
    return session_id, session


class DemoHandler(BaseHTTPRequestHandler):
    server_version = "MultiAgentDemo/3.0"

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.serve_file("index.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/app.css":
            self.serve_file("app.css", "text/css; charset=utf-8")
            return
        if parsed.path == "/app.js":
            self.serve_file("app.js", "application/javascript; charset=utf-8")
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path not in {"/api/chat", "/api/chat-sse"}:
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        user_message, session_id, session = self.parse_chat_request()
        if user_message is None or session_id is None or session is None:
            LOG.warning("post_%s_bad_request path=%s", parsed.path.strip("/"), self.path)
            return

        LOG.info(
            "post_%s session_id=%s msg_len=%d client=%s",
            parsed.path.strip("/"),
            session_id,
            len(user_message),
            self.address_string(),
        )
        if parsed.path == "/api/chat-sse":
            self.stream_sse_events(session_id, session, user_message)
            return

        self.stream_jsonl_events(session_id, session, user_message)

    def parse_chat_request(self) -> tuple[str | None, str | None, DemoConversationSession | None]:
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8") if length else "{}"

        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            self.send_json({"error": "Request body must be valid JSON."}, status=HTTPStatus.BAD_REQUEST)
            return None, None, None

        user_message = str(payload.get("message", "")).strip()
        if not user_message:
            self.send_json({"error": "Message cannot be empty."}, status=HTTPStatus.BAD_REQUEST)
            return None, None, None

        session_id, session = get_or_create_session(self.headers.get("X-Session-Id"))
        return user_message, session_id, session

    def stream_jsonl_events(self, session_id: str, session: DemoConversationSession, user_message: str) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("X-Session-Id", session_id)
        self.end_headers()
        self.close_connection = True

        try:
            for event in session.iter_turn_events(user_message):
                line = json.dumps(event, ensure_ascii=False) + "\n"
                self.wfile.write(line.encode("utf-8"))
                self.wfile.flush()

            done = json.dumps({"type": "done"}, ensure_ascii=False) + "\n"
            self.wfile.write(done.encode("utf-8"))
            self.wfile.flush()
        except Exception as exc:
            error_line = json.dumps({"type": "error", "error": str(exc)}, ensure_ascii=False) + "\n"
            try:
                self.wfile.write(error_line.encode("utf-8"))
                self.wfile.flush()
            except BrokenPipeError:
                pass

    def stream_sse_events(self, session_id: str, session: DemoConversationSession, user_message: str) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.send_header("X-Session-Id", session_id)
        self.end_headers()
        self.close_connection = True

        t0 = time.perf_counter()
        n_events = 0
        try:
            for event in session.iter_turn_events(user_message):
                n_events += 1
                self.write_sse_event("message", event)

            self.write_sse_event("message", {"type": "done"})
            LOG.info(
                "sse_complete session_id=%s events=%d elapsed_s=%.2f",
                session_id,
                n_events,
                time.perf_counter() - t0,
            )
        except Exception as exc:
            LOG.exception("sse_handler_error session_id=%s: %s", session_id, exc)
            try:
                self.write_sse_event("message", {"type": "error", "error": str(exc)})
            except BrokenPipeError:
                pass

    def write_sse_event(self, event_name: str, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False)
        message = f"event: {event_name}\ndata: {body}\n\n"
        self.wfile.write(message.encode("utf-8"))
        self.wfile.flush()

    def serve_file(self, filename: str, content_type: str):
        path = WEB_ROOT / filename
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        content = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        self.wfile.write(body)

    def log_message(self, format: str, *args):
        LOG.info("http %s - %s", self.address_string(), format % args if args else format)


def run(host: str = "127.0.0.1", port: int = 8500):
    pp = os.environ.get("PYSWASSEM_PYTHONPATH", "").strip()
    if pp:
        LOG.info("PYSWASSEM_PYTHONPATH=%s (子进程建模脚本将前置此路径)", pp)
    else:
        LOG.info(
            "未设置 PYSWASSEM_PYTHONPATH；若子进程报 ModuleNotFoundError: pyswassem，"
            "请设为包含该包的目录（可与生成代码中的 sys.path 一致）。"
        )
    server = ThreadingHTTPServer((host, port), DemoHandler)
    print(f"Multi-agent demo server running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
