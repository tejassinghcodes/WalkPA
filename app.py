"""
WalkPA final app.

This replaces the Gradio UI with a plain local web app so voice input/output is stable.

Run:
python app.py

Open:
http://127.0.0.1:7860

Features:
- Browser voice input using Chrome Web Speech API
- Browser voice output using speechSynthesis
- First-pass autonomous inbox action loop
- Follow-up conversational approval loop
"""

from __future__ import annotations

import json
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from agent import process_user_followup, run_agent


HOST = "127.0.0.1"
PORT = 7860

DEFAULT_COMMAND = (
    "I'm walking to work. Clear my inbox, draft replies, route admin or low-priority messages, "
    "schedule meetings, and tell me what you need from me."
)

DEFAULT_FOLLOWUP = (
    "Tell Rohan yes, I am okay with the latest version. For the contract, say I will review it "
    "this afternoon but I do not want to confirm anything yet."
)


HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>WalkPA</title>
  <style>
    :root {
      --bg: #0b1020;
      --panel: #121a2f;
      --panel2: #17203a;
      --text: #f8fafc;
      --muted: #a7b0c5;
      --green: #22c55e;
      --purple: #6366f1;
      --orange: #f97316;
      --border: rgba(148, 163, 184, 0.22);
      --danger: #ef4444;
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: radial-gradient(circle at top left, #18203b 0, #0b1020 34%, #070b16 100%);
      color: var(--text);
    }

    .wrap {
      max-width: 1180px;
      margin: 0 auto;
      padding: 30px 22px 70px;
    }

    .hero {
      display: grid;
      grid-template-columns: 1.4fr 0.8fr;
      gap: 18px;
      align-items: stretch;
      margin-bottom: 20px;
    }

    .card {
      background: linear-gradient(180deg, rgba(23, 32, 58, 0.96), rgba(13, 20, 38, 0.98));
      border: 1px solid var(--border);
      border-radius: 22px;
      box-shadow: 0 20px 70px rgba(0, 0, 0, 0.25);
      padding: 22px;
    }

    h1 {
      margin: 0 0 8px;
      font-size: 42px;
      line-height: 1;
      letter-spacing: -0.04em;
    }

    h2 {
      margin: 0 0 14px;
      font-size: 21px;
      letter-spacing: -0.02em;
    }

    p {
      color: var(--muted);
      line-height: 1.6;
    }

    .tagline {
      font-size: 18px;
      margin: 0;
    }

    .pillrow {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 18px;
    }

    .pill {
      border: 1px solid var(--border);
      background: rgba(255,255,255,0.04);
      padding: 8px 12px;
      border-radius: 999px;
      color: #dbeafe;
      font-size: 13px;
      font-weight: 700;
    }

    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
      margin-top: 18px;
    }

    textarea, input, select {
      width: 100%;
      border: 1px solid var(--border);
      background: #0b1224;
      color: var(--text);
      border-radius: 14px;
      padding: 14px;
      font-size: 15px;
      line-height: 1.5;
      outline: none;
    }

    textarea:focus, input:focus, select:focus {
      border-color: rgba(99, 102, 241, 0.8);
      box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.12);
    }

    .controls {
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
      margin-top: 12px;
    }

    button {
      border: none;
      border-radius: 999px;
      padding: 12px 18px;
      font-weight: 900;
      cursor: pointer;
      color: white;
      background: var(--purple);
      transition: transform 0.08s ease, opacity 0.12s ease;
    }

    button:hover { transform: translateY(-1px); }
    button:disabled { opacity: 0.6; cursor: not-allowed; }

    .green { background: var(--green); }
    .orange { background: var(--orange); }
    .ghost {
      background: transparent;
      border: 1px solid var(--border);
      color: var(--text);
    }

    .status {
      color: var(--muted);
      font-size: 14px;
      margin-left: 4px;
    }

    .brief {
      font-size: 18px;
      line-height: 1.58;
      color: #f8fafc;
      background: rgba(99, 102, 241, 0.10);
      border: 1px solid rgba(99, 102, 241, 0.26);
      border-radius: 18px;
      padding: 18px;
      min-height: 110px;
    }

    .section-title {
      margin-top: 22px;
      margin-bottom: 10px;
      color: white;
      font-size: 18px;
      font-weight: 900;
    }

    .list {
      display: grid;
      gap: 10px;
    }

    .item {
      border: 1px solid var(--border);
      background: rgba(255,255,255,0.035);
      border-radius: 16px;
      padding: 14px;
    }

    .item strong { color: white; }

    .meta {
      color: var(--muted);
      font-size: 13px;
      margin-top: 6px;
      line-height: 1.45;
    }

    .done { color: #86efac; font-weight: 900; }
    .prepared { color: #fde68a; font-weight: 900; }
    .question { color: #fca5a5; font-weight: 900; }

    pre {
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      background: #050816;
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 14px;
      color: #dbeafe;
      max-height: 360px;
      overflow: auto;
    }

    .mini {
      font-size: 13px;
      color: var(--muted);
    }

    .modebox {
      display: grid;
      gap: 12px;
      align-content: start;
    }

    label {
      font-size: 14px;
      color: #dbeafe;
      font-weight: 800;
      display: block;
      margin-bottom: 8px;
    }

    .checkbox {
      display: flex;
      align-items: center;
      gap: 10px;
      color: white;
      font-weight: 800;
    }

    .checkbox input {
      width: auto;
      transform: scale(1.2);
    }

    @media (max-width: 900px) {
      .hero, .grid { grid-template-columns: 1fr; }
      h1 { font-size: 34px; }
    }
  </style>
</head>

<body>
  <div class="wrap">
    <div class="hero">
      <div class="card">
        <h1>WalkPA</h1>
        <p class="tagline">A voice-first personal assistant that clears your Gmail and Calendar while you are walking.</p>
        <div class="pillrow">
          <span class="pill">triage</span>
          <span class="pill">draft</span>
          <span class="pill">route</span>
          <span class="pill">schedule</span>
          <span class="pill">ask follow-ups</span>
          <span class="pill">send after approval</span>
        </div>
      </div>
      <div class="card modebox">
        <div>
          <label>Mode</label>
          <select id="mode">
            <option value="autopilot" selected>autopilot - act on reversible tasks</option>
            <option value="intervention">intervention - prepare only</option>
          </select>
        </div>
        <div>
          <label>Recent emails</label>
          <input id="maxEmails" type="number" min="1" max="30" value="15" />
        </div>
        <p class="mini">Autopilot creates drafts, labels emails, and creates Calendar holds with Meet links. It only sends replies after your follow-up approval.</p>
      </div>
    </div>

    <div class="grid">
      <div class="card">
        <h2>1. First pass</h2>
        <p class="mini">Say the command while walking. WalkPA handles what it can and asks only for missing decisions.</p>
        <label>Command</label>
        <textarea id="command" rows="5">__DEFAULT_COMMAND__</textarea>
        <div class="controls">
          <button class="green" onclick="startVoice('command', 'status1')">🎙️ Speak command</button>
          <button class="ghost" onclick="stopVoice()">Stop</button>
          <button class="orange" id="firstBtn" onclick="runFirstPass()">Run PA first pass</button>
          <span class="status" id="status1">Ready.</span>
        </div>
      </div>

      <div class="card">
        <h2>2. Follow-up answer</h2>
        <p class="mini">Answer only what WalkPA asked you. It will draft or send the approved follow-ups.</p>
        <label>Follow-up / approvals</label>
        <textarea id="followup" rows="5">__DEFAULT_FOLLOWUP__</textarea>
        <div class="controls">
          <button class="green" onclick="startVoice('followup', 'status2')">🎙️ Speak follow-up</button>
          <button class="ghost" onclick="stopVoice()">Stop</button>
          <label class="checkbox"><input id="sendApproved" type="checkbox" checked /> Send approved follow-up replies</label>
          <button id="followBtn" onclick="runFollowup()">Process follow-up</button>
          <span class="status" id="status2">Ready.</span>
        </div>
      </div>
    </div>

    <div class="card" style="margin-top:18px;">
      <h2>PA briefing</h2>
      <div id="briefing" class="brief">Run the first pass to get a spoken PA briefing.</div>
      <div class="controls">
        <button onclick="speak(document.getElementById('briefing').innerText)">🔊 Speak briefing</button>
        <button class="ghost" onclick="window.speechSynthesis.cancel()">Stop speaking</button>
      </div>
    </div>

    <div class="grid">
      <div class="card">
        <h2>What WalkPA found</h2>
        <div id="triage" class="list"></div>
      </div>
      <div class="card">
        <h2>Actions taken / prepared</h2>
        <div id="actions" class="list"></div>
      </div>
    </div>

    <div class="card" style="margin-top:18px;">
      <h2>What WalkPA needs from you</h2>
      <div id="questions" class="list"></div>
    </div>

    <div class="card" style="margin-top:18px;">
      <h2>Follow-up result</h2>
      <div id="followupResult" class="list"></div>
    </div>

    <div class="card" style="margin-top:18px;">
      <h2>Raw JSON</h2>
      <pre id="raw">{}</pre>
    </div>
  </div>

<script>
const DEFAULT_COMMAND = "__DEFAULT_COMMAND__";

let recognition = null;

function speak(text) {
  if (!text || !text.trim()) return;
  window.speechSynthesis.cancel();
  const msg = new SpeechSynthesisUtterance(text);
  msg.rate = 1.06;
  msg.pitch = 1.0;
  msg.volume = 1.0;
  window.speechSynthesis.speak(msg);
}

function startVoice(targetId, statusId) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const status = document.getElementById(statusId);

  if (!SpeechRecognition) {
    status.innerText = "Speech recognition is not available. Use Chrome, or press Win + H.";
    return;
  }

  stopVoice();

  let finalTranscript = "";
  recognition = new SpeechRecognition();
  recognition.lang = "en-AU";
  recognition.interimResults = true;
  recognition.continuous = true;

  recognition.onstart = () => {
    status.innerText = "Listening...";
  };

  recognition.onresult = (event) => {
    let interim = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const txt = event.results[i][0].transcript;
      if (event.results[i].isFinal) finalTranscript += txt + " ";
      else interim += txt;
    }
    const combined = (finalTranscript + interim).trim();
    if (combined) {
      document.getElementById(targetId).value = combined;
      status.innerText = "Captured: " + combined;
    }
  };

  recognition.onerror = (event) => {
    status.innerText = "Voice error: " + event.error + ". You can type or use Win + H.";
  };

  recognition.onend = () => {
    status.innerText = "Voice stopped. Click run when ready.";
  };

  recognition.start();
}

function stopVoice() {
  if (recognition) {
    recognition.stop();
    recognition = null;
  }
}

function itemHtml(title, body, cls="") {
  return `<div class="item"><strong class="${cls}">${escapeHtml(title)}</strong><div class="meta">${escapeHtml(body)}</div></div>`;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, s => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;"
  }[s]));
}

function renderFirstPass(data) {
  const briefing = data.plan?.spoken_summary || data.spoken_summary || "No briefing returned.";
  document.getElementById("briefing").innerText = briefing;
  speak(briefing);

  const triage = data.triage || data.plan?.triage || [];
  document.getElementById("triage").innerHTML = triage.map(x =>
    itemHtml(`${(x.category || "").toUpperCase()} — ${x.subject || ""}`, `From: ${x.from || ""}\nReason: ${x.reason || ""}`)
  ).join("") || itemHtml("No triage", "");

  const exec = data.execution_results || [];
  document.getElementById("actions").innerHTML = exec.map(x => {
    const title = `${x.executed ? "DONE" : "PREPARED"} — ${x.action_type || ""}`;
    const detail = typeof x.detail === "object" ? JSON.stringify(x.detail, null, 2) : (x.detail || x.error || "");
    return itemHtml(title, `Reason: ${x.reason || ""}\n${detail}`, x.executed ? "done" : "prepared");
  }).join("") || itemHtml("No actions", "");

  const questions = data.questions || [];
  document.getElementById("questions").innerHTML = questions.map(q =>
    itemHtml(q.question || "Input needed", q.reason || "", "question")
  ).join("") || itemHtml("No follow-up needed", "WalkPA has enough information.");

  document.getElementById("raw").innerText = JSON.stringify(data, null, 2);
}

function renderFollowup(data) {
  const briefing = data.spoken_summary || "Follow-up processed.";
  document.getElementById("briefing").innerText = briefing;
  speak(briefing);

  const results = data.sent_results || [];
  document.getElementById("followupResult").innerHTML = results.map(x =>
    itemHtml(`${(x.action || "").toUpperCase()} — ${x.original_subject || ""}`, JSON.stringify(x.result || x, null, 2), "done")
  ).join("") || itemHtml("No follow-up actions", briefing);

  document.getElementById("raw").innerText = JSON.stringify(data, null, 2);
}

async function postJson(url, payload) {
  const res = await fetch(url, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });

  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

async function runFirstPass() {
  const btn = document.getElementById("firstBtn");
  btn.disabled = true;
  btn.innerText = "Running...";
  document.getElementById("briefing").innerText = "WalkPA is scanning Gmail and Calendar...";
  try {
    const data = await postJson("/api/first-pass", {
      command: document.getElementById("command").value || DEFAULT_COMMAND,
      mode: document.getElementById("mode").value,
      max_emails: Number(document.getElementById("maxEmails").value || 15)
    });
    renderFirstPass(data);
  } catch (e) {
    document.getElementById("briefing").innerText = "Error: " + e.message;
    speak("WalkPA hit an error. Check the screen.");
  } finally {
    btn.disabled = false;
    btn.innerText = "Run PA first pass";
  }
}

async function runFollowup() {
  const btn = document.getElementById("followBtn");
  btn.disabled = true;
  btn.innerText = "Processing...";
  try {
    const data = await postJson("/api/follow-up", {
      user_reply: document.getElementById("followup").value,
      send_approved: document.getElementById("sendApproved").checked
    });
    renderFollowup(data);
  } catch (e) {
    document.getElementById("followupResult").innerHTML = itemHtml("Error", e.message, "question");
    speak("Follow up failed. Check the screen.");
  } finally {
    btn.disabled = false;
    btn.innerText = "Process follow-up";
  }
}
</script>
</body>
</html>
""".replace("__DEFAULT_COMMAND__", DEFAULT_COMMAND).replace("__DEFAULT_FOLLOWUP__", DEFAULT_FOLLOWUP)


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self):
        body = HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw or "{}")

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html()
        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        try:
            parsed = urlparse(self.path)
            data = self._read_json()

            if parsed.path == "/api/first-pass":
                result = run_agent(
                    command=data.get("command") or DEFAULT_COMMAND,
                    mode=data.get("mode") or "autopilot",
                    max_emails=int(data.get("max_emails") or 15),
                    execute=True,
                )
                self._send_json(200, result)
                return

            if parsed.path == "/api/follow-up":
                result = process_user_followup(
                    user_reply=data.get("user_reply") or DEFAULT_FOLLOWUP,
                    send_approved=bool(data.get("send_approved")),
                )
                self._send_json(200, result)
                return

            self._send_json(404, {"error": "Not found"})

        except Exception as exc:
            traceback.print_exc()
            self._send_json(500, {"error": str(exc), "traceback": traceback.format_exc()})


if __name__ == "__main__":
    url = f"http://{HOST}:{PORT}"
    print(f"WalkPA running at {url}")
    print("Use Chrome for voice input/output. If voice input fails, click the box and press Win + H.")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
