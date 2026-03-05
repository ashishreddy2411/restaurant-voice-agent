"""
Restaurant Voice Agent — Entry Point
=====================================
Configures and runs the LiveKit voice pipeline.

Pipeline (fully streaming end-to-end):
    Caller audio → Silero VAD → Deepgram STT → Azure OpenAI LLM → Deepgram TTS → Caller

Module responsibilities:
    agent.py           → pipeline config, agent class (LLM tools), entrypoint
    restaurant_data.py → menu, hours, restaurant info, system prompt
    database.py        → Supabase client, call logging, reservation saving
"""

from __future__ import annotations

import os

# ── Load .env FIRST — before anything reads os.environ ───────────────────────
# This must be before all other imports, otherwise modules like database.py
# that initialize clients at import time will see empty environment variables.
from dotenv import load_dotenv
load_dotenv()

# ── macOS SSL fix ─────────────────────────────────────────────────────────────
import certifi
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
# ─────────────────────────────────────────────────────────────────────────────

import asyncio
import logging
import time
from typing import Annotated

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RunContext,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.plugins import deepgram, openai, silero

import database
from restaurant_data import RESTAURANT_INFO, RESTAURANT_NAME, build_system_prompt, get_full_menu


# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("restaurant-agent")


# ─── Agent ────────────────────────────────────────────────────────────────────
class RestaurantAgent(Agent):
    """
    The AI brain of our restaurant receptionist.

    Accepts caller_number so the system prompt can pre-fill the callback
    number and personalise the session context per call.
    """

    def __init__(self, caller_number: str = "unknown") -> None:
        super().__init__(instructions=build_system_prompt(caller_number))
        self._caller_number = caller_number

    # ── Tool: List Menu Items ────────────────────────────────────────────────
    @function_tool
    async def get_menu_items(
        self,
        context: RunContext,
        category: Annotated[
            str,
            "Menu category to list. One of: 'appetizers', 'salads', 'mains', 'sides', 'desserts', 'drinks', or 'all'",
        ],
    ) -> str:
        """List menu items for a given category with prices and availability."""
        category = category.lower().strip()

        menu = get_full_menu()
        if category == "all":
            categories = list(menu.keys())
        elif category in menu:
            categories = [category]
        else:
            return (
                f"Unknown category '{category}'. "
                f"Available categories: {', '.join(menu.keys())}."
            )

        lines = []
        for cat in categories:
            lines.append(f"\n{cat.upper()}:")
            for item in menu[cat]:
                status = "AVAILABLE" if item["available"] else "NOT AVAILABLE TODAY"
                tags = f" [{', '.join(item['tags'])}]" if item.get("tags") else ""
                lines.append(
                    f"  [{status}] {item['name']} — ${item['price']}{tags} — {item['description']}"
                )
        return "\n".join(lines)

    # ── Tool: Check a Specific Item ──────────────────────────────────────────
    @function_tool
    async def check_item_availability(
        self,
        context: RunContext,
        item_name: Annotated[str, "The exact or partial name of the menu item"],
    ) -> str:
        """Check if a specific menu item is available and return its details."""
        needle = item_name.lower()

        menu = get_full_menu()
        for category, items in menu.items():
            for item in items:
                if needle in item["name"].lower():
                    if item["available"]:
                        return (
                            f"{item['name']} is available today — ${item['price']}. "
                            f"{item['description']}."
                        )
                    # Item found but unavailable — suggest alternatives in the same category
                    alternatives = [
                        i["name"] for i in menu[category]
                        if i["available"] and i["name"] != item["name"]
                    ]
                    alt_text = (
                        f" Similar alternatives: {', '.join(alternatives[:3])}."
                        if alternatives else ""
                    )
                    return f"I'm sorry, {item['name']} is not available today.{alt_text}"

        return (
            f"I couldn't find '{item_name}' on our menu. "
            "Would you like me to list a specific category?"
        )

    # ── Tool: Restaurant Info ────────────────────────────────────────────────
    @function_tool
    async def get_restaurant_info(
        self,
        context: RunContext,
        info_type: Annotated[
            str,
            (
                "The type of information to look up. Use the exact key where possible. "
                "Available keys: hours, address, phone, cuisine, about, parking, dress_code, "
                "reservation_policy, waitlist_policy, kids_policy, dogs_policy, "
                "happy_hour, holiday_note, private_dining, events, "
                "gift_cards, catering, takeout, accessibility."
            ),
        ],
    ) -> str:
        """Get restaurant information: hours, address, parking, policies, events, etc."""
        query = info_type.lower().strip()

        # Hours need special formatting
        if query == "hours":
            lines = [f"{day}: {t}" for day, t in RESTAURANT_INFO["hours"].items()]
            return "Our hours:\n" + "\n".join(lines)

        # Exact key match
        value = RESTAURANT_INFO.get(query)
        if value and not isinstance(value, dict):
            return str(value)

        # Fuzzy alias matching — handles LLM guesses like "pet_policy", "dog policy", etc.
        aliases = {
            "pet": "dogs_policy",
            "dog": "dogs_policy",
            "cat": "dogs_policy",
            "animal": "dogs_policy",
            "kid": "kids_policy",
            "child": "kids_policy",
            "children": "kids_policy",
            "cancel": "reservation_policy",
            "cancellation": "reservation_policy",
            "walk": "waitlist_policy",
            "walkin": "waitlist_policy",
            "wheelchair": "accessibility",
            "accessible": "accessibility",
            "happy": "happy_hour",
            "holiday": "holiday_note",
            "private": "private_dining",
            "event": "events",
            "jazz": "events",
            "live music": "events",
            "gift": "gift_cards",
            "cater": "catering",
            "takeaway": "takeout",
            "take out": "takeout",
            "about": "about",
            "story": "about",
            "history": "about",
        }
        for keyword, key in aliases.items():
            if keyword in query:
                return str(RESTAURANT_INFO.get(key, "I don't have that information on hand."))

        return "I don't have that specific information on hand — is there anything else I can help you with?"

    # ── Tool: Save Reservation ───────────────────────────────────────────────
    @function_tool
    async def save_reservation(
        self,
        context: RunContext,
        guest_name: Annotated[str, "Full name of the person making the reservation"],
        date: Annotated[str, "Reservation date, e.g. 'March 15' or 'this Saturday'"],
        reservation_time: Annotated[str, "Reservation time, e.g. '7:00 PM'"],
        party_size: Annotated[int, "Number of people in the party"],
        special_requests: Annotated[
            str,
            "Dietary restrictions, allergies, or special occasions. Use 'none' if not mentioned.",
        ],
        callback_phone: Annotated[
            str,
            "Callback phone number. Use the caller's number if they didn't provide a different one.",
        ] = "",
    ) -> str:
        """
        Save a reservation to the database.
        Only call this AFTER the caller has confirmed all details are correct.
        """
        # Default to the caller's own number if no different number was given
        phone = callback_phone.strip() or self._caller_number
        # Treat empty string, whitespace, and "none" all as no special requests
        requests = special_requests.strip() or None
        if requests and requests.lower() == "none":
            requests = None

        saved = await database.save_reservation(
            guest_name=guest_name,
            callback_phone=phone,
            date=date,
            time=reservation_time,
            party_size=party_size,
            special_requests=requests,
        )

        if saved:
            return (
                f"Perfect, you're all set! Table for {party_size} under {guest_name} "
                f"on {date} at {reservation_time}. "
                f"We'll send a confirmation to {phone}. "
                f"Please note we hold reservations for 15 minutes — if you're running late, give us a call!"
            )
        else:
            return (
                f"I'm having a little trouble on my end right now, but I have all your details: "
                f"table for {party_size} under {guest_name}, {date} at {reservation_time}. "
                f"Expect a call from us at {phone} shortly to confirm. We're sorry for the inconvenience!"
            )


# ─── Transcript Builder ───────────────────────────────────────────────────────
def _build_transcript(session: AgentSession) -> str:
    """
    Build a human-readable transcript from the session's conversation history.
    Skips the system prompt (role='system') — that's internal, not conversation.

    In livekit-agents v1.4, chat_ctx.messages() is a method call (not a property),
    and msg.content is always a list[str | ImageContent | AudioContent].
    """
    lines = []
    for msg in session.history.messages():  # session.history is the public ChatContext property
        if msg.role not in ("user", "assistant"):
            continue
        # content is always a list — extract only the text parts
        text_parts = [c for c in msg.content if isinstance(c, str)]
        content = " ".join(text_parts)
        label = "Caller" if msg.role == "user" else "Agent"
        lines.append(f"{label}: {content}")
    return "\n".join(lines)


# ─── Entrypoint ───────────────────────────────────────────────────────────────
async def entrypoint(ctx: JobContext) -> None:
    """
    Called by LiveKit Workers once per incoming call (or browser test session).
    Each caller gets their own independent copy of this function running.

    Flow:
        1. Connect to the LiveKit room
        2. Wait for the caller (participant) to join
        3. Start the voice pipeline (VAD → STT → LLM → TTS)
        4. Send the opening greeting
        5. On call end → save transcript to Supabase
    """
    await ctx.connect()
    logger.info(f"Agent connected to room: {ctx.room.name}")

    # Wait for the caller.
    # Phone calls: SIP participant with phone number in attributes.
    # Browser tests: you joining from the LiveKit Playground.
    participant = await ctx.wait_for_participant()
    _sip_number = participant.attributes.get("sip.phoneNumber")
    caller_number = (
        _sip_number
        if isinstance(_sip_number, str) and _sip_number
        else participant.identity or "unknown"
    )
    logger.info(f"Call from: {caller_number}")

    call_start = time.monotonic()

    # ── Voice Pipeline ────────────────────────────────────────────────────────
    session = AgentSession(
        # VAD — Silero runs locally (no cost). Decides when the caller is speaking.
        vad=silero.VAD.load(
            # How confident to START detecting speech (0.0–1.0).
            # Raise to 0.7 if background noise triggers false detections.
            # Lower to 0.3 for quiet or soft-spoken callers.
            activation_threshold=0.5,
            # Threshold to STOP detecting speech. Slightly lower to avoid rapid toggling.
            deactivation_threshold=0.35,
            # Shortest burst counted as real speech — filters pops and mic noise.
            min_speech_duration=0.05,
            # Silence duration before "turn ended".
            # Raise to 0.5 if agent cuts callers off mid-sentence.
            min_silence_duration=0.45,
            # Audio captured just before speech onset — catches the first syllable.
            prefix_padding_duration=0.1,
        ),
        # STT — nova-2-phonecall is tuned for narrow-band 8kHz PSTN audio (real phone calls).
        # Switch back to nova-3 if testing via browser/microphone only.
        stt=deepgram.STT(model="nova-2-phonecall", language="en-US"),
        # LLM — Azure OpenAI. Reads AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT
        # from env vars automatically. azure_deployment must match your deployment
        # name in Azure AI Foundry exactly. Streams tokens immediately.
        llm=openai.LLM.with_azure(
            azure_deployment=os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5.2-chat"),
            api_version=os.environ.get("OPENAI_API_VERSION", "2024-10-01-preview"),
        ),
        # TTS — Deepgram Aura. Starts speaking as soon as the first LLM tokens arrive.
        # Other voice options:
        #   "aura-luna-en"    → softer female
        #   "aura-zeus-en"    → authoritative male
        #   "aura-orpheus-en" → casual male
        tts=deepgram.TTS(model="aura-asteria-en"),
        # Barge-in: caller can interrupt the agent mid-sentence and it stops immediately.
        allow_interruptions=True,
        # How long the caller must speak to count as an interruption.
        # Lower to 0.5 if callers struggle to interrupt the agent.
        min_interruption_duration=0.8,
        # If VAD fires but no words are transcribed (background noise), agent resumes.
        resume_false_interruption=True,
    )

    # ── Max Call Duration ─────────────────────────────────────────────────────
    # Ends the call gracefully after the configured time. Protects against
    # runaway API costs from stuck, looping, or abandoned calls.
    max_duration = int(os.environ.get("MAX_CALL_DURATION_SECONDS", "600"))

    async def _enforce_max_duration() -> None:
        await asyncio.sleep(max_duration)
        logger.warning(f"Max duration ({max_duration}s) reached — ending call {caller_number}")
        await session.generate_reply(
            instructions=(
                "Politely let the caller know the maximum call time has been reached. "
                "Thank them warmly and ask them to call back if they need more help. "
                "One sentence only."
            )
        )
        await asyncio.sleep(8)  # Allow TTS to finish before shutdown
        await ctx.shutdown()

    max_duration_task = asyncio.create_task(_enforce_max_duration())

    # ── Shutdown Callback ─────────────────────────────────────────────────────
    # Runs automatically when the call ends, for any reason.
    async def _on_shutdown() -> None:
        max_duration_task.cancel()
        duration = int(time.monotonic() - call_start)
        logger.info(f"Call ended: caller={caller_number}, duration={duration}s")
        await database.log_call(
            caller_number=caller_number,
            duration_seconds=duration,
            transcript=_build_transcript(session),
        )

    ctx.add_shutdown_callback(_on_shutdown)

    # ── Session Event Listeners (debug visibility) ────────────────────────────
    # These log every major state change so you can see exactly what the agent
    # is doing in the terminal — useful for diagnosing silent failures.
    @session.on("agent_state_changed")
    def _on_agent_state(ev) -> None:
        logger.info(f"Agent state: {ev.new_state}")

    @session.on("user_input_transcribed")
    def _on_transcript(ev) -> None:
        logger.info(f"User said (final={ev.is_final}): {ev.transcript!r}")

    @session.on("conversation_item_added")
    def _on_item(ev) -> None:
        role = getattr(ev.item, "role", "?")
        parts = [c for c in getattr(ev.item, "content", []) if isinstance(c, str)]
        logger.info(f"Conversation [{role}]: {' '.join(parts)[:120]!r}")

    # ── Start Pipeline and Greet ──────────────────────────────────────────────
    await session.start(room=ctx.room, agent=RestaurantAgent(caller_number=caller_number))

    await session.generate_reply(
        instructions=(
            f"Greet the caller. Say 'Thank you for calling {RESTAURANT_NAME}' "
            "and ask how you can help. One warm, friendly sentence."
        )
    )
    logger.info(f"Greeting sent — call active with {caller_number}")


# ─── Worker Entry Point ───────────────────────────────────────────────────────
if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            # Must match the agent_name in the SIP dispatch rule (configured in Phase 4)
            agent_name="restaurant-agent",
        )
    )
