# WalkPA

**WalkPA** is a voice-first communications agent for Gmail, Google Calendar, and Google Meet. It is designed for the moments when you are walking, commuting, or moving between meetings and cannot manually clear your inbox.

WalkPA is not just an inbox summariser. It runs a bounded autonomous action loop:

```text
listen → triage → draft → route → schedule → act → ask follow-ups → complete approved replies
```

## What it does

- Reads recent Gmail messages.
- Triage messages into meeting requests, reply-needed, routing/admin, low-priority, FYI, and needs-user-input.
- Creates visible Gmail drafts.
- Routes emails using Gmail labels.
- Creates Calendar holds from meeting requests.
- Adds Google Meet links to Calendar holds.
- Speaks a short PA briefing back to the user.
- Asks for missing decisions, then drafts or sends approved follow-up replies.
- Never sends emails on the first pass.

## Demo flow

1. Send the demo emails from `FINAL_10_DEMO_EMAILS.md` to the Gmail account connected to WalkPA.
2. Run WalkPA.
3. Use the first command:

```text
I'm walking to work. Clear my inbox, draft replies, route admin or low-priority messages, schedule meetings, and tell me what you need from me.
```

4. WalkPA will create drafts, labels, Calendar holds, and ask for missing decisions.
5. Use the follow-up command:

```text
Tell Rohan yes, I am okay with the latest version. For the contract, say I will review it this afternoon but I do not want to confirm anything yet.
```

6. WalkPA will draft or send the approved follow-up replies depending on the checkbox.

## Setup

### 1. Clone and install

```powershell
git clone https://github.com/YOUR_USERNAME/walkpa.git
cd walkpa
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Create `.env`

Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

The deterministic final demo works without OpenAI quota. Gmail and Calendar OAuth are required.

### 3. Configure Google OAuth

In Google Cloud Console:

1. Create/select a Google Cloud project.
2. Enable **Gmail API**.
3. Enable **Google Calendar API**.
4. Configure OAuth consent screen.
5. Add yourself as a test user.
6. Create an OAuth client with application type **Desktop app**.
7. Download the JSON file.
8. Rename it to:

```text
credentials.json
```

9. Put `credentials.json` in the project root beside `app.py`.

### 4. Run

```powershell
python app.py
```

Open:

```text
http://127.0.0.1:7860
```

The first run will open Google OAuth and create a local `token.json`.

## Verification

After running autopilot, verify real-world side effects:

```powershell
python verify_walkpa_actions.py
```

In Gmail, search:

```text
in:drafts "WALKPA_CREATED_DRAFT"
in:sent "WALKPA_SENT_APPROVED_REPLY"
```

In Google Calendar, search:

```text
WalkPA hold
```

## Files

```text
app.py                         Local browser UI and API server
agent.py                       Conversational agent loop
gmail_tools.py                 Gmail read/draft/send/label tools
calendar_tools.py              Calendar and Meet-link tools
google_auth.py                 Google OAuth helper
safety.py                      Bounded autonomy policy
style_memory.py                Optional writing-style profile helper
verify_walkpa_actions.py       Post-demo verification script
PLUGGABLE_ARCHITECTURE.md      How to plug WalkPA into Claude, n8n, MCP, etc.
```

## Security

Never commit:

```text
.env
credentials.json
token.json
memory/
.venv/
```

These are already included in `.gitignore`.

## Why this is agentic

WalkPA has real tools, persistent pending-question memory, a safety router, and visible side effects in Gmail and Calendar. It acts on reversible work by itself, asks when judgement is needed, and only sends approved replies after explicit follow-up input.
