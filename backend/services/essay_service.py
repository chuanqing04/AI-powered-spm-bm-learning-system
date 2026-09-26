"""
Core logic for Paper 1 (Karangan) quiz types.
Uses Google Gemini via the google-genai SDK for question generation,
relevance checking, and feedback generation.
Uses essay_scorer.py (XLM-RoBERTa) for rubric-based karangan scoring.

Quiz types handled:
  - karangan_pendek  (150–200 words, 30 marks)
  - karangan_panjang (350–500 words, 70 marks)
"""
import uuid
from typing import List, Optional
import database
from datetime import datetime, timezone, timedelta
from schemas.models import (
    QuizType, QuizQuestion, QuizSubmitRequest, QuizSubmitResponse,
    QuestionFeedback, EssayRubric,
)
from machineLearning.essay_scorer import score_essay, SPM_RUBRIC, percentage_to_grade
from services.agentic_gemini import _ask_gemini, OutputSchema
from services.adaptive_engine import get_adaptive_difficulty
from services.user_results_memory import get_weak_areas, update_result


ESSAY_QUESTION_SCHEMA = OutputSchema(
    root_type=dict,
    required_keys=["question_id", "question_text", "question_type", "difficulty"]
)

RELEVANCE_SCHEMA = OutputSchema(
    root_type=dict,
    required_keys=["relevance_score", "relevance_reason", "is_off_topic"]
)

FEEDBACK_SCHEMA = OutputSchema(
    root_type=dict,
    required_keys=["feedback_bm", "suggestions"],
    custom_check=lambda d: (
        None if isinstance(d.get("suggestions"), list) and len(d["suggestions"]) == 3
        else "Must return exactly 3 suggestions"
    )
)


# ── Helper: Get session for resuming essay if available ───────────────────────
def get_valid_session(session_id: str):
    session = database.essay_sessions_col.find_one(
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
        database.essay_sessions_col.update_one(
            {"session_id": session_id},
            {"$set": {"status": "expired"}}
        )
        return None

    return session


# ─────────────────────────────────────────────────────────────────────────────
# QUESTION GENERATION PROMPTS (Paper 1)
# ─────────────────────────────────────────────────────────────────────────────

_PROMPTS: dict[str, str] = {

    "karangan_pendek": """
Anda adalah pemeriksa SPM Bahasa Melayu berpengalaman.
Jana SATU soalan Karangan A (Respon Terhad) berformat SPM sebenar untuk 150-200 patah perkataan.

LANGKAH 1 — Pilih secara rawak SATU format:
- BIASA
- SURAT RASMI
- E-MEL

═══════════════════════════════════════════════
FORMAT 1: BIASA
═══════════════════════════════════════════════
- Bina satu tajuk/tema yang sesuai
- Sertakan 2-4 isi pokok berbentuk poin ringkas sebagai panduan pelajar
- Akhiri dengan arahan: "Tulis karangan anda berdasarkan poin-poin di atas."

FORMAT question_text yang WAJIB diikuti (gunakan \n untuk baris baru):
<tajuk>\n- <isi 1>\n- <isi 2>\n- <isi 3>\n\nTulis karangan anda berdasarkan poin-poin di atas.

═══════════════════════════════════════════════
FORMAT 2: SURAT RASMI
═══════════════════════════════════════════════
- Penulis surat mestilah seorang awam / pengguna / pelajar / ibu bapa
- Penerima surat mestilah pihak berkuasa (Pengurus, Pengetua, Pengurus Besar, YDP Majlis Perbandaran, dll.)
- Surat mesti mengandungi:
  i)  Masalah / isu yang ingin diadukan (2-3 contoh spesifik)
  ii) Cadangan tindakan yang perlu diambil
- Arahan wajib: "Tulis surat itu selengkapnya."
- JANGAN nyatakan bilangan patah perkataan dalam question_text

FORMAT question_text yang WAJIB diikuti (gunakan \n untuk baris baru):
Sebagai seorang <peranan penulis>, tulis sepucuk surat kepada <penerima> untuk mengadukan masalah <isu> yang berlaku di <tempat> sehingga mengakibatkan <kesan 1> dan <kesan 2> serta cadangkan tindakan yang perlu diambil.\n\nTulis surat itu selengkapnya.

═══════════════════════════════════════════════
FORMAT 3: E-MEL
═══════════════════════════════════════════════
- E-mel mestilah antara dua individu yang dikenali (rakan, kenalan, saudara)
- Sertakan header e-mel dalam question_text
- Kandungan e-mel yang dijana mestilah E-mel 1 SAHAJA (soalan/permintaan)
- E-mel 1 mesti:
  i)  Ada konteks / latar belakang situasi
  ii) Ada soalan / permintaan utama kepada penerima
  iii) Akhiri dengan nama penghantar
- Arahan wajib selepas e-mel: "Sebagai <nama penerima>, tulis balasan e-mel anda selengkapnya."

FORMAT question_text yang WAJIB diikuti (gunakan \n untuk baris baru):
Daripada: <nama1@emel.com>\nKepada: <nama2@emel.com>\nSubjek: <tajuk>\n\n<kandungan e-mel — konteks + soalan/permintaan>\n\nYang benar,\n<nama penghantar>\n\nSebagai <nama penerima>, tulis balasan e-mel anda selengkapnya.

PENTING - JANGAN masukkan perkara berikut dalam question_text:
- Jangan nyatakan bilangan patah perkataan (contoh: "150-200 patah perkataan")
- Jangan nyatakan jenis, nama atau format karangan (contoh: "FORMAT: BIASA")
- Jangan nyatakan label langkah (contoh: "LANGKAH 1")
- Tag HTML seperti <br> atau <br/> — gunakan \n sahaja

Hanya berikan tajuk karangan dan arahan soalan sahaja.

Kembalikan JSON dengan format berikut SAHAJA:
{
  "question_id": "q1",
  "question_text": "<tajuk dan arahan penuh dalam Bahasa Melayu>",
  "question_type": "open_ended",
  "difficulty": "<kesukaran>",
  "options": null,
  "passage": null
}
""",

    "karangan_panjang": """
Anda adalah pemeriksa SPM Bahasa Melayu berpengalaman.
Jana SATU soalan Karangan B (Respon Terbuka) berformat SPM sebenar untuk 350-500 patah perkataan.
LANGKAH 1 — Pilih secara rawak SATU domain:
- Domain Peribadi
- Domain Awam
- Domain Pendidikan
- Domain Kerjaya

LANGKAH 2 — Pilih secara rawak SATU format penulisan:
- TIDAK BERFORMAT (karangan biasa)
- BERFORMAT: Rencana
- BERFORMAT: Laporan
- BERFORMAT: Syarahan / Pidato / Ceramah / Ucapan

LANGKAH 3 — Bina tajuk soalan menggunakan kata kunci popular SPM:
- Kebaikan / Kepentingan / Faedah / Manfaat / Kemaslahatan
- Langkah / Cara / Usaha / Kaedah / Inisiatif
- Peranan / Tugas / Tanggungjawab / Fungsi / Sumbangan

LANGKAH 4 — Tulis bantuan sumber (petikan) dalam format berikut:
- Tulis 2-4 ayat prosa berkaitan topik yang dipilih (BUKAN poin atau senarai)
- Petikan mesti berbentuk perenggan berterusan, seperti artikel akhbar atau laporan rasmi
- Akhiri dengan baris sumber: "Sumber: [nama organisasi / akhbar / laman web], [tahun]"
- Sumber boleh daripada organisasi Malaysia, akhbar tempatan, atau laman web / portal berita yang realistik

LANGKAH 5 — Gunakan istilah arahan yang betul mengikut format:
- Tidak Berformat → "Tulis sebuah karangan..."
- Rencana → "Tulis sebuah rencana selengkapnya..."
- Laporan → "Tulis laporan itu selengkapnya..."
- Syarahan/Pidato → "Sediakan teks syarahan/pidato anda selengkapnya..."
- Ceramah → "Sediakan teks ceramah anda selengkapnya..."
- Ucapan → "Sediakan teks ucapan anda selengkapnya..."

PENTING - JANGAN masukkan perkara berikut dalam question_text:
- Jangan nyatakan bilangan patah perkataan (contoh: "350-500 patah perkataan")
- Jangan nyatakan nama domain (contoh: "Domain Pendidikan")
- Jangan nyatakan label format (contoh: "BERFORMAT: Rencana")

Hanya berikan tajuk karangan dan arahan soalan sahaja.

FORMAT question_text yang WAJIB diikuti:
Gunakan aksara newline sebenar (\n) untuk baris baru, BUKAN tag HTML seperti <br> atau <br/>.
<petikan prosa 2-4 ayat>\nSumber: <nama organisasi>, <tahun>.\n\n<arahan soalan>

Kembalikan JSON dengan format berikut SAHAJA:
{
  "question_id": "q1",
  "question_text": "<tajuk, bantuan sumber, dan arahan penuh dalam Bahasa Melayu>",
  "question_type": "open_ended",
  "difficulty": "<kesukaran>",
  "options": null,
  "passage": null
}
""",
}


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE (Paper 1)
# ─────────────────────────────────────────────────────────────────────────────

async def _save_essay_session(session_id: str, quiz_type: str, questions: list, user_id: str, mode: str = "quiz"):
    """Save generated questions to MongoDB when /start is called."""
    if database.essay_sessions_col is None:
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
    database.essay_sessions_col.insert_one(doc)


async def _save_essay_result(response, user_id: str):
    """Save scoring result to MongoDB when /submit is called."""
    if database.essay_results_col is None:
        raise RuntimeError("MongoDB not initialized")

    doc = response.model_dump()
    doc["user_id"]    = user_id
    doc["saved_at"]   = datetime.now(timezone.utc)
    database.essay_results_col.insert_one(doc)


# ─────────────────────────────────────────────────────────────────────────────
# QUESTION GENERATION (Paper 1)
# ─────────────────────────────────────────────────────────────────────────────
DIFFICULTY_RULES = {
    "easy": {
        "topic": "isu harian remaja dan masyarakat sekolah (SPM context)",
        "style": "bahasa SPM asas tetapi masih formal dan sesuai peperiksaan",
        "complexity": "idea jelas, kurang lapisan hujah, fokus kepada satu sudut pandang",
        "cognitive_level": "mengingat + memahami + aplikasi asas",
        "question_design": "situasi mudah dengan rangsangan jelas, tidak terlalu abstrak"
    },

    "medium": {
        "topic": "isu semasa remaja, masyarakat dan negara",
        "style": "bahasa formal dengan idea pelbagai dan contoh sokongan",
        "complexity": "hujah berlapis dan ada pertimbangan sebab-akibat",
        "cognitive_level": "aplikasi + analisis",
        "question_design": "situasi SPM sebenar dengan sedikit elemen inferens"
    },

    "hard": {
        "topic": "isu global, sosial, ekonomi dan cabaran masa depan",
        "style": "bahasa akademik, analisis kritikal dan perspektif luas",
        "complexity": "hujah kompleks, evaluasi dan perbandingan idea",
        "cognitive_level": "analisis + evaluasi + sintesis",
        "question_design": "isu abstrak, multi-dimensi, memerlukan pemikiran kritikal tinggi"
    }
}


async def generate_questions_for_type(
    quiz_type: QuizType,
    session_id: str,
    user_id: str,
    requested_difficulty: Optional[str] = None,
    mode: str = "quiz"
) -> List[QuizQuestion]:
    """
    Call Gemini to generate a karangan question and store it under session_id.
    Both karangan_pendek and karangan_panjang return a single question object.
    """
    difficulty = requested_difficulty or get_adaptive_difficulty(user_id, quiz_type)

    adaptive_difficulty_map = {
        "low": "easy",
        "medium": "medium",
        "high": "hard",
    }

    difficulty = adaptive_difficulty_map.get(difficulty, difficulty)

    # Ensure valid difficulty
    if difficulty not in DIFFICULTY_RULES:
        difficulty = "medium"

    weak_areas = get_weak_areas(user_id)

    prompt = str(_PROMPTS[quiz_type]).strip()

    rule = DIFFICULTY_RULES[difficulty]

    prompt += f"""
    \n\nTahap kesukaran yang dikehendaki: **{difficulty}.**

    Panduan:
    - Topik: {rule['topic']}
    - Gaya penulisan: {rule['style']}
    - Tahap pemikiran: {rule['complexity']}
    - Tahap kognitif: {rule['cognitive_level']}
    - Struktur soalan: {rule['question_design']}
    """

    if weak_areas and quiz_type in ["karangan_pendek", "karangan_panjang"]:
        prompt += f"""
        KELEMAHAN PELAJAR: - {', '.join(weak_areas)}

        Pastikan soalan membantu pelajar memperbaiki kelemahan di atas tanpa menjadikan soalan tidak natural.
        """
    
    data = await _ask_gemini(prompt, schema=ESSAY_QUESTION_SCHEMA)    
    if not data:
        raise RuntimeError("Failed to generate essay question from Gemini")

    questions: List[QuizQuestion] = []

    # karangan_pendek / karangan_panjang — single JSON object
    questions.append(QuizQuestion(
        question_id   = data.get("question_id", str(uuid.uuid4())),
        question_text = data["question_text"],
        question_type = data.get("question_type", "open_ended"),
        difficulty    = difficulty,
        options       = data.get("options"),
        passage       = data.get("passage"),
    ))

    await _save_essay_session(session_id, quiz_type, questions, user_id=user_id, mode=mode)

    return questions


# ─────────────────────────────────────────────────────────────────────────────
# SCORING — router
# ─────────────────────────────────────────────────────────────────────────────

async def score_submission(req: QuizSubmitRequest) -> QuizSubmitResponse:
    """Look up the session's stored questions, then score the karangan."""
    session = get_valid_session(req.session_id)

    if not session:
        raise ValueError(
            f"Session '{req.session_id}' not found. "
            "Please call /api/essay/start first."
        )

    questions: List[QuizQuestion] = session["questions"]
    result = await _score_karangan(req, questions)

    database.essay_sessions_col.update_one(
        {"session_id": req.session_id},
        {"$set": {"status": "completed"}}
    )

    await _save_essay_result(result, user_id=req.user_id)

    update_result(
        user_id=req.user_id,
        quiz_type=req.quiz_type,
        raw_score=result.total_score,
        max_score=result.max_score
    )

    return result


# ─────────────────────────────────────────────────────────────────────────────
# RELEVANCE CHECK — topic alignment (feeds into content_score)
# ─────────────────────────────────────────────────────────────────────────────

async def _check_relevance(
    essay: str,
    question_text: str,
) -> tuple[float, str, bool]:
    """
    Ask Gemini whether the essay ideas match the question topic.
    Returns (relevance_score 0-5, reason str, is_off_topic bool).

    The score is then converted to relevance_ratio = score / 5 and passed
    directly into score_essay() -> score_content(), where it accounts for
    25% of the content mark.  This mirrors how SPM examiners deduct marks
    for "isi tidak menjawab soalan" within the content band itself.

    Scale:
      5 -- Fully on-topic; all ideas address the question directly
      4 -- Mostly on-topic; minor drift in one paragraph
      3 -- Partially on-topic; some relevant content but significant drift
      2 -- Mostly off-topic; only surface mention of the question topic
      1 -- Almost entirely off-topic; essay ignores the question
      0 -- Completely off-topic or blank
    """
    prompt = f"""
Anda adalah pemeriksa SPM Bahasa Melayu yang berpengalaman.
Nilai sama ada ISI karangan pelajar menjawab tajuk / soalan yang diberikan.

Tajuk / Soalan:
\"\"\"{question_text}\"\"\"

Karangan pelajar:
\"\"\"{essay}\"\"\"

Skala markah kesesuaian tajuk (0-5):
  5 - Sepenuhnya relevan; semua isi menjawab soalan secara langsung
  4 - Kebanyakannya relevan; terdapat sedikit penyelewengan dalam satu perenggan
  3 - Sebahagiannya relevan; ada isi yang relevan tetapi penyelewengan ketara
  2 - Kebanyakannya tidak relevan; hanya menyebut tajuk secara sambil lewa
  1 - Hampir langsung tidak menjawab soalan
  0 - Langsung tidak berkaitan atau karangan kosong

Kembalikan JSON dengan format berikut SAHAJA:
{{
  "relevance_score": <integer 0-5>,
  "relevance_reason": "<satu ayat penilaian dalam Bahasa Melayu>",
  "is_off_topic": <true jika skor 0 atau 1, false sebaliknya>
}}
"""
    data             = await _ask_gemini(prompt, temperature=0.1, schema=RELEVANCE_SCHEMA)

    if not isinstance(data, dict): # Gemini/API failed or returned invalid data
        print("Gemini relevance check failed:", data)
        # Fallback to neutral score (0.6 = 3/5) to avoid off-topic penalty
        # when relevance check fails — penalise only when we are certain        
        return (3.0, "Semakan kesesuaian tajuk gagal dijalankan.", False)
    
    relevance_score  = max(0, min(5, int(data.get("relevance_score", 3))))
    relevance_reason = data.get("relevance_reason", "Kesesuaian tajuk tidak dapat dinilai.")
    is_off_topic     = bool(data.get("is_off_topic", relevance_score <= 1))
    return float(relevance_score), relevance_reason, is_off_topic


# ─────────────────────────────────────────────────────────────────────────────
# SCORER — Paper 1 (Karangan)
# Uses essay_scorer.py (XLM-RoBERTa) for rubric scoring, then passes the
# per-trait justifications to Gemini to generate natural BM feedback.
# ─────────────────────────────────────────────────────────────────────────────

async def _score_karangan(
    req: QuizSubmitRequest,
    questions: List[QuizQuestion],
) -> QuizSubmitResponse:
    """
    Scoring flow:
      1. _check_relevance()       →  relevance_score /5, reason, is_off_topic
      2. essay_scorer.score_essay()  →  rubric marks for BOTH paper types
      3. Extract the block matching req.quiz_type  →  subtotal + reasons
      4. Send reasons to Gemini   →  natural BM feedback paragraph
    """
    essay         = req.answers[0].answer if req.answers else ""
    question_text = questions[0]["question_text"] if questions else "Karangan SPM"

    # ── Step 1: Relevance check (Gemini) ──────────────────────────────────────
    # Done BEFORE the scorer so relevance_ratio is ready to pass in.
    relevance_score, relevance_reason, is_off_topic = await _check_relevance(
        essay, question_text
    )
    relevance_ratio = relevance_score / 5.0   # convert 0-5 → 0.0-1.0

    # ── Step 2: Run XLM-RoBERTa scorer (scores both types in one call) ────────
    scorer_result = score_essay(essay, relevance_ratio=relevance_ratio)

    # ── Step 3: Pick the block for the requested quiz type ────────────────────
    # karangan_pendek  →  max 30   |   karangan_panjang  →  max 70
    paper_result = scorer_result[req.quiz_type]   # "karangan_pendek" or "karangan_panjang"

    content_score    = paper_result["content_score"]
    language_score   = paper_result["language_score"]
    grammar_score    = paper_result["grammar_score"]
    vocabulary_score = paper_result["vocabulary_score"]
    coherence_score  = paper_result["coherence_score"]
    subtotal         = paper_result["subtotal"]       # e.g. 24.5 / 30  or  58.0 / 70
    max_score        = paper_result["max_total"]      # 30 or 70
    reasons          = paper_result["reasons"]        # per-trait BM justifications
    subtotal_percentage = paper_result["percentage"]          # e.g. 82.8 for /70
    subtotal_grade      = percentage_to_grade(subtotal_percentage)  # A/B/C/D/E

    # ── Step 4: Ask Gemini to turn the trait reasons into fluent BM feedback ──
    relevance_pct = round(relevance_ratio * 100)
    off_topic_warning = (
        "\n\nAMARAN PENTING: Karangan pelajar didapati tidak menjawab tajuk yang "
        "diberikan. Nasihatkan pelajar supaya membaca dan memahami tajuk sebelum menulis."
        if is_off_topic else ""
    )

    reasons_block = "\n".join([
        f"- Isi kandungan (termasuk kesesuaian tajuk {relevance_pct}%): {reasons['content']}",
        f"- Penggunaan bahasa  : {reasons['language']}",
        f"- Tatabahasa         : {reasons['grammar']}",
        f"- Perbendaharaan kata: {reasons['vocabulary']}",
        f"- Kohesi & koherensi : {reasons['coherence']}",
    ])

    feedback_prompt = f"""
Anda adalah pemeriksa SPM Bahasa Melayu yang berpengalaman.
Karangan pelajar telah dinilai secara automatik. Berikut adalah penemuan penilaian:

Tajuk karangan: {question_text}

Markah isi kandungan (termasuk kesesuaian tajuk {relevance_pct}%): {content_score} / {SPM_RUBRIC[req.quiz_type]["traits"]["content_score"]["max"]}
Markah keseluruhan: {subtotal} / {max_score}
Gred: {subtotal_grade}
{off_topic_warning}

Penemuan per-trait:
{reasons_block}

Berdasarkan penemuan di atas, tulis maklum balas yang:
1. Menerangkan prestasi kesesuaian isi dengan tajuk secara jelas {"(dengan amaran tegas kerana isi lari tajuk)" if is_off_topic else ""}
2. Memuji kekuatan linguistik karangan (jika ada)
3. Menjelaskan kelemahan utama dengan jelas
4. Memberikan 3 cadangan penambahbaikan yang konkrit

Kembalikan JSON dengan format berikut SAHAJA:
{{
  "feedback_bm": "<maklum balas terperinci dalam Bahasa Melayu, sekurang-kurangnya 4 ayat>",
  "suggestions": ["<cadangan 1>", "<cadangan 2>", "<cadangan 3>"]
}}
"""
    feedback_data = await _ask_gemini(feedback_prompt, temperature=0.3, schema=FEEDBACK_SCHEMA)
    if not feedback_data:
        feedback_bm = reasons_block
        suggestions = []
    else:
        feedback_bm = feedback_data.get("feedback_bm", reasons_block)
        suggestions = feedback_data.get("suggestions", [])
    
    # ── Build response objects ─────────────────────────────────────────────────
    rubric = EssayRubric(
        content_score    = content_score,
        language_score   = language_score,
        grammar_score    = grammar_score,
        vocabulary_score = vocabulary_score,
        coherence_score  = coherence_score,
        total_score      = subtotal,
        max_score        = max_score,
        grade            = subtotal_grade,
    )

    feedback_item = QuestionFeedback(
        question_id   = req.answers[0].question_id,
        question_text = "Karangan",
        user_answer   = essay[:200] + "..." if len(essay) > 200 else essay,
        score         = round(subtotal / max_score, 4),
        feedback      = feedback_bm,
    )

    return QuizSubmitResponse(
        session_id         = req.session_id,
        quiz_type          = req.quiz_type,
        total_score        = subtotal,
        max_score          = max_score,
        percentage         = subtotal_percentage,
        grade              = subtotal_grade,
        question_feedbacks = [feedback_item],
        essay_rubric       = rubric,
        overall_feedback   = feedback_bm,
        suggestions        = suggestions,
    )


# ─────────────────────────────────────────────────────────────────────────────
# HISTORY
# ─────────────────────────────────────────────────────────────────────────────

# async def get_essay_history(user_id: str, limit: int) -> list:
#     """Placeholder — replace with PostgreSQL query in production."""
#     return []