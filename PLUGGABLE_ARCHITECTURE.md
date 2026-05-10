# WalkPA Pluggable Architecture

WalkPA is a voice-first communications agent for Gmail, Google Calendar, and Google Meet.

The core product idea is simple:

> A user speaks while walking or commuting. WalkPA clears the communication queue by triaging messages, drafting replies, routing emails, scheduling meetings, asking for missing decisions, and completing approved follow-ups.

This document explains how WalkPA can be plugged into other agent runtimes such as Claude, n8n, MCP servers, LangGraph, CrewAI, Zapier, or internal workflow systems.

---

## 1. Current architecture

WalkPA is currently built as a local Python application with direct tool adapters.

```text
Browser UI / voice command
        ↓
WalkPA agent loop
        ↓
Safety router
        ↓
Tool adapters
        ├── Gmail tools
        ├── Calendar tools
        ├── Meet link creation via Calendar
        ├── Style memory
        └── Action logs
```

The current tool adapters are plain Python modules:

```text
agent.py
gmail_tools.py
calendar_tools.py
safety.py
style_memory.py
google_auth.py
utils.py
```

The app is intentionally modular. The agent does not need to know whether a tool is called directly, through n8n, through Claude MCP, or through another orchestration layer. The important contract is the tool interface.

---

## 2. Core agent loop

WalkPA runs a two-step conversational action loop.

### Step 1: First pass

Input:

```text
"I'm walking to work. Clear my inbox, draft replies, route admin or low-priority messages, schedule meetings, and tell me what you need from me."
```

Agent behaviour:

```text
1. Read recent Gmail messages.
2. Read Google Calendar events.
3. Classify emails.
4. Execute reversible actions.
5. Ask the user only for missing decisions.
6. Speak back a short PA briefing.
```

Actions performed:

```text
- Create Gmail drafts
- Apply Gmail labels
- Route finance/admin/low-priority emails
- Create Calendar holds
- Add Google Meet links to meeting holds
- Save pending user questions
```

### Step 2: Follow-up

Input:

```text
"Tell Rohan yes. For the contract, say I will review it this afternoon but I do not want to confirm anything yet."
```

Agent behaviour:

```text
1. Load pending user questions.
2. Convert the user's spoken decision into final replies.
3. Draft or send approved replies.
4. Speak back what was completed.
```

---

## 3. Tool contracts

These are the core functions that make WalkPA pluggable.

### Gmail tools

```python
get_recent_emails(max_results: int) -> list[EmailMessage]
create_draft(to: str, subject: str, body: str, thread_id: str | None = None) -> dict
send_email(to: str, subject: str, body: str) -> dict
apply_label(message_id: str, label_name: str) -> dict
archive_email(message_id: str) -> dict
get_sent_email_samples(max_results: int) -> list[dict]
```

### Calendar tools

```python
get_events(days_ahead: int) -> list[dict]
suggest_free_slot_options(events: list[dict]) -> list[dict]
create_calendar_hold(
    title: str,
    start_iso: str,
    end_iso: str,
    description: str = "Created by WalkPA.",
    add_meet: bool = True,
) -> dict
```

### Agent tools

```python
run_agent(command: str, mode: str = "autopilot", max_emails: int = 15, execute: bool = True) -> dict
process_user_followup(user_reply: str, send_approved: bool = False) -> dict
```

### Safety router

```python
can_execute(action_type: str, mode: str) -> bool
```

The safety router is the main guardrail.

```text
Intervention mode:
- Prepare only
- No Gmail/Calendar changes

Autopilot mode:
- Create drafts
- Apply labels
- Create Calendar holds
- Archive low-priority emails if enabled

High-risk actions:
- Sending email requires explicit user follow-up approval
- Deleting email is blocked
- Declining meetings is blocked
```

---

## 4. How to expose WalkPA as an MCP server

Each WalkPA tool can become an MCP tool.

Suggested MCP tools:

```text
walkpa.get_recent_emails
walkpa.triage_inbox
walkpa.create_draft
walkpa.apply_label
walkpa.create_calendar_hold
walkpa.process_followup
walkpa.verify_actions
```

Example MCP-style tool descriptions:

```json
{
  "name": "walkpa.triage_inbox",
  "description": "Reads recent Gmail messages, checks Calendar availability, classifies emails, and returns a safe action plan.",
  "input_schema": {
    "type": "object",
    "properties": {
      "command": {"type": "string"},
      "mode": {"type": "string", "enum": ["intervention", "autopilot"]},
      "max_emails": {"type": "integer"}
    },
    "required": ["command"]
  }
}
```

```json
{
  "name": "walkpa.process_followup",
  "description": "Processes the user's spoken follow-up decision and drafts or sends approved replies.",
  "input_schema": {
    "type": "object",
    "properties": {
      "user_reply": {"type": "string"},
      "send_approved": {"type": "boolean"}
    },
    "required": ["user_reply"]
  }
}
```

The current Python functions already match this shape. An MCP wrapper only needs to call the existing functions.

---

## 5. How to plug WalkPA into Claude

Claude can use WalkPA through either:

```text
1. MCP server wrapper
2. Local API wrapper
3. Manual tool bridge
```

Recommended Claude flow:

```text
Claude receives the user command.
Claude calls walkpa.triage_inbox.
WalkPA returns action plan + execution results + pending questions.
Claude speaks/summarises the briefing.
User gives follow-up decision.
Claude calls walkpa.process_followup.
WalkPA drafts/sends approved replies.
```

Claude should not directly send Gmail actions. Claude should call the WalkPA safety-routed tools.

---

## 6. How to plug WalkPA into n8n

Recommended n8n workflow:

```text
Trigger:
- Webhook
- Voice assistant
- Telegram/WhatsApp/Slack command
- Scheduled morning inbox run

Nodes:
1. Webhook receives command.
2. Execute Command or HTTP Request calls WalkPA local API.
3. WalkPA returns briefing + pending questions.
4. n8n sends briefing to user.
5. User replies with approval.
6. n8n calls WalkPA follow-up endpoint.
7. n8n sends final status.
```

Suggested endpoints for a production wrapper:

```text
POST /api/first-pass
POST /api/follow-up
GET /api/verify-actions
```

Payload example:

```json
{
  "command": "Clear my inbox while I walk to work.",
  "mode": "autopilot",
  "max_emails": 15
}
```

Follow-up payload:

```json
{
  "user_reply": "Tell Rohan yes. For the contract, say I will review this afternoon.",
  "send_approved": true
}
```

---

## 7. How to plug WalkPA into Zapier or Make

Expose the local functions through a small hosted API.

Useful actions:

```text
- New Gmail message triggers WalkPA triage.
- Calendar event request triggers WalkPA scheduling.
- New invoice email triggers route-to-finance label.
- Daily 8:30 AM workflow triggers "morning PA briefing".
```

The important thing is to keep Gmail/Calendar writes inside WalkPA's safety layer.

---

## 8. How to plug WalkPA into a mobile assistant

Mobile voice interface:

```text
1. Phone records voice.
2. Speech-to-text converts it into command text.
3. Command is sent to WalkPA API.
4. WalkPA executes safe actions.
5. Text-to-speech reads the PA briefing back.
```

Suggested mobile command:

```text
"I'm heading to work. Clear my inbox and tell me what you need from me."
```

Suggested mobile response:

```text
"Done. I drafted two replies, routed the invoice to finance, created one calendar hold, and labelled four promotional emails. I need your decision on the contract email before replying."
```

---

## 9. Environment variables

WalkPA expects local configuration through `.env`.

```text
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
OPENAI_TRANSCRIBE_MODEL=whisper-1
ALLOW_EMAIL_SEND=false
ALLOW_CALENDAR_CREATE=true
```

The final deterministic demo does not require OpenAI API quota to work. Gmail and Calendar OAuth are required.

---

## 10. Files that must never be committed

Do not commit:

```text
.env
credentials.json
token.json
memory/
__pycache__/
.venv/
```

These contain private keys, OAuth tokens, or local state.

---

## 11. Production roadmap

Short-term:

```text
- Replace deterministic classifier with LLM planner when API quota is available.
- Add contact mapping for "finance team", "ops team", and "legal team".
- Add approval queue UI.
- Add Slack/Teams adapter.
```

Medium-term:

```text
- MCP server wrapper.
- Hosted API.
- Persistent encrypted memory.
- Mobile-first voice interface.
- Multi-account support.
```

Long-term:

```text
- Cross-channel communications PA.
- Learns user style and preferences.
- Negotiates meeting times across people.
- Handles inbox, calendar, Slack, WhatsApp, and CRM workflows.
```

---

## 12. Why this is agentic

WalkPA is not just summarisation.

It has:

```text
- tool access
- memory
- classification
- action planning
- safety policy
- autonomous reversible execution
- follow-up question handling
- approved sending
- real Gmail/Calendar side effects
```

The product principle is bounded autonomy:

> WalkPA acts where it is safe, asks where it needs judgement, and never sends sensitive communication without explicit user approval.
