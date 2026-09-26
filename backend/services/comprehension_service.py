"""
Core logic for Paper 2 (Tatabahasa & Pemahaman) quiz types.
Uses Google Gemini via the google-genai SDK for question generation and scoring.

Quiz types handled:
  - golongan_kata     (word class identification)
  - bina_ayat         (sentence construction)
  - jenis_ayat        (sentence type identification / transformation)
  - kesalahan_bahasa  (language error identification and correction)
  - pemahaman         (reading comprehension)
  - rumusan           (summary writing)
"""
import uuid
from typing import List, Union, Optional
import database
from datetime import datetime, timezone, timedelta
from schemas.models import (
    QuizType, QuizQuestion, QuizSubmitRequest, QuizSubmitResponse,
    PemahamanSubmitResponse, PemahamanQuestionFeedback, 
    RumusanSubmitResponse, RumusanIsiBreakdown, 
    QuestionFeedback,
)
from services.rubrics.comprehension_rubrics import get_comprehension_rubrics
from services.agentic_gemini import _ask_gemini, OutputSchema
from services.adaptive_engine import get_adaptive_difficulty
from services.user_results_memory import get_weak_areas, update_result


# --- golongan_kata / bina_ayat / jenis_ayat / kesalahan_bahasa ---------------
PAPER2_SCHEMA = OutputSchema(
    root_type=list,
    min_list_length=5,
    list_item_keys=["question_id", "question_text", "question_type", "difficulty"],
)

# --- pemahaman ----------------------------------------------------------------
PEMAHAMAN_SCHEMA = OutputSchema(
    root_type=dict,
    required_keys=["bahan_1", "bahan_2", "questions"],
    custom_check=lambda d: (
        None if isinstance(d.get("questions"), list) and len(d["questions"]) == 4
        else f"Expected exactly 4 questions, got {len(d.get('questions', []))}."
    ),
)

# --- rumusan -----------------------------------------------------------------
RUMUSAN_SCHEMA = OutputSchema(
    root_type=dict,
    required_keys=["question_id", "question_text", "bahan_1", "bahan_2", "bahan_3"],
)

# --- scoring -----------------------------------------------------------------
SCORING_SCHEMA = OutputSchema(
    root_type=dict,
    required_keys=["results", "summary"],
    custom_check=lambda d: (
        None if isinstance(d.get("results"), list) and len(d["results"]) > 0
        else "results must be a non-empty list."
    ),
)


# ── Helper: Get session for resuming quiz if available ────────────────────────
def get_valid_session(session_id: str):
    session = database.comprehension_sessions_col.find_one(
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
        database.comprehension_sessions_col.update_one(
            {"session_id": session_id},
            {"$set": {"status": "expired"}}
        )
        return None

    return session


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE (Paper 2)
# ─────────────────────────────────────────────────────────────────────────────

async def _save_comprehension_session(
    session_id: str,
    quiz_type: str,
    questions: list,
    user_id: str,
    mode: str = "quiz",
):
    """Save generated questions to MongoDB when /start is called."""
    if database.comprehension_sessions_col is None:
        raise RuntimeError("MongoDB not initialized")

    doc = {
        "session_id":  session_id,
        "quiz_type":   quiz_type,
        "questions":   [q.model_dump() for q in questions],
        "user_id":     user_id,
        "mode":        mode,
        "status":      "in_progress",           
        "created_at":  datetime.now(timezone.utc),
        "expires_at":  datetime.now(timezone.utc) + timedelta(hours=2),        
    }
    database.comprehension_sessions_col.insert_one(doc)


async def _save_comprehension_result(response, user_id: str):
    """Save scoring result to MongoDB when /submit is called."""
    if database.comprehension_results_col is None:
        raise RuntimeError("MongoDB not initialized")

    doc = response.model_dump()
    doc["user_id"]    = user_id
    doc["saved_at"]   = datetime.now(timezone.utc)
    database.comprehension_results_col.insert_one(doc)


# ─────────────────────────────────────────────────────────────────────────────
# QUESTION GENERATION PROMPTS (Paper 2)
# ─────────────────────────────────────────────────────────────────────────────

_PROMPTS: dict[str, str] = {

    "golongan_kata": """
Anda adalah pemeriksa SPM Bahasa Melayu.
Jana 5 soalan mengenal pasti golongan kata untuk pelajar tingkatan 5.
Setiap soalan: satu ayat dengan SATU perkataan dicetak ditebalkan menggunakan tanda *.
JANGAN masukkan arahan seperti "Kenal pasti golongan kata...", terus mulakan dengan ayat penuh soalan.
Perkataan itu boleh berada di awal, tengah atau akhir ayat.
Variasikan topik, panjang ayat, dan kesukaran soalan (low/medium/high).
Pilihan jawapan mestilah: Kata Nama, Kata Kerja, Kata Adjektif, Kata Tugas.
Pastikan setiap ayat dan perkataan yang ditebalkan berbeza antara soalan.
"question_type" MESTI sentiasa "factual"

Kembalikan JSON array dengan format berikut SAHAJA:
[
  {
    "question_id": "q1",
    "question_text": "<soalan>",
    "question_type": "factual",
    "difficulty": "<kesukaran>",
    "options": ["Kata Nama", "Kata Kerja", "Kata Adjektif", "Kata Tugas"],
    "passage": null
  }
]
Jana 5 soalan dengan ayat dan perkataan yang berbeza.
""",

    "bina_ayat": """
Anda adalah pemeriksa SPM Bahasa Melayu.
Jana 5 soalan bina ayat untuk pelajar tingkatan 5.
Setiap soalan: berikan SATU perkataan, pelajar membina ayat lengkap menggunakannya.
Variasikan topik, panjang ayat, dan kesukaran soalan (low/medium/high).
Panduan kesukaran hanya menentukan PILIHAN PERKATAAN sahaja.
JANGAN masukkan sebarang huraian, syarat, atau konteks tambahan dalam question_text.
Format question_text adalah tetap dan tidak boleh diubah.
Bina ayat yang lengkap dan gramatis menggunakan perkataan: *perkataan*.
"question_type" MESTI sentiasa "open_ended"

Kembalikan JSON array dengan format berikut SAHAJA:
[
  {
    "question_id": "q1",
    "question_text": "<soalan>",
    "question_type": "open_ended",
    "difficulty": "<kesukaran>",
    "options": null,
    "passage": null
  }
]
Jana 5 soalan dengan 5 perkataan yang berbeza.
""",

    "jenis_ayat": """
Anda adalah pemeriksa SPM Bahasa Melayu.
Jana 5 soalan jenis ayat untuk pelajar tingkatan 5.
Campurkan jenis soalan berikut:
    1. Kenal pasti jenis ayat (Penyata / Tanya / Perintah / Seruan)
    2. Tukar jenis ayat kepada bentuk lain
    3. Tukar ayat aktif kepada ayat pasif
    4. Tukar ayat cakap langsung kepada cakap pindah
    5. Lengkapkan ayat mengikut jenis
    6. Pilih ayat yang betul
    7. Kenal pasti fungsi ayat (contohnya: ayat suruhan, larangan, silaan, permintaan)
    8. Bina ayat berdasarkan jenis ayat
Pastikan soalan merangkumi pelbagai jenis daripada senarai di atas (sekurang-kurangnya 3 jenis berbeza)
Variasikan topik, panjang ayat, dan kesukaran soalan (low/medium/high).

Peraturan options:
Jika soalan jenis "kenal pasti" atau "pilih" → gunakan: ["Ayat Penyata", "Ayat Tanya", "Ayat Perintah", "Ayat Seruan"]
Jika soalan jenis lain (tukar, bina, lengkapkan, fungsi) → set: options: null
"question_type" MESTI sentiasa "factual" atau "open_ended" sahaja

Kembalikan JSON array dengan format berikut SAHAJA:
[
  {
    "question_id": "q1",
    "question_text": "<arahan soalan>: '<ayat>'",
    "question_type": "factual" atau "open_ended",
    "difficulty": "<kesukaran>",
    "options": ["Ayat Penyata", "Ayat Tanya", "Ayat Perintah", "Ayat Seruan"],
    "passage": null
  }
]
Jana 5 soalan dengan ayat yang berlainan.
""",

    "kesalahan_bahasa": """
Anda adalah pemeriksa SPM Bahasa Melayu.
Jana 5 ayat yang mengandungi kesalahan bahasa (ejaan / tatabahasa / penggunaan kata).
Setiap ayat mesti ada kesalahan yang boleh dikenal pasti secara objektif
Pelajar perlu kenal pasti dan betulkan kesalahan tersebut.
Variasikan topik, panjang ayat, dan kesukaran soalan (low/medium/high).
SEBELUM menjana jawapan, semak setiap ayat dan pastikan ia TIDAK betul.
Jika ayat betul, ubah sehingga ada kesalahan bahasa.

Kembalikan JSON array dengan format berikut SAHAJA:
[
  {
    "question_id": "q1",
    "question_text": "Kenal pasti kesalahan bahasa dan tulis semula ayat dengan betul: '<ayat dengan kesalahan>'",
    "question_type": "open_ended",
    "difficulty": "<kesukaran>",
    "options": null,
    "passage": null
  }
]
Jana 5 soalan dengan kesalahan bahasa yang berbeza.
""",

    "pemahaman": """
Anda adalah pemeriksa SPM Bahasa Melayu.
Jana DUA bahan rangsangan yang berkongsi SATU tema yang sama dan 4 soalan pemahaman.
Pilih tema yang sesuai untuk pelajar tingkatan 5.
Setiap bahan boleh berbentuk: petikan pendek (100-150 patah perkataan), pantun, sajak, atau cerita pendek.
Kedua-dua bahan MESTI berkongsi tema yang sama.

Format soalan (tepat 4 soalan):
  Q1 - Maksud rangkai kata: pilih SATU rangkai kata daripada mana-mana bahan, tanya maknanya [2 markah]
  Q2 - Soalan berdasarkan KEDUA-DUA bahan tentang tema (kesan / kebaikan / kepentingan / dll.) [3 markah]
  Q3 - Soalan KBAT (analisis / penilaian / sintesis) [4 markah]
  Q4 - Soalan KBAT (analisis / penilaian / sintesis) [4 markah]

Kembalikan JSON dengan format berikut SAHAJA:
{
  "bahan_1": "<teks bahan pertama>",
  "bahan_2": "<teks bahan kedua>",
  "questions": [
    {
      "question_id": "q1",
      "question_text": "Berikan maksud rangkai kata '<rangkai kata>' dalam <Bahan 1/Bahan 2>.",
      "question_type": "factual",
      "difficulty": "<kesukaran>",
      "marks": 2,
      "options": null
    },
    {
      "question_id": "q2",
      "question_text": "<soalan tentang tema berdasarkan kedua-dua bahan>",
      "question_type": "inferential",
      "difficulty": "<kesukaran>",
      "marks": 3,
      "options": null
    },
    {
      "question_id": "q3",
      "question_text": "<soalan KBAT pertama>",
      "question_type": "evaluative",
      "difficulty": "<kesukaran>",
      "marks": 4,
      "options": null
    },
    {
      "question_id": "q4",
      "question_text": "<soalan KBAT kedua>",
      "question_type": "evaluative",
      "difficulty": "<kesukaran>",
      "marks": 4,
      "options": null
    }
  ]
}
""",

    "rumusan": """
Anda adalah pemeriksa SPM Bahasa Melayu.
Jana tiga bahan rangsangan yang berkongsi SATU tema yang sama untuk soalan Rumusan SPM.

Tema hendaklah sesuai untuk pelajar tingkatan 5 (contoh: alam sekitar, teknologi,
kesihatan, perpaduan, pendidikan, budaya, ekonomi, dll.)

Bahan 1: Petikan rencana (200-300 patah perkataan, bahasa formal, berkait tema)
Bahan 2: Dialog antara dua orang (8-12 baris, bahasa santai/harian, berkait tema)
Bahan 3: Puisi ATAU pantun (berkait tema yang sama)
"question_type" MESTI sentiasa "open_ended"

Kembalikan JSON dengan format berikut SAHAJA:
{
  "tema": "<tema yang dipilih>",
  "question_id": "q1",
  "question_text": "Berdasarkan ketiga-tiga bahan di bawah, tulis sebuah rumusan dalam tiga perenggan (pengenalan, isi dan kesimpulan) antara 80 hingga 120 patah perkataan.",
  "question_type": "open_ended",
  "difficulty": "<kesukaran>",
  "options": null,
  "bahan_1": "<teks petikan rencana 200-300 patah perkataan>",
  "bahan_2": "<dialog antara dua orang, setiap baris bermula dengan nama penutur>",
  "bahan_3": "<puisi atau pantun 4-8 baris>",
  "passage": null
}
""",
}


# ─────────────────────────────────────────────────────────────────────────────
# QUESTION GENERATION (Paper 2)
# ─────────────────────────────────────────────────────────────────────────────
DIFFICULTY_RULES = {
    "easy": {
        "topic": "tatabahasa asas dalam konteks ayat SPM",
        "style": "ayat SPM mudah tetapi masih berkonsepkan konteks sebenar",
        "complexity": "aplikasi asas (LOTS), tetapi bukan definisi hafalan",
        "cognitive_level": "remember + understand + apply (low HOTS)",
        "question_design": "ayat pendek sederhana, 1 konsep sahaja, sedikit distraktor"
    },

    "medium": {
        "topic": "teks SPM dengan gabungan literal dan inferens",
        "style": "campuran pemahaman langsung dan tersirat",
        "complexity": "analisis asas (lower HOTS)",
        "cognitive_level": "apply + analyze (balanced HOTS)",
        "question_design": "ayat lebih panjang, ada konteks, ada unsur mengelirukan ringan"
    },

    "hard": {
        "topic": "teks kompleks, isu semasa dan abstrak",
        "style": "inferens mendalam dan penilaian kritikal",
        "complexity": "analisis dan evaluasi (HOTS tinggi)",
        "cognitive_level": "analyze + evaluate + create",
        "question_design": "teks panjang, multi-layer meaning, distractor kuat, SPM exam standard"
    }
}

async def generate_questions_for_type(
    quiz_type: QuizType,
    session_id: str,
    user_id: str,
    requested_difficulty: Optional[str] = None,
    mode: str = "quiz",
) -> List[QuizQuestion]:
    """
    Call Gemini to generate Paper 2 questions.
    """
    prompt = str(_PROMPTS[quiz_type]).strip()

    difficulty = requested_difficulty or get_adaptive_difficulty(user_id, quiz_type)

    adaptive_difficulty_map = {
        "low": "easy",
        "medium": "medium",
        "high": "hard",
    }

    difficulty = adaptive_difficulty_map.get(difficulty, difficulty)

    if difficulty not in DIFFICULTY_RULES:
        difficulty = "medium"

    rule = DIFFICULTY_RULES[difficulty]

    prompt += f"""
    Tahap kesukaran yang dikehendaki: **{difficulty}.**

    Panduan:
    - Topik: {rule['topic']}
    - Gaya penulisan: {rule['style']}
    - Tahap pemikiran: {rule['complexity']}
    - Tahap kognitif: {rule['cognitive_level']}
    - Struktur soalan: {rule['question_design']}
    """
    prompt += "\nPastikan SEMUA soalan yang dijana mematuhi tahap kesukaran ini secara konsisten."

    weak_areas = get_weak_areas(user_id)

    WEAK_AREA_PROMPTS = {
        "bina_ayat": "Pelajar lemah dalam membina ayat gramatis yang betul. Fokus pada struktur ayat yang jelas dan tepat.",
        "golongan_kata": "Pelajar lemah dalam mengenal pasti golongan kata. Pastikan soalan membantu pengenalan kata nama, kata kerja, dll.",
        "jenis_ayat": "Pelajar lemah dalam mengenal pasti jenis ayat. Fokus pada ayat penyata, tanya, perintah dan seruan.",
        "kesalahan_bahasa": "Pelajar lemah dalam membetulkan kesalahan bahasa. Tekankan aspek tatabahasa, imbuhan dan struktur ayat.",
        "pemahaman": "Pelajar lemah dalam soalan inferens dan pemahaman tersirat. Fokus pada pemikiran aras tinggi.",
        "rumusan": "Pelajar lemah dalam mengenal pasti isi penting dan idea utama teks."
    }

    APPLICABLE_WEAK_AREAS = {"bina_ayat", "golongan_kata", "jenis_ayat", "kesalahan_bahasa", "pemahaman", "rumusan"}

    if weak_areas and quiz_type in APPLICABLE_WEAK_AREAS:
        mapped_notes = [
            WEAK_AREA_PROMPTS[area]
            for area in weak_areas
            if area in WEAK_AREA_PROMPTS
        ]

        if mapped_notes:
            prompt += f"""
    NOTA PENYESUAIAN BERDASARKAN PRESTASI PELAJAR:
    {chr(10).join(f"- {note}" for note in mapped_notes)}

    Arahan:
    - Soalan mesti membantu meningkatkan kemahiran ini secara semula jadi
    - Jangan menjadikan soalan terlalu jelas atau tidak natural
    - Soalan mesti setara dengan format SPM sebenar, bukan latihan sekolah rendah (boleh mengelirukan jika tidak teliti)
    - Gunakan konteks sebenar, bukan ayat kanak-kanak
    """
        
    if quiz_type == "pemahaman":
        data = await _ask_gemini(prompt, schema=PEMAHAMAN_SCHEMA)
    elif quiz_type == "rumusan":
        data = await _ask_gemini(prompt, schema=RUMUSAN_SCHEMA)
    else:
        data = await _ask_gemini(prompt, schema=PAPER2_SCHEMA)

    if data is None:
        raise RuntimeError(f"Failed to generate questions for {quiz_type}")
 
    questions: List[QuizQuestion] = []

    if quiz_type == "pemahaman":
        bahan_1 = data.get("bahan_1", "")
        bahan_2 = data.get("bahan_2", "")
        combined_passage = (
            f"[BAHAN_1]\n{bahan_1}\n\n"
            f"[BAHAN_2]\n{bahan_2}"
        )
        for q in data.get("questions", []):
            if q.get("question_type") not in ["factual", "inferential", "evaluative", "open_ended"]:
                q["question_type"] = "factual"

            questions.append(QuizQuestion(
                question_id   = q.get("question_id", str(uuid.uuid4())),
                question_text = q["question_text"],
                question_type = q.get("question_type", "factual"),
                difficulty    = difficulty,
                options       = q.get("options"),
                passage       = combined_passage,
                marks         = q.get("marks"),
            ))

    elif quiz_type == "rumusan":
        # Combine all 3 bahan into the passage field so the frontend
        # can render them separately by splitting on the delimiter
        bahan_1 = data.get("bahan_1", "")
        bahan_2 = data.get("bahan_2", "")
        bahan_3 = data.get("bahan_3", "")
        combined_passage = (
            f"[BAHAN_1]\n{bahan_1}\n\n"
            f"[BAHAN_2]\n{bahan_2}\n\n"
            f"[BAHAN_3]\n{bahan_3}"
        )

        if data.get("question_type") not in ["factual", "inferential", "evaluative", "open_ended"]:
            data["question_type"] = "open_ended"

        questions.append(QuizQuestion(
            question_id   = data.get("question_id", str(uuid.uuid4())),
            question_text = data["question_text"],
            question_type = data.get("question_type", "open_ended"),
            difficulty    = difficulty,
            options       = None,
            passage       = combined_passage,
        ))

    else:
        # golongan_kata / bina_ayat / jenis_ayat / kesalahan_bahasa
        # Gemini returns a JSON array
        for q in data:
            if q.get("question_type") not in ["factual", "inferential", "evaluative", "open_ended"]:
                q["question_type"] = "factual"

            questions.append(QuizQuestion(
                question_id   = q.get("question_id", str(uuid.uuid4())),
                question_text = q["question_text"],
                question_type = q.get("question_type", "open_ended"),
                difficulty    = difficulty,
                options       = q.get("options"),
                passage       = q.get("passage"),
            ))

    await _save_comprehension_session(
        session_id,
        quiz_type,
        questions,
        user_id=user_id,
        mode=mode,
    )

    return questions


# ─────────────────────────────────────────────────────────────────────────────
# SCORING — router
# ─────────────────────────────────────────────────────────────────────────────

async def score_submission(req) -> Union[QuizSubmitResponse, PemahamanSubmitResponse, RumusanSubmitResponse]:
    """
    Score real Paper 2 quiz answers.

    This DOES:
    - save to comprehension_results_col
    - call update_result(...)
    - affect dashboard marks
    """
    session = get_valid_session(req.session_id)

    if not session:
        raise ValueError(
            f"Session '{req.session_id}' not found. "
            "Please call /api/comprehension/start first."
        )

    if session.get("mode", "quiz") != "quiz":
        raise ValueError("This session is a latihan session and cannot be submitted as a quiz.")

    questions: List[QuizQuestion] = session["questions"]

    if req.quiz_type == "pemahaman":
        result = await _score_pemahaman(req, questions)
    elif req.quiz_type == "rumusan":
        result = await _score_rumusan(req, questions)
    else:
        result = await _score_paper2(req, questions)

    await _save_comprehension_result(result, user_id=req.user_id)

    update_result(
        user_id=req.user_id,
        quiz_type=req.quiz_type,
        raw_score=result.total_score,
        max_score=result.max_score,
    )

    database.comprehension_sessions_col.update_one(
        {"session_id": req.session_id},
        {"$set": {"status": "completed"}}
    )

    return result


async def score_latihan_submission(req) -> Union[QuizSubmitResponse, PemahamanSubmitResponse, RumusanSubmitResponse]:
    """
    Score Paper 2 latihan answers only.

    This intentionally does NOT:
    - save to comprehension_results_col
    - call update_result(...)
    - affect dashboard marks
    """
    session = get_valid_session(req.session_id)

    if not session:
        raise ValueError(
            f"Session '{req.session_id}' not found. "
            "Please call /api/comprehension/start first."
        )

    if session.get("mode", "quiz") != "latihan":
        raise ValueError("This session is a quiz session and cannot be submitted as latihan.")

    questions: List[QuizQuestion] = session["questions"]

    if req.quiz_type == "pemahaman":
        result = await _score_pemahaman(req, questions)
    elif req.quiz_type == "rumusan":
        result = await _score_rumusan(req, questions)
    else:
        result = await _score_paper2(req, questions)

    database.comprehension_sessions_col.update_one(
        {"session_id": req.session_id},
        {"$set": {"status": "completed"}}
    )

    return result

# ─────────────────────────────────────────────────────────────────────────────
# SCORER — Paper 2
# All five question types are scored via Gemini with full question context
# ─────────────────────────────────────────────────────────────────────────────

async def _score_paper2(
    req: QuizSubmitRequest,
    questions: List[QuizQuestion],
) -> QuizSubmitResponse:
    """Score Paper 2 answers via Gemini, with full question context."""

    # Build a paired question + answer block so Gemini can evaluate correctly
    qa_pairs = []
    for i, ans in enumerate(req.answers):
        # Match answer to its question by question_id, fallback to index
        question = next(
            (q for q in questions if q["question_id"] == ans.question_id),
            questions[i] if i < len(questions) else None,
        )
        q_text = question["question_text"] if question else f"Soalan {i+1}"
        # Include passage for pemahaman questions
        passage_text = (
            f"\nPetikan: {question['passage']}" if question and question['passage'] else ""
        )
        qa_pairs.append(
            f"Soalan {i+1}: {q_text}{passage_text}\n"
            f"Jawapan pelajar: {ans.answer}"
        )

    qa_block = "\n\n".join(qa_pairs)

    # Falls back to "medium" if questions list is empty.
    first_difficulty = questions[0].get("difficulty", "medium") if questions else "medium"
    rubric = get_comprehension_rubrics(quiz_type=req.quiz_type, difficulty=first_difficulty)

    # Type-specific instructions help Gemini apply the correct marking criteria
    type_instructions = {
        "golongan_kata":    "Semak sama ada golongan kata yang dipilih adalah betul.",
        "bina_ayat":        "Nilai ayat yang dibina: tatabahasa, makna dan kesesuaian perkataan.",
        "jenis_ayat":       "Semak sama ada jenis ayat atau penukaran ayat adalah tepat.",
        "kesalahan_bahasa": "Semak sama ada kesalahan bahasa dikenal pasti dan dibetulkan dengan betul.",
    }

    prompt = f"""
Anda adalah pemeriksa SPM Bahasa Melayu.
{type_instructions.get(req.quiz_type, '')}

Skema Pemarkahan SPM (markah maksimum: {rubric.max_score}):
{rubric.scoring_guide}

Berikut adalah soalan dan jawapan pelajar:

{qa_block}

Kembalikan JSON dengan format berikut SAHAJA:
{{
  "results": [
    {{
      "question_id": "<q1, q2 ...>",
      "is_correct": <true|false>,
      "score": <0.0 hingga 1.0>,
      "correct_answer": "<jawapan betul dalam Bahasa Melayu>",
      "feedback": "<maklum balas ringkas dalam Bahasa Melayu>"
    }}
  ],
  "summary": {{
    "overall_feedback": "<ulasan keseluruhan dalam Bahasa Melayu>",
    "suggestions": ["<tip 1>", "<tip 2>", "<tip 3>"]
  }}
}}
Pastikan "results" mengandungi tepat {len(req.answers)} objek mengikut urutan jawapan.
"""

    data = await _ask_gemini(prompt, temperature=0.2, schema=SCORING_SCHEMA)
    if data is None:
        raise RuntimeError(f"Scoring failed for quiz_type='{req.quiz_type}'. Check logs.")

    results  = data.get("results", [])
    summary  = data.get("summary", {})

    feedbacks   = []
    total_score = 0.0

    for i, ans in enumerate(req.answers):
        res   = results[i] if i < len(results) else {}
        score = float(res.get("score", 0))
        total_score += score
        feedbacks.append(QuestionFeedback(
            question_id    = ans.question_id,
            question_text  = f"Soalan {i + 1}",
            user_answer    = ans.answer,
            correct_answer = res.get("correct_answer"),
            is_correct     = res.get("is_correct"),
            score          = score,
            feedback       = res.get("feedback", ""),
        ))

    max_score  = len(req.answers)
    percentage = round((total_score / max_score) * 100, 1) if max_score > 0 else 0
    grade_map  = [(90, "A"), (75, "B"), (60, "C"), (45, "D")]
    grade      = next((g for t, g in grade_map if percentage >= t), "E")

    return QuizSubmitResponse(
        session_id         = req.session_id,
        quiz_type          = req.quiz_type,
        total_score        = round(total_score, 2),
        max_score          = max_score,
        percentage         = percentage,
        grade              = grade,
        question_feedbacks = feedbacks,
        essay_rubric       = None,
        overall_feedback   = summary.get("overall_feedback", ""),
        suggestions        = summary.get("suggestions", []),
    )

async def _score_pemahaman(
    req: QuizSubmitRequest,
    questions: List[QuizQuestion],
) -> PemahamanSubmitResponse:
    """
    Scores pemahaman using SPM mark scheme:
      Q1 — 2m  (1m makna + 1m bahasa)
      Q2 — 3m  (1m Bahan 1 + 1m Bahan 2 + 1m bahasa)
      Q3 — 4m  (3m answer + 1m bahasa)
      Q4 — 4m  (3m answer + 1m bahasa)
    """
    passage = questions[0]["passage"] if questions else ""

    qa_pairs = []
    for i, ans in enumerate(req.answers):
        question = next(
            (q for q in questions if q["question_id"] == ans.question_id),
            questions[i] if i < len(questions) else None,
        )
        q_text   = question["question_text"] if question else f"Soalan {i+1}"
        max_m    = question["marks"] if question and question["marks"] else 0
        qa_pairs.append(
            f"Soalan {i+1} [{max_m} markah]: {q_text}\n"
            f"Jawapan pelajar: {ans.answer}"
        )

    qa_block = "\n\n".join(qa_pairs)

    rubric = get_comprehension_rubrics(quiz_type="pemahaman")   # always "standard"

    prompt = f"""
Anda adalah pemeriksa SPM Bahasa Melayu berpengalaman.
Nilai jawapan pemahaman pelajar mengikut skema pemarkahan SPM berikut:

Bahan rangsangan:
{passage}

Soalan dan jawapan pelajar:
{qa_block}

Skema Pemarkahan (markah maksimum: {rubric.max_score}):
{rubric.scoring_guide}

Kembalikan JSON dengan format berikut SAHAJA:
{{
  "results": [
    {{
      "question_id": "q1",
      "marks_awarded": <0.0 hingga 2.0>,
      "max_marks": 2,
      "breakdown": {{"makna": <0 atau 1>, "bahasa": <0 atau 1>}},
      "feedback": "<maklum balas dalam Bahasa Melayu>"
    }},
    {{
      "question_id": "q2",
      "marks_awarded": <0.0 hingga 3.0>,
      "max_marks": 3,
      "breakdown": {{"bahan_1": <0 atau 1>, "bahan_2": <0 atau 1>, "bahasa": <0 atau 1>}},
      "feedback": "<maklum balas dalam Bahasa Melayu>"
    }},
    {{
      "question_id": "q3",
      "marks_awarded": <0.0 hingga 4.0>,
      "max_marks": 4,
      "breakdown": {{"isi": <0 hingga 3>, "bahasa": <0 atau 1>}},
      "feedback": "<maklum balas dalam Bahasa Melayu>"
    }},
    {{
      "question_id": "q4",
      "marks_awarded": <0.0 hingga 4.0>,
      "max_marks": 4,
      "breakdown": {{"isi": <0 hingga 3>, "bahasa": <0 atau 1>}},
      "feedback": "<maklum balas dalam Bahasa Melayu>"
    }}
  ],
  "summary": {{
    "overall_feedback": "<ulasan keseluruhan dalam Bahasa Melayu>",
    "suggestions": ["<tip 1>", "<tip 2>", "<tip 3>"]
  }}
}}
"""
    data = await _ask_gemini(prompt, temperature=0.2, schema=SCORING_SCHEMA)
 
    if data is None:
        raise RuntimeError("Pemahaman scoring failed. Check logs.")

    results = data.get("results", [])
    summary = data.get("summary", {})

    feedbacks   = []
    total_score = 0.0

    for i, ans in enumerate(req.answers):
        res          = results[i] if i < len(results) else {}
        marks        = float(res.get("marks_awarded", 0))
        total_score += marks
        feedbacks.append(PemahamanQuestionFeedback(
            question_id   = ans.question_id,
            question_text = f"Soalan {i + 1}",
            user_answer   = ans.answer,
            marks_awarded = marks,
            max_marks     = res.get("max_marks", 0),
            breakdown     = res.get("breakdown", {}),
            feedback      = res.get("feedback", ""),
        ))

    max_score  = 13
    percentage = round((total_score / max_score) * 100, 1)
    grade_map  = [(90, "A"), (75, "B"), (60, "C"), (45, "D")]
    grade      = next((g for t, g in grade_map if percentage >= t), "E")

    return PemahamanSubmitResponse(
        session_id         = req.session_id,
        quiz_type          = req.quiz_type,
        total_score        = round(total_score, 2),
        max_score          = max_score,
        percentage         = percentage,
        grade              = grade,
        question_feedbacks = feedbacks,
        overall_feedback   = summary.get("overall_feedback", ""),
        suggestions        = summary.get("suggestions", []),
    )


async def _score_rumusan(
    req: QuizSubmitRequest,
    questions: List[QuizQuestion],
) -> RumusanSubmitResponse:
    """
    Scores rumusan using SPM mark scheme:
      Isi   — 20 markah (max 8 isi × 2m, min 1 isi dari setiap bahan)
      Bahasa — 10 markah
      Total  — 30 markah, periksa setakat 120 patah perkataan sahaja
    """
    rumusan_text = req.answers[0].answer if req.answers else ""
    passage      = questions[0]["passage"]  if questions  else ""

    rubric = get_comprehension_rubrics(quiz_type="rumusan")     # always "standard"

    prompt = f"""
Anda adalah pemeriksa SPM Bahasa Melayu berpengalaman.
Nilai rumusan pelajar mengikut skema pemarkahan SPM berikut.

Tiga bahan rangsangan:
{passage}

Rumusan pelajar:
\"\"\"{rumusan_text}\"\"\"

Skema Pemarkahan (markah maksimum: {rubric.max_score}):
{rubric.scoring_guide}

Kembalikan JSON dengan format berikut SAHAJA:
{{
  "word_count": <integer>,
  "isi_list": [
    {{
      "isi_number": <1 hingga 8>,
      "isi_text": "<isi yang dikenal pasti dari rumusan pelajar>",
      "bahan_sumber": "<Bahan 1 | Bahan 2 | Bahan 3>",
      "marks_awarded": <0 atau 2>,
      "reason": "<sebab markah penuh atau tiada markah>"
    }}
  ],
  "isi_score": <jumlah markah isi, maksimum 20>,
  "bahan_coverage": {{
    "Bahan 1": <bilangan isi dari Bahan 1>,
    "Bahan 2": <bilangan isi dari Bahan 2>,
    "Bahan 3": <bilangan isi dari Bahan 3>
  }},
  "bahasa_score": <markah bahasa 0-10>,
  "bahasa_feedback": "<ulasan bahasa dalam Bahasa Melayu>",
  "overall_feedback": "<ulasan keseluruhan dalam Bahasa Melayu>",
  "suggestions": ["<cadangan 1>", "<cadangan 2>", "<cadangan 3>"]
}}
"""
    rumusan_scoring_schema = OutputSchema(
        root_type=dict,
        required_keys=["isi_list", "isi_score", "bahasa_score", "overall_feedback"],
    )
 
    data = await _ask_gemini(prompt, temperature=0.2, schema=rumusan_scoring_schema)
 
    if data is None:
        raise RuntimeError("Rumusan scoring failed. Check logs.")

    isi_raw   = data.get("isi_list", [])
    isi_list  = [
        RumusanIsiBreakdown(
            isi_number    = item.get("isi_number", i + 1),
            isi_text      = item.get("isi_text", ""),
            bahan_sumber  = item.get("bahan_sumber", ""),
            marks_awarded = float(item.get("marks_awarded", 0)),
            reason        = item.get("reason", ""),
        )
        for i, item in enumerate(isi_raw)
    ]

    isi_score    = float(data.get("isi_score", 0))
    bahasa_score = float(data.get("bahasa_score", 0))
    total_score  = isi_score + bahasa_score
    percentage   = round((total_score / 30) * 100, 1)
    grade_map    = [(90, "A"), (75, "B"), (60, "C"), (45, "D")]
    grade        = next((g for t, g in grade_map if percentage >= t), "E")

    return RumusanSubmitResponse(
        session_id       = req.session_id,
        quiz_type        = req.quiz_type,
        isi_list         = isi_list,
        isi_score        = isi_score,
        isi_count        = len(isi_list),
        bahan_coverage   = data.get("bahan_coverage", {}),
        bahasa_score     = bahasa_score,
        bahasa_feedback  = data.get("bahasa_feedback", ""),
        total_score      = round(total_score, 2),
        max_score        = 30,
        percentage       = percentage,
        grade            = grade,
        word_count       = data.get("word_count", 0),
        overall_feedback = data.get("overall_feedback", ""),
        suggestions      = data.get("suggestions", []),
    )
