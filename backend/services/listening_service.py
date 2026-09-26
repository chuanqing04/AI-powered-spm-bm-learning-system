import wave
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List

import edge_tts

import database
from services.agentic_gemini import _ask_gemini, OutputSchema
from services.user_results_memory import update_result


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

LISTENING_AUDIO_DIR = Path("uploads/listening")
LISTENING_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# Female, formal, Malaysian Malay voice
TTS_VOICE = "ms-MY-YasminNeural"

# Alternative male voice:
# TTS_VOICE = "ms-MY-OsmanNeural"


# ─────────────────────────────────────────────────────────────────────────────
# SCHEMA
# ─────────────────────────────────────────────────────────────────────────────

def _validate_listening_output(data: dict) -> str | None:
    if not data.get("tema"):
        return "Missing tema."

    if not data.get("audio_script"):
        return "Missing audio_script."

    petikans = data.get("petikans")
    if not isinstance(petikans, list) or len(petikans) < 2:
        return "petikans must be a list with at least 2 items."

    for i, petikan in enumerate(petikans):
        if not petikan.get("title"):
            return f"Petikan {i} missing title."

        questions = petikan.get("questions")
        if not isinstance(questions, list) or len(questions) < 1:
            return f"Petikan {i} must contain questions."

        for j, q in enumerate(questions):
            required = [
                "question_id",
                "question_text",
                "question_type",
                "marks",
                "answer_scheme",
            ]

            for key in required:
                if key not in q:
                    return f"Question {i}.{j} missing {key}."

            if q["question_type"] not in ["short_answer", "mcq", "true_false"]:
                return f"Question {i}.{j} has invalid question_type."

            if q["question_type"] == "mcq":
                if not isinstance(q.get("options"), list) or len(q["options"]) < 2:
                    return f"MCQ question {i}.{j} must have options."

            if not isinstance(q.get("answer_scheme"), list):
                return f"Question {i}.{j} answer_scheme must be a list."

    return None


LISTENING_SCHEMA = OutputSchema(
    root_type=dict,
    required_keys=["tema", "audio_script", "petikans"],
    custom_check=_validate_listening_output,
)


MARKING_SCHEMA = OutputSchema(
    root_type=dict,
    required_keys=[
        "total_score",
        "max_score",
        "percentage",
        "grade",
        "question_feedbacks",
        "overall_feedback",
        "suggestions",
    ],
)


# ─────────────────────────────────────────────────────────────────────────────
# PROMPTS
# ─────────────────────────────────────────────────────────────────────────────

_LISTENING_PROMPT = """
Anda ialah pemeriksa SPM Bahasa Melayu.

Jana satu set Ujian Mendengar Paper 4 yang lengkap.

Keperluan utama:
1. Pilih SATU tema sesuai untuk pelajar Tingkatan 5.
2. Jana skrip audio Bahasa Melayu formal.
3. Skrip audio mesti mengandungi PETIKAN SAHAJA.
4. Skrip audio TIDAK BOLEH mengandungi soalan.
5. Skrip audio TIDAK BOLEH mengandungi arahan seperti "jawab soalan", "baca soalan", "lihat soalan", atau "pilih jawapan".
6. Skrip audio TIDAK BOLEH menyebut skema jawapan.
7. Skrip audio TIDAK BOLEH menyuruh pelajar membaca soalan.
8. Skrip audio TIDAK BOLEH mengandungi muzik, bunyi hujan, bunyi latar, atau kesan bunyi.
9. Skrip audio mesti sesuai untuk DIDENGAR sebagai petikan ujian.
10. Jana soalan berdasarkan maklumat yang terdapat dalam skrip audio sahaja.
11. Jangan jana soalan yang tidak boleh dijawab melalui audio.
12. Campurkan jenis soalan:
   - short_answer
   - mcq
   - true_false
13. Jumlah markah sekitar 15 hingga 20 markah.
14. Bahasa soalan mesti sesuai dengan format latihan SPM Bahasa Melayu.

PENTING:
Medan "audio_script" mesti hanya mengandungi teks petikan yang akan dibaca oleh penyampai.
Medan "audio_script" jangan masukkan soalan.
Medan "audio_script" jangan masukkan arahan menjawab.
Medan "audio_script" jangan masukkan pilihan jawapan.
Medan "audio_script" jangan masukkan skema jawapan.
Medan "audio_script" jangan masukkan deskripsi bunyi seperti [bunyi hujan], [muzik], [suasana], atau [kesan bunyi].

Kembalikan JSON sahaja.
Jangan guna markdown.
Jangan tulis penjelasan.

Format JSON wajib:

{
  "tema": "<tema>",
  "audio_script": "PETIKAN 1. <teks petikan pertama sahaja>\\n\\nPETIKAN 2. <teks petikan kedua sahaja>\\n\\nPETIKAN 3. <teks petikan ketiga sahaja>",
  "petikans": [
    {
      "title": "PETIKAN 1",
      "questions": [
        {
          "question_id": "p1q1",
          "question_text": "<soalan>",
          "question_type": "short_answer",
          "marks": 2,
          "options": null,
          "answer_scheme": ["<jawapan diterima>", "<jawapan alternatif jika ada>"]
        },
        {
          "question_id": "p1q2",
          "question_text": "<soalan objektif>",
          "question_type": "mcq",
          "marks": 1,
          "options": ["A Pilihan pertama", "B Pilihan kedua", "C Pilihan ketiga", "D Pilihan keempat"],
          "answer_scheme": ["B"]
        },
        {
          "question_id": "p1q3",
          "question_text": "<soalan betul salah>",
          "question_type": "true_false",
          "marks": 1,
          "options": null,
          "answer_scheme": ["BETUL"]
        }
      ]
    },
    {
      "title": "PETIKAN 2",
      "questions": [
        {
          "question_id": "p2q1",
          "question_text": "<soalan>",
          "question_type": "short_answer",
          "marks": 2,
          "options": null,
          "answer_scheme": ["<jawapan diterima>"]
        },
        {
          "question_id": "p2q2",
          "question_text": "<soalan>",
          "question_type": "mcq",
          "marks": 1,
          "options": ["A Pilihan pertama", "B Pilihan kedua", "C Pilihan ketiga", "D Pilihan keempat"],
          "answer_scheme": ["A"]
        }
      ]
    },
    {
      "title": "PETIKAN 3",
      "questions": [
        {
          "question_id": "p3q1",
          "question_text": "<soalan>",
          "question_type": "short_answer",
          "marks": 2,
          "options": null,
          "answer_scheme": ["<jawapan diterima>"]
        },
        {
          "question_id": "p3q2",
          "question_text": "<soalan betul salah>",
          "question_type": "true_false",
          "marks": 1,
          "options": null,
          "answer_scheme": ["SALAH"]
        }
      ]
    }
  ]
}
"""


def _difficulty_instruction(difficulty: str) -> str:
    if difficulty == "easy":
        return """
Tahap kesukaran: MUDAH.

Arahan tahap:
1. Gunakan kosa kata mudah dan ayat pendek.
2. Maklumat dalam audio mesti jelas dan tersurat.
3. Soalan mestilah soalan fakta langsung.
4. Elakkan soalan inferens yang terlalu sukar.
5. Panjang skrip sekitar 300 hingga 450 patah perkataan.
6. Jumlah soalan sekitar 8 hingga 10 soalan.
"""

    if difficulty == "hard":
        return """
Tahap kesukaran: SUKAR.

Arahan tahap:
1. Gunakan kosa kata yang lebih mencabar tetapi masih sesuai untuk SPM.
2. Gunakan ayat yang lebih matang dan maklumat yang memerlukan perhatian teliti.
3. Masukkan beberapa soalan kefahaman tersirat atau inferens.
4. Elakkan soalan yang mustahil dijawab melalui audio.
5. Panjang skrip sekitar 650 hingga 850 patah perkataan.
6. Jumlah soalan sekitar 12 hingga 15 soalan.
"""

    return """
Tahap kesukaran: SEDERHANA.

Arahan tahap:
1. Gunakan standard SPM biasa.
2. Gabungkan soalan fakta langsung dan soalan kefahaman.
3. Gunakan kosa kata sederhana.
4. Panjang skrip sekitar 450 hingga 650 patah perkataan.
5. Jumlah soalan sekitar 10 hingga 12 soalan.
"""


def _build_marking_prompt(session: dict, answers: List[dict]) -> str:
    return f"""
Anda ialah pemeriksa SPM Bahasa Melayu untuk Ujian Mendengar.

Tugas:
Semak jawapan pelajar berdasarkan skema jawapan yang diberikan.
Berikan markah secara adil.
Untuk jawapan subjektif, terima jawapan yang membawa maksud yang sama walaupun ayat berbeza.

Data ujian:
{{
  "tema": {repr(session.get("tema", ""))},
  "difficulty": {repr(session.get("difficulty", "medium"))},
  "petikans": {repr(session.get("petikans", []))}
}}

Jawapan pelajar:
{repr(answers)}

Kembalikan JSON sahaja.
Jangan guna markdown.
Jangan beri penjelasan luar JSON.

Format JSON wajib:

{{
  "total_score": 0,
  "max_score": 20,
  "percentage": 0,
  "grade": "A/B/C/D/E/F",
  "question_feedbacks": [
    {{
      "question_id": "p1q1",
      "question_text": "<soalan>",
      "user_answer": "<jawapan pelajar>",
      "correct_answer": "<jawapan/skema>",
      "marks_awarded": 0,
      "max_marks": 2,
      "feedback": "<maklum balas ringkas dalam BM>"
    }}
  ],
  "overall_feedback": "<rumusan prestasi pelajar dalam BM>",
  "suggestions": [
    "<cadangan 1>",
    "<cadangan 2>",
    "<cadangan 3>"
  ]
}}
"""


# ─────────────────────────────────────────────────────────────────────────────
# AUDIO HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def write_wave_file(
    filename: str,
    pcm: bytes,
    channels: int = 1,
    rate: int = 24000,
    sample_width: int = 2,
):
    """
    Kept for compatibility in case other code imports this helper.
    Not used by Edge TTS generation.
    """
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)


def _clean_script_for_tts(script: str) -> str:
    blocked_phrases = [
        "jawab soalan",
        "baca soalan",
        "lihat soalan",
        "pilih jawapan",
        "soalan berikut",
        "skema jawapan",
        "jawapan yang betul",
        "murid dikehendaki",
        "pelajar dikehendaki",
        "bunyi hujan",
        "hujan",
        "muzik",
        "kesan bunyi",
        "suasana",
        "latar belakang",
        "background",
        "sound effect",
        "rain",
        "ambience",
        "ambient",
    ]

    lines = script.splitlines()
    clean_lines = []

    for line in lines:
        lower_line = line.lower().strip()

        if not lower_line:
            clean_lines.append(line)
            continue

        if any(phrase in lower_line for phrase in blocked_phrases):
            continue

        # Remove stage directions like [bunyi hujan], (muzik latar), etc.
        if lower_line.startswith("[") and lower_line.endswith("]"):
            continue

        if lower_line.startswith("(") and lower_line.endswith(")"):
            continue

        clean_lines.append(line)

    cleaned = "\n".join(clean_lines).strip()

    if not cleaned:
        return script.strip()

    return cleaned


def _detect_pcm_rate(mime_type: str) -> int:
    """
    Kept for compatibility in case other code imports this helper.
    Not used by Edge TTS generation.
    """
    mime_type = mime_type or ""

    if "rate=48000" in mime_type:
        return 48000

    if "rate=44100" in mime_type:
        return 44100

    if "rate=32000" in mime_type:
        return 32000

    if "rate=24000" in mime_type:
        return 24000

    if "rate=16000" in mime_type:
        return 16000

    return 24000


async def synthesize_listening_audio(script: str, session_id: str) -> str:
    """
    Converts generated listening script into spoken audio using Edge TTS.
    Saves as .mp3 and returns URL path.
    """
    clean_script = _clean_script_for_tts(script)

    print("\n========== AUDIO SCRIPT START ==========")
    print(clean_script[:3000])
    print("========== AUDIO SCRIPT END ==========\n")

    mp3_path = str(LISTENING_AUDIO_DIR / f"{session_id}.mp3")

    communicate = edge_tts.Communicate(
        text=clean_script,
        voice=TTS_VOICE,
        rate="-10%",
        pitch="-5Hz",
    )

    await communicate.save(mp3_path)

    return f"/audio/listening/{session_id}.mp3"


# ─────────────────────────────────────────────────────────────────────────────
# SESSION HELPER
# ─────────────────────────────────────────────────────────────────────────────

def get_valid_listening_session(session_id: str) -> dict | None:
    session = database.listening_sessions_col.find_one(
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
        database.listening_sessions_col.update_one(
            {"session_id": session_id},
            {"$set": {"status": "expired"}}
        )
        return None

    return session


# ─────────────────────────────────────────────────────────────────────────────
# SESSION GENERATION
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_questions(data: dict) -> dict:
    for petikan_index, petikan in enumerate(data.get("petikans", []), start=1):
        for question_index, q in enumerate(petikan.get("questions", []), start=1):
            if not q.get("question_id"):
                q["question_id"] = f"p{petikan_index}q{question_index}"

            if q.get("question_type") != "mcq":
                q["options"] = None

            try:
                q["marks"] = int(q.get("marks", 1))
            except Exception:
                q["marks"] = 1

            if not isinstance(q.get("answer_scheme"), list):
                q["answer_scheme"] = [str(q.get("answer_scheme", ""))]

    return data


def _hide_answer_scheme_for_frontend(data: dict) -> dict:
    safe_petikans = []

    for petikan in data.get("petikans", []):
        safe_questions = []

        for q in petikan.get("questions", []):
            safe_questions.append({
                "question_id": q.get("question_id"),
                "question_text": q.get("question_text"),
                "question_type": q.get("question_type"),
                "marks": q.get("marks"),
                "options": q.get("options"),
            })

        safe_petikans.append({
            "title": petikan.get("title"),
            "questions": safe_questions,
        })

    return {
        "tema": data.get("tema"),
        "difficulty": data.get("difficulty"),
        "audio_url": data.get("audio_url"),
        "petikans": safe_petikans,
    }


async def generate_listening_session(
    session_id: str,
    user_id: str,
    difficulty: str = "medium",
    mode: str = "quiz",
) -> dict:
    if database.listening_sessions_col is None:
        raise RuntimeError("MongoDB not initialized")

    if difficulty not in ["easy", "medium", "hard"]:
        difficulty = "medium"

    prompt = _LISTENING_PROMPT + "\n\n" + _difficulty_instruction(difficulty)

    data = await _ask_gemini(prompt, schema=LISTENING_SCHEMA)

    if not data:
        raise ValueError("Failed to generate listening test from Gemini")

    data = _normalize_questions(data)

    clean_script = _clean_script_for_tts(data["audio_script"])
    data["audio_script"] = clean_script
    data["difficulty"] = difficulty

    audio_url = await synthesize_listening_audio(
        script=clean_script,
        session_id=session_id,
    )

    data["audio_url"] = audio_url

    doc = {
        "session_id": session_id,
        "quiz_type": "mendengar",
        "user_id": user_id,
        "difficulty": difficulty,
        "tema": data["tema"],
        "audio_script": data["audio_script"],
        "audio_url": audio_url,
        "petikans": data["petikans"],
        "mode": mode,
        "status": "in_progress",
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=2),
    }

    database.listening_sessions_col.insert_one(doc)

    return _hide_answer_scheme_for_frontend(data)


# ─────────────────────────────────────────────────────────────────────────────
# MARKING
# ─────────────────────────────────────────────────────────────────────────────

async def score_listening_submission(
    session_id: str,
    user_id: str,
    answers: List[dict],
) -> dict:
    if database.listening_sessions_col is None:
        raise RuntimeError("MongoDB not initialized")

    if database.listening_results_col is None:
        raise RuntimeError("MongoDB not initialized")

    session = get_valid_listening_session(session_id)

    if not session:
        raise ValueError(
            f"Session '{session_id}' not found or has expired. "
            "Please start a new Paper 4 quiz."
        )

    if session.get("mode", "quiz") != "quiz":
        raise ValueError("This session is a latihan session and cannot be submitted as a quiz.")

    prompt = _build_marking_prompt(session, answers)

    result = await _ask_gemini(
        prompt,
        temperature=0.2,
        schema=MARKING_SCHEMA,
    )

    if not result:
        raise ValueError("Failed to mark listening answers from Gemini")

    result["session_id"] = session_id
    result["quiz_type"] = "mendengar"
    result["user_id"] = user_id
    result["saved_at"] = datetime.now(timezone.utc)

    database.listening_results_col.insert_one(result)

    database.listening_sessions_col.update_one(
        {"session_id": session_id},
        {"$set": {"status": "completed"}}
    )

    update_result(
        user_id=user_id,
        quiz_type="mendengar",
        raw_score=result["total_score"],
        max_score=result["max_score"],
    )

    return result

async def score_latihan_listening_submission(
    session_id: str,
    user_id: str,
    answers: List[dict],
) -> dict:
    """
    Score Paper 4 listening latihan answers only.

    This intentionally does NOT:
    - save to listening_results_col
    - call update_result(...)
    - affect dashboard marks
    """
    if database.listening_sessions_col is None:
        raise RuntimeError("MongoDB not initialized")

    session = get_valid_listening_session(session_id)

    if not session:
        raise ValueError(
            f"Session '{session_id}' not found or has expired. "
            "Please start a new Paper 4 latihan."
        )

    if session.get("mode", "quiz") != "latihan":
        raise ValueError("This session is a quiz session and cannot be submitted as latihan.")

    prompt = _build_marking_prompt(session, answers)

    result = await _ask_gemini(
        prompt,
        temperature=0.2,
        schema=MARKING_SCHEMA,
    )

    if not result:
        raise ValueError("Failed to mark listening latihan answers from Gemini")

    result["session_id"] = session_id
    result["quiz_type"] = "mendengar"
    result["user_id"] = user_id

    database.listening_sessions_col.update_one(
        {"session_id": session_id},
        {"$set": {"status": "completed"}}
    )

    return result