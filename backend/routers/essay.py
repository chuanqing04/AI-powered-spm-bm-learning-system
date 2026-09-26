"""
Endpoints for Paper 1 (Karangan) quiz types.

POST /api/essay/start   → generate a karangan question for the given type
POST /api/essay/submit  → score the submitted essay, return rubric + feedback
GET  /api/essay/types   → list available karangan types with metadata
"""
import uuid, traceback
from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone, timedelta
import database
from schemas.models import (
    QuizStartRequest, QuizStartResponse,
    QuizSubmitRequest, QuizSubmitResponse,
    QuizQuestion, QuizRetryRequest
)
from services.essay_service import (
    generate_questions_for_type,
    score_submission,
)

router = APIRouter()


# ── Essay quiz metadata ─────────────────────────────────────────────────────
ESSAY_META = {
    "karangan_pendek": {
        "paper": "paper1",
        "title": "Karangan Pendek",
        "description": "150–200 patah perkataan • 30 markah",
        "instructions": (
            "Tulis sebuah karangan pendek berdasarkan tajuk yang diberikan. "
            "Panjang karangan hendaklah antara 150 hingga 200 patah perkataan. "
            "Karangan anda hendaklah mengandungi pendahuluan, isi dan penutup."
        ),
        "time_limit_minutes": 45,
    },
    "karangan_panjang": {
        "paper": "paper1",
        "title": "Karangan Panjang",
        "description": "350–500 patah perkataan • 70 markah",
        "instructions": (
            "Tulis sebuah karangan panjang berdasarkan tajuk yang diberikan. "
            "Panjang karangan hendaklah antara 350 hingga 500 patah perkataan. "
            "Beri perhatian kepada isi, bahasa dan tatabahasa."
        ),
        "time_limit_minutes": 75,
    },
}


@router.post("/start", response_model=QuizStartResponse)
async def start_essay(req: QuizStartRequest):
    """
    Called when user clicks 'Start' on a karangan card in QuizPage.tsx.
    Returns a session + a generated karangan question for that type.
    """
    meta = ESSAY_META.get(req.quiz_type)
    if not meta:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown essay type: {req.quiz_type}. "
                   f"Valid types: {list(ESSAY_META.keys())}",
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


@router.post("/submit", response_model=QuizSubmitResponse)
async def submit_essay(req: QuizSubmitRequest):
    """
    Called when user submits a karangan.
    Returns rubric breakdown (content, language, grammar, vocabulary, coherence)
    and AI-generated feedback in Bahasa Melayu.
    """
    if req.quiz_type not in ESSAY_META:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown essay type: {req.quiz_type}. "
                   f"Valid types: {list(ESSAY_META.keys())}",
        )
    try:
        result = await score_submission(req)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return result


@router.get("/resume-latest")
def resume_latest(quiz_type: str, user_id: str):

    session = database.essay_sessions_col.find_one(
        {
            "quiz_type": quiz_type,
            "user_id": user_id,
            "status": "in_progress",
            "mode": "quiz",
            "expires_at": {"$gt": datetime.now(timezone.utc)}
        },
        sort=[("created_at", -1)]
    )

    if not session:
        raise HTTPException(status_code=404, detail="No active session")

    meta = ESSAY_META.get(session["quiz_type"])

    return {
        "session_id": session["session_id"],
        "quiz_type": session["quiz_type"],
        "questions": session["questions"],
        "status": session["status"],
        "expires_at": session["expires_at"],
        **meta
    }


@router.post("/retry", response_model=QuizStartResponse)
async def retry_essay(req: QuizRetryRequest):
    try:
        # Fetch exact session
        old_session = database.essay_sessions_col.find_one({
            "session_id": req.session_id,
            "user_id": req.user_id
        })

        if not old_session:
            raise HTTPException(status_code=404, detail="Original session not found")

        # Generate new session_id
        new_session_id = str(uuid.uuid4())

        # Reuse same question
        questions = old_session.get("questions", [])

        # Insert new session
        database.essay_sessions_col.insert_one({
            "session_id": new_session_id,
            "user_id": req.user_id,
            "quiz_type": old_session["quiz_type"],
            "questions": questions,
            "mode": old_session.get("mode", "quiz"),
            "status": "in_progress",
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=2),
            "retry_from": req.session_id
        })

        # Metadata
        meta = ESSAY_META.get(old_session["quiz_type"])
        if not meta:
            raise HTTPException(status_code=400, detail="Invalid quiz type in session")

        # Return same structure as /start
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
def get_essay_types():
    """
    Returns all available karangan types with metadata.
    Used by QuizPage.tsx to render the Kertas 1 cards.
    """
    return {
        "paper1": [
            {**{"quiz_type": k}, **v}
            for k, v in ESSAY_META.items()
        ]
    }