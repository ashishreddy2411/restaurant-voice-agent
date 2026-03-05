# Restaurant Voice Agent

An AI phone receptionist powered by LiveKit Agents. Answers calls, discusses the menu, and takes reservations.

**Pipeline:** Caller audio → Silero VAD → Deepgram STT → Azure OpenAI → Deepgram TTS → Caller

---

## Phases

| Phase | Status | What it does |
|---|---|---|
| **Phase 2** | ✅ Current | Core agent, test via browser |
| **Phase 3** | 🔜 Next | Full Supabase logging + reservation DB |
| **Phase 4** | Planned | Twilio SIP — real phone number |
| **Phase 5** | Planned | Production hardening |

---

## Setup — Step by Step

### 1. Python environment

```bash
cd restaurant_agent

# Create a virtual environment (keeps dependencies isolated)
python3 -m venv .venv
source .venv/bin/activate       # Mac/Linux
# .venv\Scripts\activate        # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Copy and fill in credentials

```bash
cp .env.example .env
```

Open `.env` in your editor and fill in each value. See the table below for where to find each one.

### 3. Set up Supabase tables

In your Supabase dashboard, go to **SQL Editor** and run these two queries:

**Table 1: Call logs** (required by the spec)
```sql
CREATE TABLE call_logs (
    id           BIGSERIAL PRIMARY KEY,
    caller_number TEXT,
    duration_seconds INTEGER,
    transcript   TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);
```

**Table 2: Reservations** (for restaurant bookings)
```sql
CREATE TABLE reservations (
    id               BIGSERIAL PRIMARY KEY,
    guest_name       TEXT NOT NULL,
    callback_phone   TEXT NOT NULL,
    date             TEXT NOT NULL,
    time             TEXT NOT NULL,
    party_size       INTEGER NOT NULL,
    special_requests TEXT,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);
```

### 4. Run the agent

```bash
python agent.py start
```

You should see:
```
INFO [worker] Connected to LiveKit Cloud
INFO [worker] Waiting for jobs...
```

### 5. Test in your browser (Phase 2)

1. Go to [agents-playground.livekit.io](https://agents-playground.livekit.io)
2. Enter your `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET`
3. Click **Connect** — this creates a room and your agent joins automatically
4. Allow microphone access and start talking

You should hear the agent greet you. Try asking:
- "What's on the menu?"
- "Is the lobster pasta available?"
- "What are your hours?"
- "I'd like to make a reservation"

---

## Environment Variables

| Variable | Where to find it |
|---|---|
| `LIVEKIT_URL` | [cloud.livekit.io](https://cloud.livekit.io) → your project → Settings → `wss://...` |
| `LIVEKIT_API_KEY` | Same page → API Keys → Create key |
| `LIVEKIT_API_SECRET` | Same page (only shown once at creation) |
| `DEEPGRAM_API_KEY` | [console.deepgram.com](https://console.deepgram.com) → API Keys → Create key |
| `AZURE_OPENAI_ENDPOINT` | Azure AI Foundry → your project → Deployments → click your model → Endpoint |
| `AZURE_OPENAI_API_KEY` | Azure AI Foundry → your project → Keys and Endpoint |
| `OPENAI_API_VERSION` | Use `2024-08-01-preview` (or check Azure docs for latest) |
| `AZURE_OPENAI_DEPLOYMENT` | The name you gave your model in Azure AI Foundry (e.g. `gpt-5.2-chat`) |
| `SUPABASE_URL` | [supabase.com](https://supabase.com) → your project → Settings → API → Project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Same page → Legacy API Keys → `service_role` (⚠️ keep secret) |
| `MAX_CALL_DURATION_SECONDS` | Set to `600` (10 min) — increase for longer calls |
| `RESTAURANT_NAME` | Whatever you want to call the restaurant in greetings |

---

## Architecture

```
                  ┌──────────────────────────────────┐
                  │         agent.py                  │
                  │                                    │
  Audio in ──────►│ Silero VAD                         │
  (from room)     │   │ (is caller speaking?)          │
                  │   ▼                                │
                  │ Deepgram STT                       │
                  │   │ (audio → text)                 │
                  │   ▼                                │
                  │ Azure OpenAI LLM ──► tools:        │
                  │   │ (text → reply)    get_menu     │
                  │   │                  check_item    │
                  │   │                  save_res.     │
                  │   │                  get_info      │
                  │   ▼                                │
                  │ Deepgram TTS                       │
                  │   │ (reply text → audio)           │
                  │   ▼                                │
  Audio out ◄─────│ LiveKit Room                       │
  (to caller)     └──────────────────────────────────┘
                           │ (on call end)
                           ▼
                      Supabase DB
                   (call_logs + reservations)
```

---

## Tuning VAD

The VAD (Voice Activity Detection) parameters are documented in `agent.py`. Quick reference:

| Parameter | Effect | Tune if... |
|---|---|---|
| `activation_threshold` | How sensitive to start detecting speech | Increase (0.7) if background noise triggers it; decrease (0.3) for quiet speakers |
| `min_silence_duration` | How long a pause before "turn ends" | Increase (0.5) if agent cuts people off mid-sentence |
| `min_interruption_duration` | How long caller must speak to interrupt agent | Increase (0.8) if "mm-hmm" keeps cutting the agent off |

---

## Coming in Phase 3

- Pull menu from Supabase instead of hardcoded dict (update menu without redeploying)
- Reservation confirmation emails
- Supabase dashboard to view all bookings

## Coming in Phase 4 (Twilio SIP)

- Real phone number — callers ring in from any phone
- LiveKit SIP trunk setup
- Caller ID displayed in Supabase logs
