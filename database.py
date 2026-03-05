"""
Database Layer
==============
All Supabase interactions live here — call logging and reservation saving.

Keeping this separate from agent.py means:
  - You can swap the database (e.g., Postgres directly) without touching agent logic
  - Database errors are handled in one place
  - Easy to test in isolation
"""

import logging
import os
from datetime import datetime

from supabase import Client, create_client

logger = logging.getLogger("restaurant-agent.db")


# ─── Client ───────────────────────────────────────────────────────────────────
def init_supabase() -> Client | None:
    """
    Create and return a Supabase client using environment variables.

    Returns None (gracefully) if credentials are missing — the agent will
    still run and take calls, just without database persistence.

    Environment variables required:
        SUPABASE_URL              — https://<project-id>.supabase.co
        SUPABASE_SERVICE_ROLE_KEY — service_role key (bypasses RLS, server-side only)
    """
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        logger.warning(
            "SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set. "
            "Call logging and reservations are disabled until credentials are provided."
        )
        return None
    client = create_client(url, key)
    logger.info("Supabase client initialized.")
    return client


# Module-level client — created once at startup, reused for all calls
supabase: Client | None = init_supabase()


# ─── Call Logging ─────────────────────────────────────────────────────────────
async def log_call(caller_number: str, duration_seconds: int, transcript: str) -> None:
    """
    Save a completed call's details to the `call_logs` table.

    This is called after every call ends. Errors are caught and logged —
    a database failure here must never affect the caller's experience.

    Table schema (run in Supabase SQL editor):
        CREATE TABLE call_logs (
            id               BIGSERIAL PRIMARY KEY,
            caller_number    TEXT,
            duration_seconds INTEGER,
            transcript       TEXT,
            created_at       TIMESTAMPTZ DEFAULT NOW()
        );
    """
    if not supabase:
        logger.warning("Supabase not configured — skipping call log.")
        return
    try:
        supabase.table("call_logs").insert(
            {
                "caller_number": caller_number,
                "duration_seconds": duration_seconds,
                "transcript": transcript,
                # created_at defaults to NOW() in Supabase
            }
        ).execute()
        logger.info(f"Call logged: caller={caller_number}, duration={duration_seconds}s")
    except Exception as e:
        logger.error(f"Failed to log call to Supabase: {e}", exc_info=True)


# ─── Reservation Saving ───────────────────────────────────────────────────────
async def save_reservation(
    guest_name: str,
    callback_phone: str,
    date: str,
    time: str,
    party_size: int,
    special_requests: str | None,
) -> bool:
    """
    Save a reservation request to the `reservations` table.

    Returns True if saved successfully, False otherwise.
    The caller (agent tool) should handle the False case with a graceful fallback message.

    Table schema (run in Supabase SQL editor):
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
    """
    if not supabase:
        logger.warning("Supabase not configured — reservation not persisted.")
        logger.info(
            f"[RESERVATION — no DB] {guest_name}, {party_size} guests, {date} at {time}, "
            f"phone={callback_phone}, requests={special_requests}"
        )
        return False
    try:
        supabase.table("reservations").insert(
            {
                "guest_name": guest_name,
                "callback_phone": callback_phone,
                "date": date,
                "time": time,
                "party_size": party_size,
                "special_requests": special_requests,
                "created_at": datetime.utcnow().isoformat(),
            }
        ).execute()
        logger.info(
            f"Reservation saved: {guest_name}, {party_size} guests, {date} at {time}"
        )
        return True
    except Exception as e:
        logger.error(f"Failed to save reservation: {e}", exc_info=True)
        return False
