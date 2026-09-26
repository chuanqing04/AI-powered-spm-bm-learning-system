"""
Endpoints for Paper 2 (Tatabahasa & Pemahaman) quiz types.

POST /api/comprehension/start          → generate questions for the given type
POST /api/comprehension/submit         → score real quiz answers and update dashboard
POST /api/comprehension/latihan-submit → score latihan answers only, no dashboard update
GET  /api/comprehension/types          → list available Paper 2 types with metadata
"""
import uuid
import traceback
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Union
from datetime import datetime, timezone, timedelta

import database
from schemas.models import (
    QuizStartRequest,
    QuizStartResponse,
    QuizSubmitRequest,
    QuizSubmitResponse,
    PemahamanSubmitResponse,
    RumusanSubmitResponse,
    QuizQuestion,
    QuizRetryRequest,
    QuizAnswer,
    QuizType,
)
from services.comprehension_service import (
    generate_questions_for_type,
    score_submission,
    score_latihan_submission,
)

router = APIRouter()


class LatihanComprehensionSubmitRequest(BaseModel):
    session_id: str
    user_id: str
    quiz_type: QuizType
    answers: List[QuizAnswer]


# ── Comprehension quiz metadata ─────────────────────────────────────────────
COMPREHENSION_META = {
    "golongan_kata": {
        "paper": "paper2",
        "title": "Kenal Pasti Golongan Kata",
        "description": "Soalan mengenal pasti golongan kata",
        "instructions": (
            "Kenal pasti golongan kata bagi perkataan yang dicetak tebal "
            "dalam ayat-ayat berikut."
        ),
        "time_limit_minutes": 15,
    },
    "bina_ayat": {
        "paper": "paper2",
        "title": "Bina Ayat",
        "description": "Membina ayat berdasarkan perkataan diberi",
        "instructions": (
            "Bina ayat yang lengkap dan gramatis menggunakan perkataan "
            "yang diberikan. Pastikan ayat anda bermakna dan tepat."
        ),
        "time_limit_minutes": 20,
    },
    "jenis_ayat": {
        "paper": "paper2",
        "title": "Kenal Pasti Jenis Ayat",
        "description": "Menukar bentuk ayat secara tepat",
        "instructions": (
            "Kenal pasti jenis ayat atau tukar ayat kepada bentuk yang "
            "diminta berdasarkan arahan setiap soalan."
        ),
        "time_limit_minutes": 15,
    },
    "kesalahan_bahasa": {
        "paper": "paper2",
        "title": "Kenal Pasti Kesalahan Bahasa",
        "description": "Mengenal pasti dan membetulkan kesalahan",
        "instructions": (
            "Kenal pasti kesalahan bahasa dalam ayat-ayat berikut dan "
            "tulis semula ayat tersebut dengan betul."
        ),
        "time_limit_minutes": 20,
    },
    "pemahaman": {
        "paper": "paper2",
        "title": "Pemahaman",
        "description": "Dua bahan rangsangan dan soalan pemahaman",
        "instructions": (
            "Baca kedua-dua bahan berikut dengan teliti, kemudian jawab soalan-soalan "
            "yang berikutnya berdasarkan bahan-bahan tersebut."
        ),
        "time_limit_minutes": 30,
    },
    "rumusan": {
        "paper": "paper2",
        "title": "Rumusan",
        "description": "Tiga bahan rangsangan ringkas untuk rumusan",
        "instructions": (
            "Baca ketiga-tiga bahan dengan teliti, kemudian tulis rumusan "
            "tidak lebih daripada 120 patah perkataan."
        ),
        "time_limit_minutes": 35,
    },
}


@router.post("/start", response_model=QuizStartResponse)
async def start_comprehension(req: QuizStartRequest):
    """
    Called when user starts a Paper 2 quiz/practice.
    Returns a session + generated questions for that quiz type.
    """
    meta = COMPREHENSION_META.get(req.quiz_type)
    if not meta:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown comprehension type: {req.quiz_type}. "
            f"Valid types: {list(COMPREHENSION_META.keys())}",
        )

    session_id = str(uuid.uuid4())
    questions = await generate_questions_for_type(
        req.quiz_type,
        session_id,
        req.user_id,
        req.difficulty,
        req.mode,
    )

    return QuizStartResponse(
        session_id=session_id,
        quiz_type=req.quiz_type,
        paper=meta["paper"],
        title=meta["title"],
        description=meta["description"],
        instructions=meta["instructions"],
        questions=questions,
        time_limit_minutes=meta.get("time_limit_minutes"),
    )


@router.post(
    "/submit",
    response_model=Union[
        QuizSubmitResponse,
        PemahamanSubmitResponse,
        RumusanSubmitResponse,
    ],
)
async def submit_comprehension(req: QuizSubmitRequest):
    """
    Real Paper 2 quiz submit.
    This DOES save result and update dashboard.
    """
    if req.quiz_type not in COMPREHENSION_META:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown comprehension type: {req.quiz_type}. "
            f"Valid types: {list(COMPREHENSION_META.keys())}",
        )

    try:
        result = await score_submission(req)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print("Unexpected error in submit_comprehension:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/latihan-submit",
    response_model=Union[
        QuizSubmitResponse,
        PemahamanSubmitResponse,
        RumusanSubmitResponse,
    ],
)
async def submit_latihan_comprehension(req: LatihanComprehensionSubmitRequest):
    """
    Paper 2 latihan submit.
    This only marks and returns feedback.
    It does NOT save result and does NOT update dashboard.
    """
    if req.quiz_type not in COMPREHENSION_META:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown comprehension type: {req.quiz_type}. "
            f"Valid types: {list(COMPREHENSION_META.keys())}",
        )

    try:
        result = await score_latihan_submission(req)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        print("Unexpected error in submit_latihan_comprehension:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resume-latest")
def resume_latest(quiz_type: str, user_id: str):
    session = database.comprehension_sessions_col.find_one(
        {
            "quiz_type": quiz_type,
            "user_id": user_id,
            "status": "in_progress",
            "mode": "quiz",
            "expires_at": {"$gt": datetime.now(timezone.utc)},
        },
        sort=[("created_at", -1)],
    )

    if not session:
        raise HTTPException(status_code=404, detail="No active session")

    meta = COMPREHENSION_META.get(session["quiz_type"])

    return {
        "session_id": session["session_id"],
        "quiz_type": session["quiz_type"],
        "questions": session["questions"],
        "status": session["status"],
        "expires_at": session["expires_at"],
        **meta,
    }


@router.post("/retry", response_model=QuizStartResponse)
async def retry_comprehension(req: QuizRetryRequest):
    try:
        old_session = database.comprehension_sessions_col.find_one(
            {
                "session_id": req.session_id,
                "user_id": req.user_id,
            }
        )

        if not old_session:
            raise HTTPException(status_code=404, detail="Original session not found")

        new_session_id = str(uuid.uuid4())
        questions = old_session.get("questions", [])

        database.comprehension_sessions_col.insert_one(
            {
                "session_id": new_session_id,
                "user_id": req.user_id,
                "quiz_type": old_session["quiz_type"],
                "questions": questions,
                "mode": old_session.get("mode", "quiz"),
                "status": "in_progress",
                "created_at": datetime.now(timezone.utc),
                "expires_at": datetime.now(timezone.utc) + timedelta(hours=2),
                "retry_from": req.session_id,
            }
        )

        meta = COMPREHENSION_META.get(old_session["quiz_type"])

        if not meta:
            raise HTTPException(status_code=400, detail="Invalid quiz type in session")

        return QuizStartResponse(
            session_id=new_session_id,
            quiz_type=old_session["quiz_type"],
            paper=meta["paper"],
            title=meta["title"],
            description=meta["description"],
            instructions=meta["instructions"],
            questions=questions,
            time_limit_minutes=meta.get("time_limit_minutes"),
        )

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/types")
def get_comprehension_types():
    """
    Returns all available Paper 2 types with metadata.
    Used by QuizPage.tsx to render the Kertas 2 cards.
    """
    return {
        "paper2": [
            {**{"quiz_type": k}, **v}
            for k, v in COMPREHENSION_META.items()
        ]
    }