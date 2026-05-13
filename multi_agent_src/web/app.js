const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const log = document.getElementById("chat-log");
const button = document.getElementById("send-button");

let sessionId = crypto.randomUUID();
const messageBodies = new Map();
let activeParallelPanel = null;

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
  scrollToBottom();
  return body;
}

function appendStatus(title, content) {
  return appendMessage("agent", title, content);
}

function scrollToBottom() {
  log.scrollTop = log.scrollHeight;
}

function setBusy(isBusy) {
  button.disabled = isBusy;
  input.disabled = isBusy;
}

function handleMessageStart(event) {
  const body = appendMessage("agent", event.agent_name || "Agent", "");
  if (event.message_id) {
    messageBodies.set(event.message_id, body);
  }
}

function handleDelta(event) {
  let body = event.message_id ? messageBodies.get(event.message_id) : null;
  if (!body) {
    body = appendMessage("agent", event.agent_name || "Agent", "");
    if (event.message_id) {
      messageBodies.set(event.message_id, body);
    }
  }
  body.textContent += event.content || "";
  scrollToBottom();
}

function handleMessageEnd(event) {
  if (event.message_id) {
    messageBodies.delete(event.message_id);
  }
}

function createParallelPanel(event) {
  const wrapper = document.createElement("article");
  wrapper.className = "message agent parallel-panel";

  const meta = document.createElement("div");
  meta.className = "message-meta";
  meta.textContent = "Parallel Parts";

  const title = document.createElement("div");
  title.className = "parallel-title";
  title.textContent = `零件并行任务 0/${event.total || 0}`;

  const bar = document.createElement("div");
  bar.className = "parallel-bar";
  const fill = document.createElement("div");
  fill.className = "parallel-bar-fill";
  bar.appendChild(fill);

  const list = document.createElement("div");
  list.className = "parallel-list";

  activeParallelPanel = {
    total: event.total || 0,
    done: 0,
    title,
    fill,
    list,
    items: new Map(),
  };

  (event.part_ids || []).forEach((partId) => {
    const row = document.createElement("div");
    row.className = "parallel-row pending";
    row.textContent = `${partId || "part"} · waiting`;
    activeParallelPanel.items.set(partId, row);
    list.appendChild(row);
  });

  wrapper.append(meta, title, bar, list);
  log.appendChild(wrapper);
  scrollToBottom();
}

function handleParallelPartDone(event) {
  if (!activeParallelPanel) {
    createParallelPanel({ total: 0, part_ids: [] });
  }

  activeParallelPanel.done += 1;
  const total = activeParallelPanel.total || activeParallelPanel.done;
  activeParallelPanel.title.textContent = `零件并行任务 ${activeParallelPanel.done}/${total}`;
  activeParallelPanel.fill.style.width = `${Math.min(100, (activeParallelPanel.done / total) * 100)}%`;

  let row = activeParallelPanel.items.get(event.part_id);
  if (!row) {
    row = document.createElement("div");
    activeParallelPanel.list.appendChild(row);
    activeParallelPanel.items.set(event.part_id, row);
  }

  row.className = `parallel-row ${event.success ? "success" : "failed"}`;
  row.textContent = `${event.name || event.part_id} · ${event.success ? "done" : "failed"}`;
  if (event.error) {
    row.textContent += ` · ${event.error}`;
  }
  scrollToBottom();
}

function handleParallelPartsEnd(event) {
  const results = event.results || [];
  const failed = results.filter((item) => !item.success);
  appendStatus(
    "Parallel Parts",
    failed.length
      ? `并行零件阶段完成，失败 ${failed.length}/${results.length}：${failed.map((item) => item.part_id).join(", ")}`
      : `并行零件阶段完成，成功 ${results.length}/${results.length}`
  );
}

function handleState(event) {
  const context = event.context && Object.keys(event.context).length
    ? `\n${JSON.stringify(event.context, null, 2)}`
    : "";
  appendStatus("State", `${event.state || ""}${context}`);
}

function handleToolResult(event) {
  const marker = event.success ? "ok" : "failed";
  appendStatus(`Tool · ${event.tool || "unknown"}`, `${marker}\n${event.content || ""}`);
}

function handleReviewResult(event) {
  const comments = event.comments_for_next_agent && event.comments_for_next_agent.length
    ? `\n\nComments:\n- ${event.comments_for_next_agent.join("\n- ")}`
    : "";
  appendStatus(
    `Review · ${event.scope || "check"}`,
    `${event.severity || (event.pass ? "pass" : "failed")}\n${event.feedback || ""}${comments}`
  );
}

function handleEvent(event) {
  if (event.type === "message_start" && event.agent_name) {
    handleMessageStart(event);
  } else if (event.type === "delta") {
    handleDelta(event);
  } else if (event.type === "message_end") {
    handleMessageEnd(event);
  } else if (event.type === "status") {
    appendStatus("System", event.message || "");
  } else if (event.type === "state") {
    handleState(event);
  } else if (event.type === "tool_result") {
    handleToolResult(event);
  } else if (event.type === "review_result") {
    handleReviewResult(event);
  } else if (event.type === "parallel_parts_start") {
    createParallelPanel(event);
  } else if (event.type === "parallel_part_done") {
    handleParallelPartDone(event);
  } else if (event.type === "parallel_parts_end") {
    handleParallelPartsEnd(event);
  } else if (event.type === "execution_log") {
    appendStatus(event.title || "Execution Log", event.content || "");
  } else if (event.type === "error") {
    appendStatus("System", `[Error] ${event.error || "Unknown error"}`);
  } else if (event.type === "done") {
    setBusy(false);
    input.focus();
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message) return;

  appendMessage("user", "User", message);
  input.value = "";
  setBusy(true);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Session-Id": sessionId,
      },
      body: JSON.stringify({ message }),
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
        handleEvent(JSON.parse(line));
      }
    }
  } catch (error) {
    appendMessage("agent", "System", `[Error] ${error.message}`);
  } finally {
    setBusy(false);
    input.focus();
  }
});
