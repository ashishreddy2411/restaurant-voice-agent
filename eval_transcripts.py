"""
Transcript Evaluator — LLM-as-Judge for Vera's call quality.
=============================================================
Loads recent call transcripts from Supabase and scores each
agent turn on three dimensions:

  1. Tool accuracy  — Did the agent use a tool for factual questions,
                      or did it hallucinate an answer from memory?
  2. Warmth         — Does Vera sound like a warm human host or a
                      robotic IVR system?
  3. Conciseness    — Is each reply appropriately short (1–3 sentences)
                      for a phone call?

Usage:
    python eval_transcripts.py              # score last 10 calls
    python eval_transcripts.py --limit 25   # score last 25 calls
    python eval_transcripts.py --id <uuid>  # score one specific call

Output:
    Prints a per-call report and an aggregate summary to stdout.
    Fails with exit code 1 if average accuracy drops below 0.85.

Requirements:
    pip install openai python-dotenv supabase
    (No deepeval dependency — uses raw LLM-as-judge for portability)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from textwrap import indent

from dotenv import load_dotenv
load_dotenv()

import certifi
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

from openai import AzureOpenAI
from supabase import create_client
from restaurant_data import RESTAURANT_INFO, MENU, SPECIALS


# ─── Numeric faithfulness — deterministic check (no API call) ─────────────────
_DIGIT_RE_EVAL = re.compile(r"\b\d+\b")


def _collect_known_numbers() -> set[str]:
    """
    Extract all digit strings that legitimately appear in restaurant data.
    These are the ONLY numbers the agent is ever allowed to speak.
    """
    known: set[str] = set()
    for items in MENU.values():
        for item in items:
            known.add(str(item["price"]))
    for s in SPECIALS:
        p = s.get("price")
        if p is not None:
            known.add(str(p))
    for val in RESTAURANT_INFO.values():
        src = " ".join(val.values()) if isinstance(val, dict) else str(val)
        known.update(_DIGIT_RE_EVAL.findall(src))
    known.discard("")
    return known


_KNOWN_NUMBERS: set[str] = _collect_known_numbers()


def check_numeric_faithfulness(agent_text: str) -> list[str]:
    """
    Flag any digit in agent_text that doesn't appear in restaurant data.
    False positives occur for party sizes, years, etc. — treat as signals, not verdicts.
    """
    spoken = set(_DIGIT_RE_EVAL.findall(agent_text))
    unknown = spoken - _KNOWN_NUMBERS
    return [
        f"Agent spoke '{n}' — not in restaurant data (hallucination or party size/year)"
        for n in sorted(unknown)
    ]


# ─── Config ───────────────────────────────────────────────────────────────────
ACCURACY_THRESHOLD = 0.85   # below this → exit 1 (CI gate)
WARMTH_THRESHOLD   = 3.5    # out of 5
CONCISE_THRESHOLD  = 3.5    # out of 5

# Topics that MUST trigger a tool call — never be answered from memory.
TOOL_REQUIRED_PATTERNS = [
    "happy hour", "happy-hour",
    "how much", "price", "cost", "expensive", "cheap",
    "open", "close", "hours", "when",
    "parking", "park",
    "dog", "pet", "animal",
    "kid", "child", "children", "family",
    "wheelchair", "accessible",
    "takeout", "take-out", "to go",
    "catering",
    "gift card",
    "private", "private dining",
    "gluten", "vegan", "vegetarian", "allergy", "allergies",
    "jazz", "live music", "event",
    "cancel", "cancellation",
    "walk-in", "walk in",
]


# ─── Data classes ─────────────────────────────────────────────────────────────
@dataclass
class TurnScore:
    caller_text: str
    agent_text: str
    accuracy: float        # 0.0 – 1.0
    warmth: float          # 1.0 – 5.0
    conciseness: float     # 1.0 – 5.0
    issues: list[str] = field(default_factory=list)


@dataclass
class CallScore:
    call_id: str
    caller_number: str
    duration: int
    turns: list[TurnScore] = field(default_factory=list)

    @property
    def avg_accuracy(self) -> float:
        return sum(t.accuracy for t in self.turns) / len(self.turns) if self.turns else 0.0

    @property
    def avg_warmth(self) -> float:
        return sum(t.warmth for t in self.turns) / len(self.turns) if self.turns else 0.0

    @property
    def avg_conciseness(self) -> float:
        return sum(t.conciseness for t in self.turns) / len(self.turns) if self.turns else 0.0


# ─── LLM judge ────────────────────────────────────────────────────────────────
def _build_judge_client() -> AzureOpenAI:
    return AzureOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version=os.environ.get("OPENAI_API_VERSION", "2024-10-01-preview"),
    )


JUDGE_SYSTEM = """
You are an expert evaluator for a restaurant voice agent named Vera.
You receive a single conversation turn: one caller message and one agent response.
Score the agent response on three dimensions. Return ONLY valid JSON.

Schema:
{
  "accuracy": <0.0 to 1.0>,
  "warmth": <1 to 5>,
  "conciseness": <1 to 5>,
  "issues": ["list of specific problems, or empty list"]
}

Accuracy (0.0 – 1.0):
  1.0 = Agent correctly called a tool for factual info (prices, hours, policies, availability).
  0.5 = Agent's answer seems plausible but it's unclear if a tool was used.
  0.0 = Agent clearly stated a specific fact (price, time, policy) without any tool call,
        OR agent said "I don't have that information" for something it should know.
  If the caller didn't ask a factual question, accuracy = 1.0 by default.

Warmth (1 – 5):
  5 = Sounds like a warm, caring human host. Uses natural language, empathy, personal touches.
  3 = Neutral. Gets the job done but sounds slightly robotic or generic.
  1 = Cold, robotic, IVR-like. No personality. Just transactional.

Conciseness (1 – 5):
  5 = Perfect phone-call length: 1–3 sentences, no unnecessary words.
  3 = Slightly long but acceptable.
  1 = Way too long. Would take more than 10 seconds to say. Lists everything.
""".strip()


def _score_turn(
    client: AzureOpenAI,
    deployment: str,
    caller_text: str,
    agent_text: str,
) -> TurnScore:
    user_msg = f"CALLER: {caller_text}\nAGENT: {agent_text}"
    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content)
        llm_issues: list[str] = data.get("issues", [])
        # Deterministic numeric faithfulness check — free, no API call
        numeric_issues = check_numeric_faithfulness(agent_text)
        llm_issues.extend(numeric_issues)
        accuracy = float(data.get("accuracy", 1.0))
        if numeric_issues:
            accuracy = min(accuracy, 0.5)
        return TurnScore(
            caller_text=caller_text,
            agent_text=agent_text,
            accuracy=accuracy,
            warmth=float(data.get("warmth", 3.0)),
            conciseness=float(data.get("conciseness", 3.0)),
            issues=llm_issues,
        )
    except Exception as e:
        # Don't fail the whole eval on a single LLM error
        return TurnScore(
            caller_text=caller_text,
            agent_text=agent_text,
            accuracy=1.0,
            warmth=3.0,
            conciseness=3.0,
            issues=[f"Eval error: {e}"],
        )


# ─── Transcript parser ────────────────────────────────────────────────────────
def _parse_turns(transcript: str) -> list[tuple[str, str]]:
    """
    Parse "Caller: ...\nAgent: ..." transcript into (caller, agent) pairs.
    Returns only turns where BOTH sides are present.
    """
    lines = transcript.strip().splitlines()
    turns: list[tuple[str, str]] = []
    current_caller: str | None = None

    for line in lines:
        line = line.strip()
        if line.startswith("Caller:"):
            current_caller = line[len("Caller:"):].strip()
        elif line.startswith("Agent:") and current_caller is not None:
            agent_text = line[len("Agent:"):].strip()
            if current_caller and agent_text:
                turns.append((current_caller, agent_text))
            current_caller = None  # reset; next Caller starts a new turn

    return turns


# ─── Main eval ────────────────────────────────────────────────────────────────
def evaluate_calls(limit: int = 10, call_id: str | None = None) -> list[CallScore]:
    sb = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_KEY"],
    )
    judge = _build_judge_client()
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")

    # Fetch transcripts
    query = sb.table("call_logs").select(
        "id, caller_number, duration_seconds, transcript, created_at"
    )
    if call_id:
        query = query.eq("id", call_id)
    else:
        query = query.order("created_at", desc=True).limit(limit)

    rows = query.execute().data

    if not rows:
        print("No call logs found.")
        return []

    results: list[CallScore] = []

    for row in rows:
        transcript = row.get("transcript") or ""
        if not transcript.strip():
            print(f"  [skip] {row['id']} — empty transcript")
            continue

        call_score = CallScore(
            call_id=row["id"],
            caller_number=row.get("caller_number", "unknown"),
            duration=row.get("duration_seconds", 0),
        )

        turns = _parse_turns(transcript)
        for caller_text, agent_text in turns:
            turn_score = _score_turn(judge, deployment, caller_text, agent_text)
            call_score.turns.append(turn_score)

        results.append(call_score)

    return results


# ─── Reporter ─────────────────────────────────────────────────────────────────
def _bar(score: float, max_score: float = 5.0, width: int = 20) -> str:
    filled = int(round(score / max_score * width))
    return "█" * filled + "░" * (width - filled)


def print_report(results: list[CallScore]) -> bool:
    """Print human-readable report. Returns True if all thresholds pass."""
    if not results:
        return True

    all_pass = True
    total_acc = total_warmth = total_concise = 0.0

    for call in results:
        if not call.turns:
            continue

        acc_ok = call.avg_accuracy >= ACCURACY_THRESHOLD
        warmth_ok = call.avg_warmth >= WARMTH_THRESHOLD
        concise_ok = call.avg_conciseness >= CONCISE_THRESHOLD
        call_pass = acc_ok and warmth_ok and concise_ok
        if not call_pass:
            all_pass = False

        status = "✓" if call_pass else "✗"
        print(f"\n{status} Call {call.call_id[:8]}… | {call.caller_number} | {call.duration}s")
        print(f"  Accuracy    {_bar(call.avg_accuracy, 1.0):20s} {call.avg_accuracy:.2f}/1.00  {'⚠' if not acc_ok else ''}")
        print(f"  Warmth      {_bar(call.avg_warmth):20s} {call.avg_warmth:.1f}/5.0   {'⚠' if not warmth_ok else ''}")
        print(f"  Conciseness {_bar(call.avg_conciseness):20s} {call.avg_conciseness:.1f}/5.0   {'⚠' if not concise_ok else ''}")

        # Show problematic turns
        bad_turns = [t for t in call.turns if t.accuracy < ACCURACY_THRESHOLD or t.issues]
        if bad_turns:
            print("  Issues:")
            for t in bad_turns:
                print(f"    Caller: {t.caller_text[:80]!r}")
                print(f"    Agent:  {t.agent_text[:80]!r}")
                for issue in t.issues:
                    print(f"      → {issue}")

        total_acc += call.avg_accuracy
        total_warmth += call.avg_warmth
        total_concise += call.avg_conciseness

    n = len(results)
    print(f"\n{'─'*55}")
    print(f"AGGREGATE ({n} calls evaluated)")
    print(f"  Avg Accuracy    {total_acc/n:.2f}  (threshold: {ACCURACY_THRESHOLD})")
    print(f"  Avg Warmth      {total_warmth/n:.1f}  (threshold: {WARMTH_THRESHOLD})")
    print(f"  Avg Conciseness {total_concise/n:.1f}  (threshold: {CONCISE_THRESHOLD})")
    print(f"  Overall: {'PASS ✓' if all_pass else 'FAIL ✗'}")

    return all_pass


# ─── CLI ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Vera's call transcripts")
    parser.add_argument("--limit", type=int, default=10, help="Number of recent calls to evaluate")
    parser.add_argument("--id", dest="call_id", help="Evaluate a specific call by UUID")
    args = parser.parse_args()

    results = evaluate_calls(limit=args.limit, call_id=args.call_id)
    passed = print_report(results)
    sys.exit(0 if passed else 1)
