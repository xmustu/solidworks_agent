from __future__ import annotations

import json
import queue
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

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
        self.event_queue.put(event)

    def iter_turn_events(self, user_message: str):
        if self.stage == "requirement":
            yield {"type": "message_start", "role": "agent", "agent_name": "RequirementAgent"}
            for chunk in self.orchestrator.requirement_agent.stream_chat(user_message):
                yield {"type": "delta", "content": chunk}
            yield {"type": "message_end"}

            latest_reply = self.orchestrator.requirement_agent.history[-1]["content"]
            if "[CONFIRMED]" not in latest_reply:
                return

            try:
                requirement_payload = extract_json_payload(latest_reply)
            except ValueError:
                yield {
                    "type": "status",
                    "message": "需求分析阶段已确认，但确认消息中的 JSON 无法解析，后续流程未启动。",
                }
                return

            self.stage = "executing"
            yield from self._run_pipeline(requirement_payload)
            self.stage = "finished"
            return

        if self.stage == "executing":
            yield {
                "type": "status",
                "message": "当前任务仍在执行中，请等待本轮自动流程完成。",
            }
            return

        if self.stage == "finished":
            yield {
                "type": "status",
                "message": "当前会话的自动流程已完成。如需重新开始，请刷新页面开启新会话。",
            }

    def _run_pipeline(self, requirement_payload: dict):
        sentinel = {"type": "_pipeline_done"}

        def worker():
            try:
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
            return

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

        try:
            for event in session.iter_turn_events(user_message):
                self.write_sse_event("message", event)

            self.write_sse_event("message", {"type": "done"})
        except Exception as exc:
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
        return


def run(host: str = "127.0.0.1", port: int = 8000):
    server = ThreadingHTTPServer((host, port), DemoHandler)
    print(f"Multi-agent demo server running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
