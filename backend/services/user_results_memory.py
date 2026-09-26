"""
Persistent user result store — the memory layer for the agentic system.

WHY THIS EXISTS:
  Each quiz session currently lives in isolation. Once it ends, nothing is
  remembered. This module accumulates scores across sessions so the
  orchestrator can read a user's weak areas BEFORE generating questions,
  enabling targeted practice rather than random selection.
"""

from datetime import datetime, timezone
from typing import Optional
import database

# ── Thresholds ────────────────────────────────────────────────────────────────
# Normalised 0-1 scale. Scores below WEAK_THRESHOLD go into weak_areas.
# Scores above STRONG_THRESHOLD go into strong_areas.
WEAK_THRESHOLD   = 0.60
STRONG_THRESHOLD = 0.80

# Minimum number of attempts before a quiz type influences weak/strong labels.
# Avoids labelling a type "weak" after just one bad attempt.
MIN_ATTEMPTS_TO_LABEL = 2

# Max sessions to factor into avg (rolling window keeps old data from distorting)
ROLLING_WINDOW = 10


# ── Public API ────────────────────────────────────────────────────────────────

def get_result(user_id: str) -> Optional[dict]:
    """
    Fetch the user for user_id.
    Returns None if this user has no history yet.

    Called by comprehension_service.py BEFORE generating questions so the
    orchestrator can bias question selection toward weak areas.
    """
    if database.user_results_col is None:
        raise RuntimeError("MongoDB not initialized — user_results_col is None")

    return database.user_results_col.find_one(
        {"user_id": user_id},
        {"_id": 0},  # exclude internal Mongo _id from result
    )


def get_weak_areas(user_id: str) -> list[str]:
    """
    Convenience wrapper — returns just the weak_areas list.
    Returns empty list if no result exists yet (new user).

    Used in question generation prompts:
        weak = get_weak_areas(user_id)
        if weak:
            prompt += f"\\nFokus pada kawasan lemah pelajar: {', '.join(weak)}"
    """
    result = get_result(user_id)
    if not result:
        return []
    return result.get("weak_areas", [])


def update_result(user_id: str, quiz_type: str, raw_score: float, max_score: float) -> dict:
    """
    Record a new quiz result and recompute weak/strong areas.

    Called by comprehension_service.py AFTER scoring, inside _save_comprehension_result
    or score_submission.

    Args:
        user_id:   The user's user ID.
        quiz_type: One of the six quiz type strings.
        raw_score: The raw score returned by the scorer
                   (e.g. 0.8 for paper2, 9.5 for pemahaman, 24.0 for rumusan).

    Returns:
        The updated result document.
    """
    if database.user_results_col is None:
        raise RuntimeError("MongoDB not initialized — user_results_col is None")

    # Normalise to 0-1
    norm_score    = min(raw_score / max_score, 1.0)

    # Fetch existing or start fresh
    existing = database.user_results_col.find_one({"user_id": user_id}) or {}
    stats    = existing.get("quiz_type_stats", {})

    # Update rolling stats for this quiz_type
    entry    = stats.get(quiz_type, {"attempts": 0, "scores": []})
    scores   = entry.get("scores", [])
    scores.append(round(norm_score, 4))

    # Keep only the last ROLLING_WINDOW scores
    if len(scores) > ROLLING_WINDOW:
        scores = scores[-ROLLING_WINDOW:]

    avg = round(sum(scores) / len(scores), 4)
    stats[quiz_type] = {
        "attempts":    len(scores),
        "avg_score":   avg,
        "last_score":  round(norm_score, 4),
        "scores":      scores,
    }

    # Recompute weak / strong labels across all tracked quiz types
    weak_areas   = []
    strong_areas = []
    for qt, s in stats.items():
        if s["attempts"] < MIN_ATTEMPTS_TO_LABEL:
            continue
        if s["avg_score"] < WEAK_THRESHOLD:
            weak_areas.append(qt)
        elif s["avg_score"] >= STRONG_THRESHOLD:
            strong_areas.append(qt)

    updated_result = {
        "user_id":         user_id,
        "total_sessions":  existing.get("total_sessions", 0) + 1,
        "quiz_type_stats": stats,
        "weak_areas":      weak_areas,
        "strong_areas":    strong_areas,
        "last_updated":    datetime.now(timezone.utc).isoformat(),
    }

    database.user_results_col.replace_one(
        {"user_id": user_id},
        updated_result,
        upsert=True,  # creates document if user has no result yet
    )

    return updated_result