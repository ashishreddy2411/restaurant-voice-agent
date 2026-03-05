# Restaurant Voice Agent — Vera

A production-grade AI phone receptionist built on LiveKit Agents. Vera answers real phone calls, discusses the menu, handles reservations, and never makes up facts.

**Pipeline:** Caller Phone → Twilio SIP → LiveKit → Silero VAD → Deepgram STT → Azure OpenAI → Deepgram TTS → Caller

---

## What Vera Can Do

- Answer questions about the menu, hours, parking, policies, events
- Check item availability and quote exact prices
- Take reservations (collects name, date, time, party size, special requests)
- Handle barge-in — caller can interrupt mid-sentence
- Quote factual data (prices, times, policies) with zero hallucination
- Log every call transcript and reservation to Supabase

---

## Architecture

```
CALLER (real phone)
      │ PSTN
      ▼
TWILIO SIP TRUNK
      │ SIP → WebRTC
      ▼
LIVEKIT CLOUD
      │ dispatches to "restaurant-agent"
      ▼
YOUR MACHINE
  ┌─────────────────────────────────────┐
  │           agent.py                  │
  │                                     │
  │  Silero VAD  ← detects speech       │
  │      │                              │
  │  MultilingualModel  ← turn end      │
  │      │                              │
  │  Deepgram STT  ← audio → text       │
  │      │                              │
  │  Azure OpenAI (gpt-4o-mini, t=0.3)  │
  │      │         ↕ tool calls         │
  │      │    ┌────────────────────┐    │
  │      │    │  get_menu_items    │    │
  │      │    │  check_item_avail  │    │
  │      │    │  get_restaurant_info│   │
  │      │    │  save_reservation  │    │
  │      │    └────────────────────┘    │
  │      │                              │
  │  Deepgram TTS (aura-asteria-en)     │
  │      │                              │
  └──────┼──────────────────────────────┘
         │ (on call end)
         ▼
    Supabase DB
  (call_logs + reservations)
```

---

## Zero-Hallucination Design

Vera uses a **SPEAK:: speech template pattern** to guarantee factual accuracy:

1. **Tool routing map** — the system prompt explicitly maps every factual topic to the correct tool. Vera cannot answer prices, hours, or policies from memory.

2. **Pre-formatted speech** — tools convert raw data to spoken English *before* the LLM sees it:
   ```
   price: 52  →  "fifty-two dollars"    (never touches LLM free-form generation)
   "11:00 AM" →  "eleven AM"
   "12:00 PM" →  "noon"
   ```

3. **SPEAK:: contract** — tools return strings prefixed with `SPEAK::`. The system prompt instructs the LLM to read these verbatim, no changes.

4. **Eval auditor** — `eval_transcripts.py` runs after calls and flags any number the agent spoke that wasn't in the restaurant dataset.

---

## Files

| File | Purpose |
|---|---|
| `agent.py` | LiveKit pipeline, `RestaurantAgent` class, 4 tools, entrypoint |
| `restaurant_data.py` | Menu, restaurant info, number-to-words helpers, system prompt |
| `database.py` | Supabase client, `log_call()`, `save_reservation()` |
| `eval_transcripts.py` | LLM-as-judge + deterministic numeric faithfulness check |
| `run.sh` | Kills old instance, starts fresh on port 8081 |
| `requirements.txt` | All dependencies |
| `.env.example` | Environment variable template |
| `sip/` | LiveKit SIP trunk and dispatch rule config |

---

## Setup

### 1. Python environment

```bash
cd Voice_Agent
python3 -m venv .venv
source .venv/bin/activate

cd restaurant_agent
pip install -r requirements.txt
```

### 2. Download turn-detector model weights (one-time)

```bash
python agent.py download-files
```

This downloads the MultilingualModel ONNX weights (~50MB) to `~/.cache/huggingface/`.

### 3. Configure credentials

```bash
cp .env.example .env
# Fill in all values — see table below
```

### 4. Create Supabase tables

Run in your Supabase SQL editor:

```sql
CREATE TABLE call_logs (
    id               BIGSERIAL PRIMARY KEY,
    caller_number    TEXT,
    duration_seconds INTEGER,
    transcript       TEXT,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

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

### 5. Run the agent

```bash
bash run.sh
```

Watch for `registered worker` in the logs — the agent is live and waiting for calls.

### 6. Test via browser (no phone needed)

1. Go to [agents-playground.livekit.io](https://agents-playground.livekit.io)
2. Enter your `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`
3. Connect and talk to Vera

---

## Environment Variables

| Variable | Where to find it |
|---|---|
| `LIVEKIT_URL` | [cloud.livekit.io](https://cloud.livekit.io) → project → Settings → `wss://...` |
| `LIVEKIT_API_KEY` | Same page → API Keys |
| `LIVEKIT_API_SECRET` | Same page (shown once at creation) |
| `DEEPGRAM_API_KEY` | [console.deepgram.com](https://console.deepgram.com) → API Keys |
| `AZURE_OPENAI_ENDPOINT` | Azure AI Foundry → Deployments → your model → Endpoint |
| `AZURE_OPENAI_API_KEY` | Azure AI Foundry → Keys and Endpoint |
| `OPENAI_API_VERSION` | Use `2024-10-01-preview` |
| `AZURE_OPENAI_DEPLOYMENT` | Deployment name in Azure AI Foundry (e.g. `gpt-4o-mini`) |
| `SUPABASE_URL` | [supabase.com](https://supabase.com) → project → Settings → API → Project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Same page → Legacy API Keys → `service_role` ⚠️ keep secret |
| `MAX_CALL_DURATION_SECONDS` | Default `600` (10 min) |
| `RESTAURANT_NAME` | Display name used in greetings |

---

## Evaluating Call Quality

```bash
python eval_transcripts.py              # score last 10 calls
python eval_transcripts.py --limit 25   # score last 25 calls
python eval_transcripts.py --id <uuid>  # score one specific call
```

Scores each agent turn on:
- **Accuracy** (0–1) — did it use a tool for factual questions?
- **Warmth** (1–5) — does it sound human and welcoming?
- **Conciseness** (1–5) — appropriate phone-call length?

Exits with code `1` if average accuracy drops below `0.85` — use as a CI gate.

---

## VAD Tuning Reference

| Parameter | Default | Increase if... | Decrease if... |
|---|---|---|---|
| `activation_threshold` | `0.5` | Background noise triggers false starts | Quiet callers aren't detected |
| `min_silence_duration` | `0.45s` | Agent cuts callers off mid-sentence | Agent waits too long to respond |
| `min_interruption_duration` | `0.6s` | "Mm-hmm" keeps interrupting the agent | Caller can't barge in fast enough |

---

## Latency Notes

The minimum latency for this STT → LLM → TTS pipeline is **~1.5–2 seconds**. Key optimizations applied:

- `MultilingualModel` turn detector — transformer-based, ~10ms local inference
- `preemptive_generation=True` — LLM starts on partial transcript (bug fixed in agents ≥ 1.4.2)
- `min_endpointing_delay=0.1s` — safe because MultilingualModel handles semantic turn detection
- Deepgram `nova-2-phonecall` — tuned for narrow-band 8kHz PSTN audio
- `smart_format=False`, `punctuate=False` — removes unnecessary STT processing
- `temperature=0.3` — lower temperature means more deterministic, faster token generation

Going below ~1.5s requires switching to OpenAI Realtime API (WebSocket audio → audio, no STT/TTS roundtrip).
