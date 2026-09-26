import uuid
from typing import List, Optional, Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
import database
from schemas.models import (
    ListeningStartRequest,
    ListeningQuestion,
    ListeningPetikan,
    ListeningStartResponse,
    ListeningAnswer,
    ListeningSubmitRequest,
    ListeningQuestionFeedback,
    ListeningSubmitResponse,
    ListeningRetryRequest,
)
from services.listening_service import (
    generate_listening_session,
    score_listening_submission,
    score_latihan_listening_submission,
    _hide_answer_scheme_for_frontend,
)

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# METADATA
# ─────────────────────────────────────────────────────────────────────────────

LISTENING_META = {
    "mendengar": {
        "paper": "paper4",
        "title": "Ujian Mendengar",
        "description": "Dengar audio dan jawab soalan berdasarkan petikan.",
        "instructions": (
            "Dengar audio dengan teliti. Jawab semua soalan berdasarkan "
            "maklumat yang didengar dalam audio."
        ),
        "time_limit_minutes": 30,
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/tasks")
async def get_listening_tasks():
    return LISTENING_META


@router.post("/start", response_model=ListeningStartResponse)
async def start_listening(req: ListeningStartRequest):
    meta = LISTENING_META.get(req.task_type)

    if not meta:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown task type: {req.task_type}",
        )

    session_id = str(uuid.uuid4())

    try:
        data = await generate_listening_session(
            session_id=session_id,
            user_id=req.user_id,
            difficulty=req.difficulty,
            mode=req.mode,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate listening session: {str(e)}",
        )

    return ListeningStartResponse(
        session_id=session_id,
        task_type=req.task_type,
        paper=meta["paper"],
        title=meta["title"],
        description=meta["description"],
        instructions=meta["instructions"],
        time_limit_minutes=meta["time_limit_minutes"],
        tema=data["tema"],
        audio_url=data["audio_url"],
        petikans=data["petikans"],
    )


@router.post("/submit", response_model=ListeningSubmitResponse)
async def submit_listening(req: ListeningSubmitRequest):
    if req.task_type != "mendengar":
        raise HTTPException(
            status_code=400,
            detail="Invalid task type. Expected 'mendengar'.",
        )

    try:
        result = await score_listening_submission(
            session_id=req.session_id,
            user_id=req.user_id,
            answers=[answer.model_dump() for answer in req.answers],
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to mark listening submission: {str(e)}",
        )

    return result

@router.post("/latihan-submit", response_model=ListeningSubmitResponse)
async def submit_latihan_listening(req: ListeningSubmitRequest):
    if req.task_type != "mendengar":
        raise HTTPException(
            status_code=400,
            detail="Invalid task type. Expected 'mendengar'.",
        )

    try:
        result = await score_latihan_listening_submission(
            session_id=req.session_id,
            user_id=req.user_id,
            answers=[answer.model_dump() for answer in req.answers],
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to mark listening latihan submission: {str(e)}",
        )

    return result

@router.get("/resume-latest")
def resume_latest(quiz_type: str, user_id: str):
    session = database.listening_sessions_col.find_one(
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

    meta = LISTENING_META.get(session["quiz_type"])

    return {
        "session_id": session["session_id"],
        "task_type": session["quiz_type"],
        "tema": session["tema"],
        "audio_url": session["audio_url"],
        "petikans": _hide_answer_scheme_for_frontend(session)["petikans"],
        "status": session["status"],
        "expires_at": session["expires_at"],
        **meta,
    }


@router.post("/retry", response_model=ListeningStartResponse)
async def retry_listening(req: ListeningRetryRequest):
    try:
        old_session = database.listening_sessions_col.find_one({
            "session_id": req.session_id,
            "user_id": req.user_id,
        })

        if not old_session:
            raise HTTPException(status_code=404, detail="Original session not found")

        new_session_id = str(uuid.uuid4())

        database.listening_sessions_col.insert_one({
            "session_id": new_session_id,
            "user_id": req.user_id,
            "quiz_type": old_session["quiz_type"],
            "difficulty": old_session.get("difficulty", "medium"),
            "tema": old_session.get("tema"),
            "audio_script": old_session.get("audio_script"),
            "audio_url": old_session.get("audio_url"),
            "petikans": old_session.get("petikans", []),
            "mode": old_session.get("mode", "quiz"),
            "status": "in_progress",
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=2),
            "retry_from": req.session_id,
        })

        meta = LISTENING_META.get(old_session["quiz_type"])
        if not meta:
            raise HTTPException(status_code=400, detail="Invalid quiz type in session")

        safe = _hide_answer_scheme_for_frontend({
            **old_session,
            "audio_url": old_session.get("audio_url"),
        })

        return ListeningStartResponse(
            session_id=new_session_id,
            task_type=old_session["quiz_type"],
            paper=meta["paper"],
            title=meta["title"],
            description=meta["description"],
            instructions=meta["instructions"],
            time_limit_minutes=meta["time_limit_minutes"],
            tema=old_session.get("tema", ""),
            audio_url=old_session.get("audio_url", ""),
            petikans=safe["petikans"],
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
