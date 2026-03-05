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

import asyncio
import logging
import os
import time
from typing import Annotated

from dotenv import load_dotenv
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
from restaurant_data import MENU, RESTAURANT_INFO, RESTAURANT_NAME, SYSTEM_PROMPT

# Load .env file before anything reads os.environ
load_dotenv()


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

    Subclasses Agent to:
    1. Apply the restaurant's system prompt (personality + rules)
    2. Define tools the LLM can call during a conversation

    Tools are Python functions decorated with @function_tool.
    The LLM decides autonomously when to call them based on context.
    For example: caller asks "is the salmon available?" → LLM calls check_item_availability().
    """

    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)

    # ── Tool: List Menu Items ────────────────────────────────────────────────
    @function_tool
    async def get_menu_items(
        self,
        context: RunContext,
        category: Annotated[
            str,
            "Menu category to list. One of: 'appetizers', 'mains', 'desserts', 'drinks', or 'all'",
        ],
    ) -> str:
        """List menu items for a given category with prices and availability."""
        category = category.lower().strip()

        if category == "all":
            categories = list(MENU.keys())
        elif category in MENU:
            categories = [category]
        else:
            return (
                f"Unknown category '{category}'. "
                "Available categories: appetizers, mains, desserts, drinks."
            )

        lines = []
        for cat in categories:
            lines.append(f"\n{cat.upper()}:")
            for item in MENU[cat]:
                status = "AVAILABLE" if item["available"] else "NOT AVAILABLE TODAY"
                lines.append(
                    f"  [{status}] {item['name']} — ${item['price']} — {item['description']}"
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

        for category, items in MENU.items():
            for item in items:
                if needle in item["name"].lower():
                    if item["available"]:
                        return (
                            f"{item['name']} is available today — ${item['price']}. "
                            f"{item['description']}."
                        )
                    # Item found but unavailable — suggest alternatives in the same category
                    alternatives = [
                        i["name"] for i in MENU[category]
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
            "Type of info: 'hours', 'address', 'parking', 'dress_code', 'reservation_policy', 'cuisine'",
        ],
    ) -> str:
        """Get restaurant information: hours, address, parking, policies, etc."""
        info_type = info_type.lower().strip()

        if info_type == "hours":
            lines = [f"{day}: {t}" for day, t in RESTAURANT_INFO["hours"].items()]
            return "Our hours:\n" + "\n".join(lines)

        value = RESTAURANT_INFO.get(info_type)
        if value and not isinstance(value, dict):
            return str(value)

        # Fallback: most commonly needed info in one sentence
        return (
            f"{RESTAURANT_NAME} is at {RESTAURANT_INFO['address']}. "
            f"Open Mon–Thu 11am–10pm, Fri–Sat 11am–11pm, Sun 12pm–9pm. "
            f"Reach us at {RESTAURANT_INFO['phone']}."
        )

    # ── Tool: Save Reservation ───────────────────────────────────────────────
    @function_tool
    async def save_reservation(
        self,
        context: RunContext,
        guest_name: Annotated[str, "Full name of the person making the reservation"],
        callback_phone: Annotated[str, "Phone number to confirm the reservation"],
        date: Annotated[str, "Reservation date, e.g. 'March 15' or 'this Saturday'"],
        reservation_time: Annotated[str, "Reservation time, e.g. '7:00 PM'"],
        party_size: Annotated[int, "Number of people in the party"],
        special_requests: Annotated[
            str,
            "Dietary restrictions, allergies, or special occasions. Use 'none' if not mentioned.",
        ],
    ) -> str:
        """
        Save a reservation to the database.
        Only call this AFTER the caller has confirmed all details are correct.
        """
        requests = special_requests if special_requests.lower() != "none" else None

        saved = await database.save_reservation(
            guest_name=guest_name,
            callback_phone=callback_phone,
            date=date,
            time=reservation_time,
            party_size=party_size,
            special_requests=requests,
        )

        if saved:
            return (
                f"Reservation confirmed! Table for {party_size} under {guest_name} "
                f"on {date} at {reservation_time}. "
                f"We'll call {callback_phone} to confirm. "
                f"We hold reservations for 15 minutes — see you soon!"
            )
        else:
            # Database failed or not configured — still give caller a good experience
            return (
                f"I've noted your request for {party_size} guests on {date} at {reservation_time} "
                f"under {guest_name}. Our team will call {callback_phone} to confirm shortly."
            )


# ─── Transcript Builder ───────────────────────────────────────────────────────
def _build_transcript(session: AgentSession) -> str:
    """
    Build a human-readable transcript from the session's conversation history.
    Skips the system prompt (role='system') — that's internal, not conversation.
    """
    lines = []
    for msg in session.chat_ctx.messages:
        if msg.role not in ("user", "assistant"):
            continue
        content = (
            msg.content
            if isinstance(msg.content, str)
            else " ".join(str(c) for c in msg.content)
        )
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
    caller_number = (
        participant.attributes.get("sip.phoneNumber")
        or participant.identity
        or "unknown"
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
            # Raise to 0.5 if the agent cuts callers off mid-sentence.
            # Lower to 0.2 for faster response if callers pause at natural breaks.
            min_silence_duration=0.3,
            # Audio captured just before speech onset — catches the first syllable.
            prefix_padding_duration=0.1,
        ),
        # STT — Deepgram nova-3: fast, accurate, handles accents well. Fully streaming.
        stt=deepgram.STT(model="nova-3", language="en-US"),
        # LLM — Azure OpenAI. Reads from env vars: AZURE_OPENAI_API_KEY,
        # AZURE_OPENAI_ENDPOINT, OPENAI_API_VERSION. Streams tokens immediately.
        llm=openai.LLM.with_azure(
            model=os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5.2-chat"),
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
        # Raise to 0.8 if background noise keeps cutting the agent off.
        min_interruption_duration=0.5,
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

    # ── Start Pipeline and Greet ──────────────────────────────────────────────
    await session.start(room=ctx.room, agent=RestaurantAgent())

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
