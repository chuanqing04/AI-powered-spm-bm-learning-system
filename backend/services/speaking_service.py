"""
Service layer for SPM Paper 3 (Ujian Lisan) speaking assessment.
Mirrors the structure of quiz_service.py.

Responsibilities:
  - Save 5 uploaded audio files to disk (async)
  - Orchestrate the full scoring pipeline via speaking_scorer.py
  - Build the SpeakingSubmitResponse returned to the router

5 audio clips per submission:
  audio_bacaan  — bacaan mekanis (pronunciation/fluency/grammar only)
  audio_r1      — soalan rangsangan 1
  audio_r2      — soalan rangsangan 2
  audio_k1      — soalan KBAT 1
  audio_k2      — soalan KBAT 2
"""
import uuid
import aiofiles
from pathlib import Path
from typing import Optional, List
import database
from datetime import datetime, timezone, timedelta
from schemas.models import SpeakingSubmitResponse, ClipResult
from machineLearning.speaking_scorer import score_speaking
from services.agentic_gemini import _ask_gemini, OutputSchema
from services.adaptive_engine import get_adaptive_difficulty
from services.user_results_memory import get_weak_areas, update_result


SPEAKING_SCHEMA = OutputSchema(
    root_type=dict,
    required_keys=[
        "tema",
        "stimulus_text",
        "soalan_rangsangan",
        "soalan_kbat",
    ],
)


# ── Helper: Get session for resuming speaking if available ───────────────────────
def get_valid_session(session_id: str):
    session = database.speaking_sessions_col.find_one(
        {"session_id": session_id}
    )

    if not session:
        return None

    if session.get("status") != "in_progress":
        return None

    expires_at = session.get("expires_at")

    if isinstance(expires_at, str):
        from dateutil import parser
        expires_at = parser.isoparse(expires_at)

    if not expires_at:
        return None

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > expires_at:
        database.speaking_sessions_col.update_one(
            {"session_id": session_id},
            {"$set": {"status": "expired"}}
        )
        return None

    return session


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG — AUDIO STORAGE
# ─────────────────────────────────────────────────────────────────────────────

# Temporary directory for uploaded audio files
# Replace with AWS S3 upload in production
AUDIO_UPLOAD_DIR = Path("uploads/audio")
AUDIO_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# AUDIO FILE HANDLING
# ─────────────────────────────────────────────────────────────────────────────

async def save_audio_file(file, session_id: str, clip_id: str) -> str:
    """
    Saves a single UploadFile to AUDIO_UPLOAD_DIR.
    Filename: <session_id>_<clip_id>.<ext>  e.g. abc123_bacaan.webm
    Returns the saved file path string.
    """
    suffix   = Path(file.filename).suffix if file.filename else ".wav"
    filename = f"{session_id}_{clip_id}{suffix}"
    filepath = AUDIO_UPLOAD_DIR / filename

    async with aiofiles.open(filepath, "wb") as out_file:
        content = await file.read()
        await out_file.write(content)

    return str(filepath)


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE (Paper 3)
# ─────────────────────────────────────────────────────────────────────────────

async def _save_speaking_session(
    session_id: str,
    quiz_type: str,
    session_data: dict,
    user_id: str,
    mode: str = "quiz",
):
    """Save generated questions to MongoDB when /start is called."""
    if database.speaking_sessions_col is None:
        raise RuntimeError("MongoDB not initialized")

    doc = {
        "session_id":  session_id,
        "quiz_type":   quiz_type,
        "tema": session_data["tema"],
        "stimulus_text": session_data["stimulus_text"],
        "soalan_rangsangan": session_data["soalan_rangsangan"],
        "soalan_kbat": session_data["soalan_kbat"],
        "user_id":     user_id,
        "mode":        mode,
        "status":      "in_progress",           
        "created_at":  datetime.now(timezone.utc),
        "expires_at":  datetime.now(timezone.utc) + timedelta(hours=2),        
    }
    database.speaking_sessions_col.insert_one(doc)


async def _save_speaking_result(response, user_id: str):
    """Save scoring result to MongoDB when /submit is called."""
    if database.speaking_results_col is None:
        raise RuntimeError("MongoDB not initialized")

    doc = response.model_dump()
    doc["user_id"]    = user_id
    doc["saved_at"]   = datetime.now(timezone.utc)
    database.speaking_results_col.insert_one(doc)


# ─────────────────────────────────────────────────────────────────────────────
# LISAN GENERATION PROMPTS (Paper 3)
# ─────────────────────────────────────────────────────────────────────────────

_LISAN_PROMPT = """
Anda adalah pemeriksa SPM Bahasa Melayu berpengalaman.
Jana satu set bahan rangsangan Ujian Lisan SPM yang lengkap dan KOHEREN.
Semua bahagian MESTI berkait rapat dengan SATU tema yang sama.

Langkah:
1. Pilih SATU tema semasa yang sesuai untuk pelajar tingkatan 5
2. Tulis petikan bahan rangsangan berdasarkan tema tersebut
3. Jana semua soalan berkait dengan petikan dan tema yang sama

Format petikan:
- 150–200 patah perkataan
- Bahasa Melayu formal
- Gaya rencana/artikel

Format soalan rangsangan (2 sahaja):
- Berdasarkan petikan
- 1 faktual
- 1 inferensi

Format soalan KBAT (2 sahaja):
- Berkait dengan tema
- Perlu pemikiran kritis
- Aras analisis / penilaian

Kembalikan JSON sahaja:
{
  "tema": "<tema>",
  "stimulus_text": "<petikan>",
  "soalan_rangsangan": [
    {"question_id": "r1", "question_text": "<soalan>"},
    {"question_id": "r2", "question_text": "<soalan>"}
  ],
  "soalan_kbat": [
    {"question_id": "k1", "question_text": "<soalan>"},
    {"question_id": "k2", "question_text": "<soalan>"}
  ]
}
"""

DIFFICULTY_RULES = {
    "easy": {
        "topic": "tema harian yang dekat dengan kehidupan pelajar seperti sekolah, keluarga, kesihatan, hobi atau amalan baik",
        "stimulus": "petikan mudah dengan isi yang jelas, ayat tidak terlalu panjang dan maksud yang terus",
        "questions": "soalan rangsangan mudah yang boleh dijawab terus berdasarkan petikan",
        "kbat": "soalan KBAT asas yang meminta pendapat, sebab atau cadangan mudah",
    },
    "medium": {
        "topic": "tema semasa berkaitan remaja, masyarakat, pendidikan, teknologi, alam sekitar atau kesihatan awam",
        "stimulus": "petikan sederhana dengan beberapa isi utama, contoh dan hubungan sebab-akibat",
        "questions": "soalan rangsangan yang memerlukan pemahaman dan sedikit inferens",
        "kbat": "soalan KBAT yang meminta huraian, kesan, kepentingan atau langkah penyelesaian",
    },
    "hard": {
        "topic": "tema mencabar seperti isu global, ekonomi, etika teknologi, perpaduan, kepimpinan, jati diri atau masa depan negara",
        "stimulus": "petikan matang dan analitis dengan isu pelbagai dimensi serta idea yang lebih abstrak",
        "questions": "soalan rangsangan yang memerlukan inferens, analisis dan penilaian",
        "kbat": "soalan KBAT tinggi yang memerlukan hujah matang, penilaian kritis dan cadangan bernas",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# QUESTION GENERATION (Paper 3)
# ─────────────────────────────────────────────────────────────────────────────

async def generate_questions_for_type(
    session_id: str,
    user_id: str,
    requested_difficulty: Optional[str] = None,
    mode: str = "quiz",
) -> dict:
    weak_areas = get_weak_areas(user_id)

    # LATIHAN MODE:
    # Only use selected easy/medium/hard if frontend sends requested_difficulty.
    if requested_difficulty:
        difficulty = requested_difficulty

        if difficulty not in DIFFICULTY_RULES:
            difficulty = "medium"

        rule = DIFFICULTY_RULES[difficulty]

        adaptive_prompt = _LISAN_PROMPT + f"""
MAKLUMAT PELAJAR:
- Tahap kesukaran sasaran: **{difficulty}**

WAJIB ikut tahap kesukaran ini:
- easy = mudah
- medium = sederhana
- hard = sukar / KBAT

Panduan tahap ini:
- Tema: {rule["topic"]}
- Petikan: {rule["stimulus"]}
- Soalan rangsangan: {rule["questions"]}
- Soalan KBAT: {rule["kbat"]}

Pastikan petikan dan soalan yang dijana benar-benar sepadan dengan tahap **{difficulty}**.
"""

    # QUIZ MODE:
    # If no selected difficulty is sent, keep the original adaptive behavior.
    else:
        difficulty = get_adaptive_difficulty(user_id, "lisan")

        adaptive_prompt = _LISAN_PROMPT + f"""
MAKLUMAT PELAJAR:
- Tahap kesukaran sasaran: **{difficulty}**
"""

    if weak_areas:
        adaptive_prompt += f"""
- Kawasan lemah pelajar: {", ".join(weak_areas)}
Pelajar menunjukkan kelemahan dalam aspek tersebut. Fokuskan soalan yang dapat membantu memperbaiki kemahiran ini secara berperingkat dan jelas.
"""

    data = await _ask_gemini(adaptive_prompt, schema=SPEAKING_SCHEMA,)
    
    if not data:
        raise ValueError("Failed to generate speaking questions from Gemini")

    # Normalize IDs
    for q in data.get("soalan_rangsangan", []):
        if not q.get("question_id"):
            q["question_id"] = str(uuid.uuid4())

    for q in data.get("soalan_kbat", []):
        if not q.get("question_id"):
            q["question_id"] = str(uuid.uuid4())

    result = {
        "tema": data.get("tema", ""),
        "stimulus_text": data.get("stimulus_text", ""),
        "soalan_rangsangan": data.get("soalan_rangsangan", []),
        "soalan_kbat": data.get("soalan_kbat", []),
    }

    await _save_speaking_session(
        session_id,
        "lisan",
        {
            "tema":              result["tema"],
            "stimulus_text":     result["stimulus_text"],
            "soalan_rangsangan": result["soalan_rangsangan"],
            "soalan_kbat":       result["soalan_kbat"],
        },
        user_id=user_id,
        mode=mode,
    )

    return result


# ─────────────────────────────────────────────────────────────────────────────
# MAIN SCORING ORCHESTRATOR
# ─────────────────────────────────────────────────────────────────────────────

async def score_speaking_submission(
    session_id:        str,
    task_type:         str,
    user_id:           str,
    path_bacaan:       str,
    path_r1:           str,
    path_r2:           str,
    path_k1:           str,
    path_k2:           str,
    stimulus_text:     str,
    soalan_rangsangan: List[dict],   # [{"question_id": str, "question_text": str}]
    soalan_kbat:       List[dict],   # [{"question_id": str, "question_text": str}]
    reference_texts:   Optional[dict] = None,
) -> SpeakingSubmitResponse:
    """
    Runs the full SPM Lisan scoring pipeline across 5 audio clips
    and builds the SpeakingSubmitResponse returned to the router.

    Parameters
    ----------
    session_id        : UUID from the session store in speaking.py
    task_type         : "lisan"
    path_bacaan       : saved path for bacaan mekanis clip
    path_r1 / path_r2 : saved paths for soalan rangsangan clips
    path_k1 / path_k2 : saved paths for soalan KBAT clips
    stimulus_text     : Gemini-generated bahan rangsangan petikan
    soalan_rangsangan : 2 questions directly based on the petikan
    soalan_kbat       : 2 KBAT questions related to the same theme
    """

    """Look up the session's stored questions, then score the speaking."""
    session = get_valid_session(session_id)

    if not session:
        raise ValueError(
            f"Session '{session_id}' not found or has expired. "
            "Please call /api/speaking/start first."
        )

    if session.get("mode", "quiz") != "quiz":
        raise ValueError("This session is a latihan session and cannot be submitted as a quiz.")

    try:
        result = await score_speaking(
            path_bacaan        = path_bacaan,
            path_r1            = path_r1,
            path_r2            = path_r2,
            path_k1            = path_k1,
            path_k2            = path_k2,
            stimulus_text      = stimulus_text,
            soalan_rangsangan  = soalan_rangsangan,
            soalan_kbat        = soalan_kbat,
            reference_texts    = reference_texts or {},
        )
    except Exception as e:
        import traceback
        print("SCORING CRASH:")
        print(str(e))
        print(traceback.format_exc())
        raise

    if not result:
        raise ValueError("score_speaking returned None")

    required_keys = ["clips", "grammar_vocabulary", "pronunciation", "fluency", "ideas"]

    missing = [k for k in required_keys if k not in result]
    if missing:
        raise ValueError(f"Missing keys in scoring result: {missing}")

    # ── Build ClipResult list from raw scorer output ──────────────────────────
    clip_objects = [
        ClipResult(
            clip_id=c["clip_id"],
            transcription=c["transcription"],
            no_speech=c.get("no_speech", False),
            no_speech_reason=c.get("no_speech_reason", None),

            grammar_vocabulary=c["grammar_vocabulary"],

            pronunciation=c["pronunciation"],

            fluency=c["fluency"],

            ideas=c.get("ideas"),

            wer=c.get("wer"),
        )
        for c in result["clips"]
    ]

    result_response = SpeakingSubmitResponse(
        session_id    = session_id,
        task_type     = task_type,

        # Per-clip results
        clips = clip_objects,

        # Trait 1 — grammar & vocabulary # tatabahasa & kosa kata
        grammar_vocabulary = result["grammar_vocabulary"],

        # Trait 2 — pronunciation # sebutan, intonasi & nada
        pronunciation      = result["pronunciation"],
 
        # Trait 3 — fluency # kefasihan & kelancaran
        fluency            = result["fluency"],

        # Trait 4 — ideas # idea & bermakna
        ideas              = result["ideas"],
        
        bacaan_wer         = result["bacaan_wer"],

        # Overall band
        total_score         = result["total_score"],
        overall_band        = result["overall_band"],
        overall_descriptor  = result["overall_descriptor"],

        # Evaluation
        processing_time_s = result["processing_time_s"],
    )

    database.speaking_sessions_col.update_one(
        {"session_id": session_id},
        {"$set": {"status": "completed"}}
    )

    await _save_speaking_result(result_response, user_id=user_id)

    update_result(
        user_id=user_id,
        quiz_type="lisan",
        raw_score=result["total_score"],
        max_score=1.0
    )

    return result_response

async def score_latihan_speaking_submission(
    session_id:        str,
    task_type:         str,
    user_id:           str,
    path_bacaan:       str,
    path_r1:           str,
    path_r2:           str,
    path_k1:           str,
    path_k2:           str,
    stimulus_text:     str,
    soalan_rangsangan: List[dict],
    soalan_kbat:       List[dict],
    reference_texts:   Optional[dict] = None,
) -> SpeakingSubmitResponse:
    """
    Runs speaking marking for latihan only.

    This intentionally does NOT:
    - save to speaking results collection
    - call update_result(...)
    - affect dashboard marks
    """
    session = get_valid_session(session_id)

    if not session:
        raise ValueError(
            f"Session '{session_id}' not found or has expired. "
            "Please call /api/speaking/start first."
        )

    if session.get("mode", "quiz") != "quiz":
        raise ValueError("This session is a latihan session and cannot be submitted as a quiz.")

    try:
        result = await score_speaking(
            path_bacaan        = path_bacaan,
            path_r1            = path_r1,
            path_r2            = path_r2,
            path_k1            = path_k1,
            path_k2            = path_k2,
            stimulus_text      = stimulus_text,
            soalan_rangsangan  = soalan_rangsangan,
            soalan_kbat        = soalan_kbat,
            reference_texts    = reference_texts or {},
        )
    except Exception as e:
        import traceback
        print("LATIHAN SPEAKING SCORING CRASH:")
        print(str(e))
        print(traceback.format_exc())
        raise

    if not result:
        raise ValueError("score_speaking returned None")

    required_keys = ["clips", "grammar_vocabulary", "pronunciation", "fluency", "ideas"]

    missing = [k for k in required_keys if k not in result]
    if missing:
        raise ValueError(f"Missing keys in scoring result: {missing}")

    clip_objects = [
        ClipResult(
            clip_id=c["clip_id"],
            transcription=c.get("transcription", ""),
            no_speech=c.get("no_speech", False),
            no_speech_reason=c.get("no_speech_reason", None),
            grammar_vocabulary=c["grammar_vocabulary"],
            pronunciation=c["pronunciation"],
            fluency=c["fluency"],
            ideas=c.get("ideas"),
            wer=c.get("wer"),
        )
        for c in result["clips"]
    ]

    result_response = SpeakingSubmitResponse(
        session_id    = session_id,
        task_type     = task_type,
        clips         = clip_objects,

        grammar_vocabulary = result["grammar_vocabulary"],
        pronunciation      = result["pronunciation"],
        fluency            = result["fluency"],
        ideas              = result["ideas"],

        bacaan_wer         = result["bacaan_wer"],
        total_score        = result["total_score"],
        overall_band       = result["overall_band"],
        overall_descriptor = result["overall_descriptor"],
        processing_time_s  = result["processing_time_s"],
    )

    database.speaking_sessions_col.update_one(
        {"session_id": session_id},
        {"$set": {"status": "completed"}}
    )

    return result_response