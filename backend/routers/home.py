from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
import database

router = APIRouter()

TOPIC_META = {
    "karangan_pendek": {
        "title": "Short Karangan",
        "paper": "PAPER 1",
        "route": "/karangan-pendek-latihan",
        "icon": "📝",
        "color": "blue",
    },
    "karangan_panjang": {
        "title": "Long Karangan",
        "paper": "PAPER 1",
        "route": "/karangan-panjang-latihan",
        "icon": "📚",
        "color": "green",
    },
    "golongan_kata": {
        "title": "Golongan Kata",
        "paper": "PAPER 2",
        "route": "/golongan-kata-latihan",
        "icon": "🔤",
        "color": "blue",
    },
    "bina_ayat": {
        "title": "Bina Ayat",
        "paper": "PAPER 2",
        "route": "/bina-ayat-latihan",
        "icon": "✏️",
        "color": "green",
    },
    "jenis_ayat": {
        "title": "Jenis Ayat",
        "paper": "PAPER 2",
        "route": "/jenis-ayat-latihan",
        "icon": "🧩",
        "color": "orange",
    },
    "kesalahan_bahasa": {
        "title": "Cari Kesalahan Bahasa",
        "paper": "PAPER 2",
        "route": "/kesalahan-bahasa-latihan",
        "icon": "⚠️",
        "color": "orange",
    },
    "pemahaman": {
        "title": "Pemahaman",
        "paper": "PAPER 2",
        "route": "/pemahaman-latihan",
        "icon": "📖",
        "color": "blue",
    },
    "rumusan": {
        "title": "Rumusan",
        "paper": "PAPER 2",
        "route": "/rumusan-latihan",
        "icon": "🧠",
        "color": "green",
    },
    "lisan": {
        "title": "Ujian Bertutur",
        "paper": "PAPER 3",
        "route": "/ujian-bertutur-latihan",
        "icon": "🎤",
        "color": "orange",
    },
}

STARTER_RECOMMENDATIONS = [
    {
        **TOPIC_META["golongan_kata"],
        "reason": "Good starting point to warm up grammar basics.",
    },
    {
        **TOPIC_META["bina_ayat"],
        "reason": "Build stronger sentence construction before harder sections.",
    },
    {
        **TOPIC_META["karangan_pendek"],
        "reason": "Quick writing practice to estimate your current level.",
    },
]

TOPIC_ORDER = list(TOPIC_META.keys())

HIGH_SCORE_THRESHOLD = 80


def _normalize_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass

    return datetime.min


def _extract_percentage(doc: dict, source: str) -> float:
    if source == "speaking":
        grammar = float(doc.get("grammar_vocabulary_score", 0))
        pronunciation = float(doc.get("pronunciation_score", 0))
        fluency = float(doc.get("fluency_score", 0))
        ideas = float(doc.get("ideas_score", 0))
        return round(((grammar + pronunciation + fluency + ideas) / 4) * 100, 1)

    return round(float(doc.get("percentage", 0)), 1)


def _topic_from_recommendation(item: dict) -> str | None:
    return next(
        (key for key, meta in TOPIC_META.items() if meta["title"] == item["title"]),
        None,
    )


def _build_unattempted_recommendations(
    attempted_topics: set[str],
    used_topics: set[str],
    high_score: bool,
) -> list[dict]:
    recommendations = []

    starter_topics = [
        topic
        for topic in (
            _topic_from_recommendation(item) for item in STARTER_RECOMMENDATIONS
        )
        if topic
    ]

    ordered_topics = starter_topics + [
        topic for topic in TOPIC_ORDER if topic not in starter_topics
    ]

    for topic in ordered_topics:
        if topic in attempted_topics or topic in used_topics:
            continue

        reason = (
            f"Great job scoring {HIGH_SCORE_THRESHOLD}% or above. Try this new topic next to test yourself in another area."
            if high_score
            else "You have not tried this topic yet, so it is a good next practice area."
        )

        recommendations.append({
            **TOPIC_META[topic],
            "reason": reason,
        })
        used_topics.add(topic)

        if len(recommendations) == 3:
            break

    return recommendations


@router.get("/recommendations")
def get_home_recommendations(user_id: str = Query(..., min_length=1)):
    if database.db is None:
        raise HTTPException(status_code=500, detail="Database not connected yet")

    attempts = []

    for source, collection in (
        ("essay", database.essay_results_col),
        ("comprehension", database.comprehension_results_col),
        ("speaking", database.speaking_results_col),
    ):
        if collection is None:
            continue

        docs = list(collection.find({"user_id": user_id}, {"_id": 0}))

        for doc in docs:
            topic = doc.get("quiz_type") or doc.get("task_type")

            if not topic or topic not in TOPIC_META:
                continue

            attempts.append({
                "topic": topic,
                "percentage": _extract_percentage(doc, source),
                "saved_at": _normalize_timestamp(
                    doc.get("saved_at") or doc.get("created_at")
                ),
            })

    if not attempts:
        return {
            "mode": "first_time",
            "message": "Start with these core practices to build your foundation.",
            "items": STARTER_RECOMMENDATIONS,
        }

    by_topic: dict[str, list[float]] = {}
    latest_attempt = max(attempts, key=lambda x: x["saved_at"])

    for item in attempts:
        by_topic.setdefault(item["topic"], []).append(item["percentage"])

    ranked = []

    for topic, scores in by_topic.items():
        avg_score = round(sum(scores) / len(scores), 1)

        ranked.append({
            "topic": topic,
            "average_score": avg_score,
            "attempts": len(scores),
        })

    ranked.sort(key=lambda x: x["average_score"])

    recommendations = []
    used_topics = set()
    attempted_topics = set(by_topic.keys())

    needs_practice = [
        item for item in ranked
        if item["average_score"] < HIGH_SCORE_THRESHOLD
    ]

    has_high_score_only = bool(ranked) and not needs_practice

    if has_high_score_only:
        recommendations.extend(
            _build_unattempted_recommendations(
                attempted_topics=attempted_topics,
                used_topics=used_topics,
                high_score=True,
            )
        )
    else:
        weakest = needs_practice[0]

        recommendations.append({
            **TOPIC_META[weakest["topic"]],
            "reason": (
                f"Your average here is {weakest['average_score']}%, "
                "so this is the best place to improve next."
            ),
        })
        used_topics.add(weakest["topic"])

        if (
            latest_attempt["topic"] not in used_topics
            and latest_attempt["percentage"] < HIGH_SCORE_THRESHOLD
        ):
            recommendations.append({
                **TOPIC_META[latest_attempt["topic"]],
                "reason": (
                    "You worked on this recently, "
                    "so this is a good time to continue the momentum."
                ),
            })
            used_topics.add(latest_attempt["topic"])

        for item in needs_practice:
            if item["topic"] in used_topics:
                continue

            recommendations.append({
                **TOPIC_META[item["topic"]],
                "reason": (
                    f"This topic is also below your stronger areas "
                    f"at {item['average_score']}%."
                ),
            })
            used_topics.add(item["topic"])

            if len(recommendations) == 3:
                break

        if len(recommendations) < 3:
            recommendations.extend(
                _build_unattempted_recommendations(
                    attempted_topics=attempted_topics,
                    used_topics=used_topics,
                    high_score=False,
                )
            )

    if len(recommendations) < 3:
        for item in ranked:
            if item["topic"] in used_topics:
                continue

            recommendations.append({
                **TOPIC_META[item["topic"]],
                "reason": (
                    f"Excellent work at {item['average_score']}%. "
                    "Revisit this topic to maintain your mastery."
                ),
            })
            used_topics.add(item["topic"])

            if len(recommendations) == 3:
                break

    message = (
        f"Great job scoring {HIGH_SCORE_THRESHOLD}% or above. Try these new topics to test yourself next."
        if has_high_score_only and recommendations
        else "Based on your recent performance, these are the best next topics to focus on."
    )

    return {
        "mode": "personalized",
        "message": message,
        "items": recommendations[:3],
    }