from typing import Literal, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from machineLearning.essay_scorer import (
    score_essay,
    SPM_RUBRIC,
    percentage_to_grade,
)

from services.essay_service import (
    _ask_gemini,
    _check_relevance,
)


router = APIRouter()


class LatihanEssayMarkRequest(BaseModel):
    essay_type: Literal["karangan_pendek", "karangan_panjang"]
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    question: str
    answer: str


class LatihanEssayRubric(BaseModel):
    content_score: float
    language_score: float
    grammar_score: float
    vocabulary_score: float
    coherence_score: float


class LatihanEssayRelevance(BaseModel):
    score: float
    percentage: float
    reason: str
    is_off_topic: bool


class LatihanEssayMarkResponse(BaseModel):
    essay_type: str
    difficulty: str
    mark: float
    max_mark: int
    percentage: float
    grade: str
    word_count: int
    feedback: str
    suggestions: List[str]
    rubric: LatihanEssayRubric
    relevance: LatihanEssayRelevance


def count_words(text: str) -> int:
    return len([word for word in text.strip().split() if word.strip()])


@router.post("/essay/mark", response_model=LatihanEssayMarkResponse)
async def mark_latihan_essay(req: LatihanEssayMarkRequest):
    essay = req.answer.strip()
    question_text = req.question.strip()

    if not essay:
        raise HTTPException(status_code=400, detail="Karangan tidak boleh kosong.")

    if len(essay.split()) < 20:
        raise HTTPException(
            status_code=400,
            detail="Karangan terlalu pendek untuk disemak. Sila tulis jawapan yang lebih lengkap.",
        )

    if not question_text:
        raise HTTPException(status_code=400, detail="Soalan karangan diperlukan.")

    try:
        relevance_score, relevance_reason, is_off_topic = await _check_relevance(
            essay,
            question_text,
        )

        relevance_ratio = relevance_score / 5.0

        scorer_result = score_essay(
            essay,
            relevance_ratio=relevance_ratio,
        )

        paper_result = scorer_result[req.essay_type]

        content_score = paper_result["content_score"]
        language_score = paper_result["language_score"]
        grammar_score = paper_result["grammar_score"]
        vocabulary_score = paper_result["vocabulary_score"]
        coherence_score = paper_result["coherence_score"]

        subtotal = paper_result["subtotal"]
        max_score = paper_result["max_total"]
        percentage = paper_result["percentage"]
        grade = percentage_to_grade(percentage)

        reasons = paper_result["reasons"]
        relevance_pct = round(relevance_ratio * 100)

        off_topic_warning = (
            "\n\nAMARAN: Karangan ini kelihatan kurang menjawab tajuk yang diberikan. "
            "Berikan teguran yang jelas supaya pelajar lebih fokus kepada kehendak soalan."
            if is_off_topic
            else ""
        )

        difficulty_label = {
            "easy": "Mudah",
            "medium": "Sederhana",
            "hard": "Sukar",
        }.get(req.difficulty, "Sederhana")

        feedback_prompt = f"""
Anda ialah pemeriksa SPM Bahasa Melayu yang berpengalaman.

Tugas:
Berikan maklum balas latihan karangan kepada pelajar dalam Bahasa Melayu.

Jenis karangan: {req.essay_type}
Aras latihan: {difficulty_label}
Tajuk / Soalan:
\"\"\"{question_text}\"\"\"

Karangan pelajar:
\"\"\"{essay}\"\"\"

Markah:
- Markah keseluruhan: {subtotal} / {max_score}
- Peratus: {percentage}%
- Gred: {grade}

Kesesuaian tajuk:
- Skor kesesuaian: {relevance_score} / 5
- Peratus kesesuaian: {relevance_pct}%
- Ulasan: {relevance_reason}
{off_topic_warning}

Penilaian per aspek:
- Isi kandungan: {content_score} / {SPM_RUBRIC[req.essay_type]["traits"]["content_score"]["max"]}
  Sebab: {reasons["content"]}

- Bahasa: {language_score} / {SPM_RUBRIC[req.essay_type]["traits"]["language_score"]["max"]}
  Sebab: {reasons["language"]}

- Tatabahasa: {grammar_score} / {SPM_RUBRIC[req.essay_type]["traits"]["grammar_score"]["max"]}
  Sebab: {reasons["grammar"]}

- Kosa kata: {vocabulary_score} / {SPM_RUBRIC[req.essay_type]["traits"]["vocabulary_score"]["max"]}
  Sebab: {reasons["vocabulary"]}

- Kohesi dan koherensi: {coherence_score} / {SPM_RUBRIC[req.essay_type]["traits"]["coherence_score"]["max"]}
  Sebab: {reasons["coherence"]}

Kembalikan JSON sahaja dalam format ini:
{{
  "feedback": "<maklum balas lengkap dalam Bahasa Melayu, 4 hingga 6 ayat>",
  "suggestions": [
    "<cadangan penambahbaikan 1>",
    "<cadangan penambahbaikan 2>",
    "<cadangan penambahbaikan 3>"
  ]
}}
"""

        feedback_data = await _ask_gemini(feedback_prompt, temperature=0.3)

        if not isinstance(feedback_data, dict):
            feedback_data = {}

        feedback = feedback_data.get(
            "feedback",
            "Karangan telah disemak. Sila beri perhatian kepada isi, bahasa, tatabahasa dan susunan huraian.",
        )

        suggestions = feedback_data.get("suggestions", [])

        if not isinstance(suggestions, list) or len(suggestions) == 0:
            suggestions = [
                "Pastikan setiap isi menjawab kehendak soalan dengan jelas.",
                "Gunakan penanda wacana yang sesuai untuk menghubungkan idea.",
                "Semak semula tatabahasa, ejaan dan struktur ayat sebelum menghantar jawapan.",
            ]

        return LatihanEssayMarkResponse(
            essay_type=req.essay_type,
            difficulty=req.difficulty,
            mark=round(float(subtotal), 2),
            max_mark=int(max_score),
            percentage=round(float(percentage), 2),
            grade=grade,
            word_count=count_words(essay),
            feedback=feedback,
            suggestions=suggestions[:3],
            rubric=LatihanEssayRubric(
                content_score=round(float(content_score), 2),
                language_score=round(float(language_score), 2),
                grammar_score=round(float(grammar_score), 2),
                vocabulary_score=round(float(vocabulary_score), 2),
                coherence_score=round(float(coherence_score), 2),
            ),
            relevance=LatihanEssayRelevance(
                score=round(float(relevance_score), 2),
                percentage=round(float(relevance_pct), 2),
                reason=relevance_reason,
                is_off_topic=is_off_topic,
            ),
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Gagal menyemak karangan latihan: {str(e)}",
        )