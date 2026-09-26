"""
Endpoints for SPM Paper 3 (Ujian Lisan) speaking assessment.

POST /api/speaking/start   → Gemini generates stimulus + questions, returns session_id + content
POST /api/speaking/submit  → upload audio, score it, return band + feedback
GET  /api/speaking/tasks   → list available SPM Lisan task types
"""

import uuid, traceback, json
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from datetime import datetime, timedelta, timezone
import database
from schemas.models import (
    SpeakingStartRequest,
    SpeakingStartResponse,
    SpeakingSubmitResponse,
    LisanQuestion,
    SpeakingRetryRequest,
)
from services.speaking_service import (
    save_audio_file,
    score_speaking_submission,
    score_latihan_speaking_submission,
    generate_questions_for_type,
)

router = APIRouter()

# Clip IDs — matches the 5 audio file fields in /submit
CLIP_IDS = ("bacaan", "r1", "r2", "k1", "k2")


# ── Speaking task metadata ─────────────────────────────────────────────────────
SPEAKING_META = {
    "lisan": {  # Paper 3 — Ujian Lisan
        "paper":               "paper3",
        "title":               "Ujian Lisan",
        "description":         "Bacaan mekanis dan soalan berdasarkan bahan rangsangan",
        "instructions": (
            "Sesi Ujian Lisan mengandungi tiga bahagian: "
            "(1) Bacaan mekanis petikan bahan rangsangan, "
            "(2) 2 soalan berdasarkan bahan rangsangan, dan "
            "(3) 2 soalan KBAT berkaitan bahan rangsangan. "
            "Anda mempunyai 3 minit untuk membaca bahan rangsangan "
            "sebelum sesi bermula."
        ),
        "time_limit_minutes":  5,
        "scored_traits": [
            "grammar_vocabulary",   # tatabahasa & kosa kata
            "pronunciation",        # sebutan, intonasi & nada
            "fluency",              # kefasihan & kelancaran
            "ideas",                # idea & bermakna
        ],
    },
}

# Allowed audio MIME types for the submit endpoint
ALLOWED_AUDIO_TYPES = {
    "audio/wav",
    "audio/mpeg",       # .mp3
    "audio/mp4",        # .m4a
    "audio/x-m4a",
    "audio/webm",       # browser MediaRecorder default
    "video/webm",
    "audio/weba",
    "audio/ogg",
}


@router.post("/start", response_model=SpeakingStartResponse)
async def start_speaking(req: SpeakingStartRequest):
    """
    Called when the student selects the Ujian Lisan card and clicks Start.

    Gemini generates in one coherent call:
      - A stimulus petikan (bahan rangsangan) on a single chosen theme
      - 2 soalan berdasarkan bahan rangsangan (factual + inferential)
      - 2 soalan KBAT on the same theme (analysis + evaluation/synthesis)

    All content is stored in _speaking_sessions keyed by session_id so that
    POST /api/speaking/submit can retrieve it for relevance scoring without
    the frontend needing to send it back.
    """
    meta = SPEAKING_META.get(req.task_type)
    if not meta:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown task type: '{req.task_type}'. "
                   f"Valid options: {list(SPEAKING_META.keys())}",
        )

    session_id = str(uuid.uuid4())
    lisan_content = await generate_questions_for_type(
        session_id,
        req.user_id,
        req.difficulty,
        req.mode,
    )

    # ── Build typed question lists for the response ───────────────────────────
    soalan_rangsangan = [
        LisanQuestion(
            question_id       = q["question_id"],
            question_text     = q["question_text"],
        )
        for q in lisan_content["soalan_rangsangan"]
    ]
    soalan_kbat = [
        LisanQuestion(
            question_id       = q["question_id"],
            question_text     = q["question_text"],
        )
        for q in lisan_content["soalan_kbat"]
    ]

    return SpeakingStartResponse(
        session_id         = session_id,
        task_type          = req.task_type,
        paper              = meta["paper"],
        title              = meta["title"],
        description        = meta["description"],
        instructions       = meta["instructions"],
        time_limit_minutes = meta["time_limit_minutes"],
        scored_traits      = meta["scored_traits"],
        tema               = lisan_content["tema"],
        stimulus_text      = lisan_content["stimulus_text"],
        soalan_rangsangan  = soalan_rangsangan,
        soalan_kbat        = soalan_kbat,
    )


@router.post("/submit", response_model=SpeakingSubmitResponse)
async def submit_speaking(
    session_id: str = Form(...),
    task_type: str = Form(...),
    user_id: str = Form(...),

    stimulus_text: str = Form(...),
    soalan_rangsangan: str = Form(...),
    soalan_kbat: str = Form(...),

    audio_bacaan: UploadFile = File(...),
    audio_r1: UploadFile = File(...),
    audio_r2: UploadFile = File(...),
    audio_k1: UploadFile = File(...),
    audio_k2: UploadFile = File(...),
):
    """
    Called when the student submits all 5 recordings at the end of the session.
    Returns SPM Band 1–6 scores for all four Lisan traits plus overall band.
 
    Questions are retrieved from DB using session_id.
    """

    if task_type not in SPEAKING_META:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown task type: {task_type}. "
                   f"Valid types: {list(SPEAKING_META.keys())}",
        )
 
    # ── Validate audio MIME types ──────────────────────────────────────
    audio_files = {
        "bacaan": audio_bacaan,
        "r1": audio_r1,
        "r2": audio_r2,
        "k1": audio_k1,
        "k2": audio_k2,
    }

    for clip_id, f in audio_files.items():
        if f.content_type not in ALLOWED_AUDIO_TYPES:
            raise HTTPException(
                status_code=415,
                detail=(
                    f"audio_{clip_id}: unsupported format '{f.content_type}'. "
                    f"Accepted: wav, mp3, m4a, webm, weba, ogg."
                ),
            )
  
    # ── Save audio files ────────────────────────────────────────────────
    try:
        saved_paths = {}
        for clip_id, f in audio_files.items():
            saved_paths[clip_id] = await save_audio_file(f, session_id, clip_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save audio file: {str(e)}",
        )

    # ── Score ─────────────────────────────────────────────────────────────────
    try:
        result = await score_speaking_submission(
            session_id        = session_id,
            task_type         = task_type,
            user_id           = user_id,
            path_bacaan       = saved_paths["bacaan"],
            path_r1           = saved_paths["r1"],
            path_r2           = saved_paths["r2"],
            path_k1           = saved_paths["k1"],
            path_k2           = saved_paths["k2"],
            stimulus_text     = stimulus_text,
            soalan_rangsangan = json.loads(soalan_rangsangan),
            soalan_kbat       = json.loads(soalan_kbat),
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Internal scoring error",
                "error": str(e),
            }
        )
    return result

@router.post("/latihan-submit", response_model=SpeakingSubmitResponse)
async def submit_latihan_speaking(
    session_id: str = Form(...),
    task_type: str = Form(...),
    user_id: str = Form(...),

    stimulus_text: str = Form(...),
    soalan_rangsangan: str = Form(...),
    soalan_kbat: str = Form(...),

    audio_bacaan: UploadFile = File(...),
    audio_r1: UploadFile = File(...),
    audio_r2: UploadFile = File(...),
    audio_k1: UploadFile = File(...),
    audio_k2: UploadFile = File(...),
):
    """
    Latihan-only speaking submit.
    This marks speaking answers but does NOT update dashboard.
    """
    if task_type not in SPEAKING_META:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown task type: {task_type}. "
                   f"Valid types: {list(SPEAKING_META.keys())}",
        )

    audio_files = {
        "bacaan": audio_bacaan,
        "r1": audio_r1,
        "r2": audio_r2,
        "k1": audio_k1,
        "k2": audio_k2,
    }

    for clip_id, f in audio_files.items():
        if f.content_type not in ALLOWED_AUDIO_TYPES:
            raise HTTPException(
                status_code=415,
                detail=(
                    f"audio_{clip_id}: unsupported format '{f.content_type}'. "
                    f"Accepted: wav, mp3, m4a, webm, ogg."
                ),
            )

    try:
        saved_paths = {}

        for clip_id, f in audio_files.items():
            saved_paths[clip_id] = await save_audio_file(f, session_id, clip_id)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save audio file: {str(e)}",
        )

    try:
        result = await score_latihan_speaking_submission(
            session_id        = session_id,
            task_type         = task_type,
            user_id           = user_id,
            path_bacaan       = saved_paths["bacaan"],
            path_r1           = saved_paths["r1"],
            path_r2           = saved_paths["r2"],
            path_k1           = saved_paths["k1"],
            path_k2           = saved_paths["k2"],
            stimulus_text     = stimulus_text,
            soalan_rangsangan = json.loads(soalan_rangsangan),
            soalan_kbat       = json.loads(soalan_kbat),
        )

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Internal latihan speaking scoring error",
                "error": str(e),
            },
        )

    return result

@router.get("/resume-latest")
def resume_latest(quiz_type: str, user_id: str):

    session = database.speaking_sessions_col.find_one(
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

    meta = SPEAKING_META.get(session["quiz_type"])

    return {
        "session_id": session["session_id"],
        "quiz_type": session["quiz_type"],
        "stimulus_text": session["stimulus_text"],
        "soalan_rangsangan": session["soalan_rangsangan"],
        "soalan_kbat": session["soalan_kbat"],
        "status": session["status"],
        "expires_at": session["expires_at"],
        **meta
    }


@router.post("/retry", response_model=SpeakingStartResponse)
async def retry_speaking(req: SpeakingRetryRequest):

    try:
        # Fetch original session
        old_session = database.speaking_sessions_col.find_one({
            "session_id": req.session_id,
            "user_id": req.user_id
        })

        if not old_session:
            raise HTTPException(status_code=404, detail="Original session not found")

        # Generate new session_id
        new_session_id = str(uuid.uuid4())

        # Reuse same content
        stimulus_text = old_session.get("stimulus_text")
        soalan_rangsangan = old_session.get("soalan_rangsangan", [])
        soalan_kbat = old_session.get("soalan_kbat", [])

        # Insert new session
        database.speaking_sessions_col.insert_one({
            "session_id": new_session_id,
            "user_id": req.user_id,
            "quiz_type": old_session["quiz_type"],
            "tema": old_session.get("tema"),
            "stimulus_text": stimulus_text,
            "soalan_rangsangan": soalan_rangsangan,
            "soalan_kbat": soalan_kbat,
            "mode": old_session.get("mode", "quiz"),
            "status": "in_progress",
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=2),
            "retry_from": req.session_id
        })

        # Metadata
        meta = SPEAKING_META.get(old_session["quiz_type"])
        if not meta:
            raise HTTPException(status_code=400, detail="Invalid quiz type in session")

        # Return same structure as /start 
        return SpeakingStartResponse(
            session_id=new_session_id,
            task_type=old_session["quiz_type"],
            paper=meta["paper"],
            title=meta["title"],
            description=meta["description"],
            instructions=meta["instructions"],
            time_limit_minutes=meta.get("time_limit_minutes"),
            scored_traits=meta["scored_traits"],
            tema=old_session.get("tema"),
            stimulus_text=stimulus_text,
            soalan_rangsangan=soalan_rangsangan,
            soalan_kbat=soalan_kbat,
        )

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks")
def get_speaking_tasks():
    """
    Returns all available speaking task types with metadata.
    """
    return {
        "paper3": [
            {**{"task_type": k}, **v}
            for k, v in SPEAKING_META.items()
        ],
    }