"""
All Pydantic request/response models.
"""
from fastapi import UploadFile
from pydantic import BaseModel
from typing import Optional, List, Literal
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
# SHARED
# ─────────────────────────────────────────────────────────────────────────────

class BaseResponse(BaseModel):
    success: bool = True
    message: str = "OK"


# ─────────────────────────────────────────────────────────────────────────────
# QUIZ TYPES
# Maps to QuizPage.tsx cards:
#   Paper 1: karangan_pendek | karangan_panjang
#   Paper 2: golongan_kata | bina_ayat | jenis_ayat | kesalahan_bahasa | pemahaman | rumusan
#   Paper 3: lisan
#   Paper 4: mendengar
# ─────────────────────────────────────────────────────────────────────────────

QuizType = Literal[
    # Paper 1
    "karangan_pendek",
    "karangan_panjang",
    # Paper 2
    "golongan_kata",
    "bina_ayat",
    "jenis_ayat",
    "kesalahan_bahasa",
    "pemahaman",
    "rumusan",
    # Paper 3
    "lisan",
    # Paper 4
    "mendengar"
]


PaperType = Literal["paper1", "paper2", "paper3", "paper4"]


# ── Quiz Session (Start) ──────────────────────────────────────────────────────

class QuizStartRequest(BaseModel):
    quiz_type: QuizType
    user_id: str
    difficulty: Optional[Literal["easy", "medium", "hard"]] = None
    mode: Literal["quiz", "latihan"] = "quiz"

class QuizQuestion(BaseModel):
    question_id: str
    question_text: str
    question_type: Literal["factual", "inferential", "evaluative", "open_ended"]
    difficulty: Literal["easy", "medium", "hard", "low", "high"]
    # For golongan_kata, jenis_ayat, kesalahan_bahasa
    options: Optional[List[str]] = None
    # Context passage for pemahaman - 2 bahan combined, for rumusan - 3 bahan combined
    passage: Optional[str] = None
    marks: Optional[int] = None

class QuizStartResponse(BaseModel):
    session_id: str
    quiz_type: QuizType
    paper: PaperType
    title: str                    # e.g. "Karangan Pendek"
    description: str              # e.g. "150–200 patah perkataan • 30 markah"
    instructions: str
    questions: List[QuizQuestion]
    time_limit_minutes: Optional[int] = None


# ── Quiz Submission ───────────────────────────────────────────────────────────

class QuizAnswer(BaseModel):
    question_id: str
    answer: str                   # essay text OR selected option OR constructed sentence

class QuizSubmitRequest(BaseModel):
    session_id: str
    user_id: str
    quiz_type: QuizType
    answers: List[QuizAnswer]

class QuizRetryRequest(BaseModel):
    session_id: str              # REQUIRED: the session you want to retry
    user_id: str

# Per-question feedback
class QuestionFeedback(BaseModel):
    question_id: str
    question_text: str
    user_answer: str
    correct_answer: Optional[str] = None
    is_correct: Optional[bool] = None
    score: float                  # 0.0 – 1.0 for MCQ; rubric score for essays
    feedback: str                 # AI-generated explanation in BM

# Essay-specific rubric breakdown (Paper 1)
class EssayRubric(BaseModel):
    content_score: float          # isi
    language_score: float         # bahasa
    grammar_score: float          # tatabahasa
    vocabulary_score: float
    coherence_score: float
    total_score: float
    max_score: int                # 30 for pendek, 70 for panjang
    grade: Literal["A", "B", "C", "D", "E", "F"]

class QuizSubmitResponse(BaseModel):
    session_id: str
    quiz_type: QuizType
    total_score: float
    max_score: int
    percentage: float
    grade: Optional[str] = None
    time_taken_seconds: Optional[int] = None
    question_feedbacks: List[QuestionFeedback]
    # Only present for karangan
    essay_rubric: Optional[EssayRubric] = None
    overall_feedback: str         # Summary feedback paragraph in BM
    suggestions: List[str]        # 3 actionable improvement tips


# ── Dedicated Response Models for Pemahaman and Rumusan ───────────────────────────────────────────────────────────
# Pemahaman-specific per-question feedback (marks > 1.0)
class PemahamanQuestionFeedback(BaseModel):
    question_id: str
    question_text: str
    user_answer: str
    marks_awarded: float          # e.g. 1.5 / 2, 2 / 3, 3 / 4
    max_marks: int                # 2, 3, or 4
    breakdown: dict               # e.g. {"makna": 1, "bahasa": 1} for Q1
    feedback: str                 # AI explanation in BM

class PemahamanSubmitResponse(BaseModel):
    session_id: str
    quiz_type: QuizType
    total_score: float            # out of 13
    max_score: int                # 13
    percentage: float
    grade: Optional[str] = None
    question_feedbacks: List[PemahamanQuestionFeedback]
    overall_feedback: str
    suggestions: List[str]


# Rumusan-specific response
class RumusanIsiBreakdown(BaseModel):
    isi_number: int               # 1–8
    isi_text: str                 # the point extracted from student's rumusan
    bahan_sumber: str             # "Bahan 1" | "Bahan 2" | "Bahan 3"
    marks_awarded: float          # 0 or 2
    reason: str                   # why full/no marks

class RumusanSubmitResponse(BaseModel):
    session_id: str
    quiz_type: QuizType
    # Isi breakdown
    isi_list: List[RumusanIsiBreakdown]
    isi_score: float              # out of 20 (max 8 isi × 2m)
    isi_count: int                # how many valid isi found
    bahan_coverage: dict          # e.g. {"Bahan 1": 2, "Bahan 2": 3, "Bahan 3": 1}
    # Bahasa
    bahasa_score: float           # out of 10
    bahasa_feedback: str
    # Totals
    total_score: float            # out of 30
    max_score: int                # 30
    percentage: float
    grade: Optional[str] = None
    word_count: int               # counted up to 120 words
    overall_feedback: str
    suggestions: List[str]


# ─────────────────────────────────────────────────────────────────────────────
# SPEAKING — SESSION START  (Paper 3 — Ujian Lisan)
# Frontend sends only task_type + user_id.
# Gemini generates stimulus_text and all questions on the backend.
# ─────────────────────────────────────────────────────────────────────────────

class LisanQuestion(BaseModel):
    question_id:       str
    question_text:     str

class SpeakingStartRequest(BaseModel):
    task_type: QuizType           # must be "lisan"
    user_id: str
    difficulty: Optional[Literal["easy", "medium", "hard"]] = None
    mode: Literal["quiz", "latihan"] = "quiz"

class SpeakingStartResponse(BaseModel):
    session_id:         str
    task_type:          QuizType
    paper:              PaperType
    title:              str                    # "Ujian Lisan"
    description:        str
    instructions:       str                    # shown to student before recording
    time_limit_minutes: int
    scored_traits:      List[str]              # all 4 traits for lisan
    tema:               str                    # theme Gemini chose
    stimulus_text:      str                    # bahan rangsangan petikan
    soalan_rangsangan:  List[LisanQuestion]    # 2 questions based on petikan
    soalan_kbat:        List[LisanQuestion]    # 2 KBAT questions


# ─────────────────────────────────────────────────────────────────────────────
# SPEAKING — CLIP-LEVEL TRAIT RESULTS
# ─────────────────────────────────────────────────────────────────────────────

class GrammarVocabResult(BaseModel):
    score:  float                             # 0.0–1.0
    reason: str

class PronunciationResult(BaseModel):
    score:         float                      # 0.0–1.0
    reason:        str
    metrics: Optional[dict] = {}

class FluencyResult(BaseModel):
    score:   float                            # 0.0–1.0
    reason:  str
    metrics: Optional[dict] = {}              # wpm, pause_count, pause_ratio, etc.

class IdeasResult(BaseModel):
    score:         float                      # 0.0–1.0
    reason:        str
    question_id:   str
    question_text: str
    category:      str                        # "soalan_rangsangan" | "soalan_kbat"


# ─────────────────────────────────────────────────────────────────────────────
# SPEAKING — PER-CLIP RESULT
# ─────────────────────────────────────────────────────────────────────────────

class WerResult(BaseModel):
    strict:       float
    spoken_only:  float
    completeness: float

class ClipResult(BaseModel):
    clip_id:          str                     # "bacaan" | "r1" | "r2" | "k1" | "k2"
    transcription:    str
    no_speech:        bool                    # True when gate fired (silence/noise)
    no_speech_reason: Optional[str] = None    # Why gate fired, "" otherwise

    # Nested dicts instead of flat score + reason fields
    grammar_vocabulary: GrammarVocabResult
    pronunciation:      PronunciationResult
    fluency:            FluencyResult

    # None for bacaan clip (reading task — no ideas scored)
    ideas: Optional[IdeasResult] = None

    # Eval mode only (For bacaan clip only)
    wer: Optional[WerResult] = None


# ─────────────────────────────────────────────────────────────────────────────
# SPEAKING — PER-CLIP BREAKDOWN ROWS
# Used inside the aggregated trait blocks so the frontend can render a per-clip table alongside the overall average.
# ─────────────────────────────────────────────────────────────────────────────

class GrammarPerClip(BaseModel):
    clip_id: str
    score:   float
    reason:  str

class PronunciationPerClip(BaseModel):
    clip_id:       str
    score:         float
    reason:        str
    metrics: Optional[dict] = None

class FluencyPerClip(BaseModel):
    clip_id: str
    score:   float
    reason:  str
    metrics: Optional[dict] = None

class IdeasPerQuestion(BaseModel):
    clip_id:       str
    question_id:   str
    question_text: str
    category:      str                        # "soalan_rangsangan" | "soalan_kbat"
    score:         float
    reason:        str


# ─────────────────────────────────────────────────────────────────────────────
# SPEAKING — AGGREGATED TRAIT BLOCKS
# Each block carries the overall average + per_clip breakdown.
# ─────────────────────────────────────────────────────────────────────────────

class AggregatedGrammar(BaseModel):
    score:    float
    reason:   str
    per_clip: List[GrammarPerClip]

class AggregatedPronunciation(BaseModel):
    score:    float
    reason:   str
    per_clip: List[PronunciationPerClip]

class AggregatedFluency(BaseModel):
    score:    float
    reason:   str
    per_clip: List[FluencyPerClip]

class AggregatedIdeas(BaseModel):
    score:        float
    reason:       str
    per_question: List[IdeasPerQuestion]


# ─────────────────────────────────────────────────────────────────────────────
# SPEAKING — SUBMIT RESPONSE
# ─────────────────────────────────────────────────────────────────────────────

class SpeakingSubmitResponse(BaseModel):
    session_id: str
    task_type:  QuizType

    # 5 per-clip results (ordered: bacaan, r1, r2, k1, k2)
    clips: List[ClipResult]

    # Nested aggregated blocks
    grammar_vocabulary: AggregatedGrammar
    pronunciation:      AggregatedPronunciation
    fluency:            AggregatedFluency
    ideas:              AggregatedIdeas

    bacaan_wer: Optional[WerResult] = None

    # Overall band
    total_score:        float
    overall_band:       int         # 1–6
    overall_descriptor: str         # e.g. "Cemerlang"

    processing_time_s:  float


# ─────────────────────────────────────────────────────────────────────────────
# SPEAKING — RETRY
# ─────────────────────────────────────────────────────────────────────────────

class SpeakingRetryRequest(BaseModel):
    session_id: str
    user_id:    str


# ─────────────────────────────────────────────────────────────────────────────
# LISTENING
# ─────────────────────────────────────────────────────────────────────────────

class ListeningStartRequest(BaseModel):
    task_type: Literal["mendengar"]
    user_id: str
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    mode: Literal["quiz", "latihan"] = "quiz"


class ListeningQuestion(BaseModel):
    question_id: str
    question_text: str
    question_type: Literal["short_answer", "mcq", "true_false"]
    marks: int
    options: Optional[List[str]] = None
    answer_scheme: Optional[List[str]] = None


class ListeningPetikan(BaseModel):
    title: str
    questions: List[ListeningQuestion]


class ListeningStartResponse(BaseModel):
    session_id: str
    task_type: str
    paper: str
    title: str
    description: str
    instructions: str
    time_limit_minutes: int
    tema: str
    audio_url: str
    petikans: List[ListeningPetikan]


class ListeningAnswer(BaseModel):
    question_id: str
    answer: str


class ListeningSubmitRequest(BaseModel):
    session_id: str
    user_id: str
    task_type: Literal["mendengar"]
    answers: List[ListeningAnswer]


class ListeningQuestionFeedback(BaseModel):
    question_id: str
    question_text: str
    user_answer: str
    correct_answer: str
    marks_awarded: float
    max_marks: int
    feedback: str


class ListeningSubmitResponse(BaseModel):
    session_id: str
    quiz_type: str
    user_id: str
    total_score: float
    max_score: int
    percentage: float
    grade: str
    question_feedbacks: List[ListeningQuestionFeedback]
    overall_feedback: str
    suggestions: List[str]


class ListeningRetryRequest(BaseModel):
    session_id: str
    user_id: str
    task_type: Literal["mendengar"]