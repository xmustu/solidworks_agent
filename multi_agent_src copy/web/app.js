const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const log = document.getElementById("chat-log");
const button = document.getElementById("send-button");
let sessionId = crypto.randomUUID();

function appendMessage(role, name, content) {
  const wrapper = document.createElement("article");
  wrapper.className = `message ${role}`;

  const meta = document.createElement("div");
  meta.className = "message-meta";
  meta.textContent = name;

  const body = document.createElement("div");
  body.className = "message-body";
  body.textContent = content;

  wrapper.append(meta, body);
  log.appendChild(wrapper);
  log.scrollTop = log.scrollHeight;
  return body;
}

function appendStatus(title, content) {
  return appendMessage("agent", title, content);
}

function setBusy(isBusy) {
  button.disabled = isBusy;
  input.disabled = isBusy;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message) return;

  appendMessage("user", "User", message);
  input.value = "";
  setBusy(true);

  let agentBody = null;

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Session-Id": sessionId,
      },
      body: JSON.stringify({
        message,
      }),
    });

    const returnedSessionId = response.headers.get("X-Session-Id");
    if (returnedSessionId) {
      sessionId = returnedSessionId;
    }

    if (!response.ok || !response.body) {
      const payload = await response.json().catch(() => ({ error: "请求失败" }));
      appendMessage("agent", "System", payload.error || "请求失败");
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.trim()) continue;
        const event = JSON.parse(line);
        if (event.type === "message_start" && event.agent_name) {
          agentBody = appendMessage("agent", event.agent_name, "");
        } else if (event.type === "delta") {
          if (!agentBody) {
            agentBody = appendMessage("agent", "Agent", "");
          }
          agentBody.textContent += event.content;
          log.scrollTop = log.scrollHeight;
        } else if (event.type === "status") {
          appendStatus("System", event.message || "");
        } else if (event.type === "execution_log") {
          appendStatus(event.title || "Execution Log", event.content || "");
        } else if (event.type === "error") {
          if (!agentBody) {
            agentBody = appendMessage("agent", "System", "");
          }
          agentBody.textContent += `\n\n[Error] ${event.error}`;
        } else if (event.type === "done") {
          setBusy(false);
          input.focus();
        }
      }
    }
  } catch (error) {
    appendMessage("agent", "System", `[Error] ${error.message}`);
  } finally {
    setBusy(false);
    input.focus();
  }
});
