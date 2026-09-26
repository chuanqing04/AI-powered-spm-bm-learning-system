import random
from services.user_results_memory import get_result


def get_adaptive_difficulty(user_id: str, quiz_type: str) -> str:
    """
    Returns: "low" | "medium" | "high"
    based on user's historical performance + controlled randomness.
    """

    result = get_result(user_id)

    if not result:
        return "medium"

    weak = result.get("weak_areas", [])
    strong = result.get("strong_areas", [])
    stats = result.get("quiz_type_stats", {}).get(quiz_type)

    if not stats:
        return "medium"

    avg = stats.get("avg_score", 0) if stats else 0

    print("QUIZ TYPE:", quiz_type)
    print("STATS FOUND:", stats)
    print("AVG:", avg if stats else None)

    r = random.random()

    # ─────────────────────────────────────────────
    # STRONG STUDENTS (priority)
    # ─────────────────────────────────────────────
    if quiz_type in strong:
        return "high" if r < 0.75 else "medium" if r < 0.95 else "low"

    # ─────────────────────────────────────────────
    # WEAK STUDENTS (careful progression)
    # ─────────────────────────────────────────────
    if quiz_type in weak:
        if avg < 0.30:
            return "low" if r < 0.7 else "medium"
        elif avg < 0.60:
            return "low" if r < 0.4 else "medium" if r < 0.85 else "high"
        else:
            return "medium" if r < 0.6 else "high"

    # ─────────────────────────────────────────────
    # NORMAL STUDENTS (balanced learning)
    # ─────────────────────────────────────────────
    if avg < 0.50:
        return "low" if r < 0.5 else "medium" if r < 0.85 else "high"

    if avg < 0.80:
        return "low" if r < 0.3 else "medium" if r < 0.7 else "high"

    # high performers
    return "high" if r < 0.7 else "medium" if r < 0.95 else "low"