from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
import database

router = APIRouter()

QUIZ_LABELS = {
    "karangan_pendek": "Karangan Pendek",
    "karangan_panjang": "Karangan Panjang",
    "golongan_kata": "Golongan Kata",
    "bina_ayat": "Bina Ayat",
    "jenis_ayat": "Jenis Ayat",
    "kesalahan_bahasa": "Kesalahan Bahasa",
    "pemahaman": "Pemahaman",
    "rumusan": "Rumusan",
    "lisan": "Ujian Lisan",
}


def _grade_from_percentage(value: float) -> str:
    if value >= 85:
        return "A"
    if value >= 70:
        return "B"
    if value >= 60:
        return "C"
    if value >= 50:
        return "D"
    if value >= 40:
        return "E"
    return "F"


def _normalize_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.min


def _normalize_result(doc: dict, source: str) -> dict:
    quiz_type = doc.get("quiz_type") or doc.get("task_type") or "unknown"
    label = QUIZ_LABELS.get(quiz_type, quiz_type.replace("_", " ").title())

    if source == "speaking":
        grammar = float(doc.get("grammar_vocabulary_score", 0))
        pronunciation = float(doc.get("pronunciation_score", 0))
        fluency = float(doc.get("fluency_score", 0))
        ideas = float(doc.get("ideas_score", 0))

        percentage = round(((grammar + pronunciation + fluency + ideas) / 4) * 100, 1)
        grade = _grade_from_percentage(percentage)
        questions_count = len(doc.get("ideas_per_question", [])) or 4
    else:
        percentage = round(float(doc.get("percentage", 0)), 1)
        grade = doc.get("grade") or _grade_from_percentage(percentage)
        feedbacks = doc.get("question_feedbacks", []) or []
        questions_count = len(feedbacks) or 1

    saved_at = _normalize_timestamp(doc.get("saved_at") or doc.get("created_at"))

    return {
        "quiz_type": quiz_type,
        "title": label,
        "percentage": percentage,
        "grade": grade,
        "questions_count": questions_count,
        "saved_at": saved_at,
        "saved_at_label": saved_at.strftime("%d %b") if saved_at != datetime.min else "-",
    }


@router.get("/overview")
def get_dashboard_overview(user_id: str = Query(..., min_length=1)):
    if database.db is None:
        raise HTTPException(status_code=500, detail="Database not connected yet")

    results: list[dict] = []

    for source, collection in (
        ("essay", database.essay_results_col),
        ("comprehension", database.comprehension_results_col),
        ("speaking", database.speaking_results_col),
    ):
        if collection is None:
            continue

        docs = list(collection.find({"user_id": user_id}, {"_id": 0}))
        results.extend(_normalize_result(doc, source) for doc in docs)

    results.sort(key=lambda item: item["saved_at"])

    if not results:
        return {
            "user_id": user_id,
            "summary": {
                "average_score": None,
                "total_questions": 0,
                "grade_predictor": None,
                "predicted_percentage": None,
                "confidence": "low",
                "total_attempts": 0,
            },
            "trend": [],
            "breakdown": [],
            "latest_result": None,
        }

    total_attempts = len(results)
    average_score = round(sum(item["percentage"] for item in results) / total_attempts, 1)
    total_questions = sum(item["questions_count"] for item in results)

    recent = results[-3:]
    recent_average = sum(item["percentage"] for item in recent) / len(recent)

    trend_delta = results[-1]["percentage"] - results[0]["percentage"]
    improvement_bonus = max(-5.0, min(5.0, trend_delta * 0.15))

    predicted_percentage = round(
        max(0.0, min(100.0, average_score * 0.65 + recent_average * 0.35 + improvement_bonus)),
        1,
    )
    grade_predictor = _grade_from_percentage(predicted_percentage)

    if total_attempts >= 8:
        confidence = "high"
    elif total_attempts >= 4:
        confidence = "medium"
    else:
        confidence = "low"

    by_quiz: dict[str, list[float]] = {}
    for item in results:
        by_quiz.setdefault(item["quiz_type"], []).append(item["percentage"])

    breakdown = [
        {
            "quiz_type": quiz_type,
            "title": QUIZ_LABELS.get(quiz_type, quiz_type.replace("_", " ").title()),
            "average_percentage": round(sum(scores) / len(scores), 1),
            "attempts": len(scores),
        }
        for quiz_type, scores in by_quiz.items()
    ]
    breakdown.sort(key=lambda item: item["average_percentage"], reverse=True)

    by_day: dict[str, list[dict]] = {}
    for item in results:
        if item["saved_at"] == datetime.min:
            day_key = "Unknown"
        else:
            day_key = item["saved_at"].strftime("%Y-%m-%d")

        by_day.setdefault(day_key, []).append(item)

    daily_trend = []
    for day_key, day_results in by_day.items():
        daily_average = round(
            sum(item["percentage"] for item in day_results) / len(day_results),
            1,
        )

        if day_key == "Unknown":
            label = "-"
            full_date = "Unknown date"
        else:
            parsed_day = datetime.fromisoformat(day_key)
            label = parsed_day.strftime("%d %b")
            full_date = parsed_day.strftime("%d %B %Y")

        daily_trend.append(
            {
                "date": day_key,
                "label": label,
                "title": "Daily average",
                "percentage": daily_average,
                "grade": _grade_from_percentage(daily_average),
                "attempts": len(day_results),
                "full_date": full_date,
                "topics": sorted({item["title"] for item in day_results}),
            }
        )

    daily_trend.sort(key=lambda item: item["date"])
    trend = daily_trend[-7:]

    latest_result = results[-1]

    return {
        "user_id": user_id,
        "summary": {
            "average_score": average_score,
            "total_questions": total_questions,
            "grade_predictor": grade_predictor,
            "predicted_percentage": predicted_percentage,
            "confidence": confidence,
            "total_attempts": total_attempts,
        },
        "trend": trend,
        "breakdown": breakdown,
        "latest_result": {
            "title": latest_result["title"],
            "percentage": latest_result["percentage"],
            "grade": latest_result["grade"],
            "saved_at": latest_result["saved_at_label"],
        },
    }