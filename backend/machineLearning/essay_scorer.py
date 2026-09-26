"""
XLM-RoBERTa essay scorer for SPM Bahasa Melayu.
Uses pretrained XLM-RoBERTa for linguistic feature extraction.
Scoring uses BM-specific rule-based logic per SPM rubric traits.

score_essay() returns:
  - karangan_pendek   : trait scores + subtotal (max 30)
  - karangan_panjang  : trait scores + subtotal (max 70)
  - total_score       : combined mark (max 100)
  - grade             : A–F based on combined percentage
"""
import re
import torch
import numpy as np
from transformers import XLMRobertaTokenizer, XLMRobertaModel
from langdetect import detect_langs, LangDetectException

# ── Model loading ────────────────────────────────────────────────────────
MODEL_NAME = "xlm-roberta-base"
_tokenizer = None
_model     = None


def get_model():
    global _tokenizer, _model
    if _tokenizer is None:
        print("Loading XLM-RoBERTa... (first run only)")
        _tokenizer = XLMRobertaTokenizer.from_pretrained(MODEL_NAME)
        _model     = XLMRobertaModel.from_pretrained(MODEL_NAME)
        _model.eval()
        print("XLM-RoBERTa ready.")
    return _tokenizer, _model


# ─────────────────────────────────────────────────────────────────────────────
# SPM RUBRIC — max marks per trait per paper type
# ─────────────────────────────────────────────────────────────────────────────

SPM_RUBRIC = {
    "karangan_pendek": {
        "max_total": 30,
        "traits": {
            "content_score":    {"max": 12},   # isi
            "language_score":   {"max":  9},   # bahasa
            "grammar_score":    {"max":  5},   # tatabahasa
            "vocabulary_score": {"max":  3},   # perbendaharaan kata
            "coherence_score":  {"max":  1},   # kohesi & koherensi
        },
    },
    "karangan_panjang": {
        "max_total": 70,
        "traits": {
            "content_score":    {"max": 28},   # isi / tugasan + idea
            "language_score":   {"max": 15},   # penggunaan bahasa / ayat
            "grammar_score":    {"max": 10},   # tatabahasa, ejaan, tanda baca
            "vocabulary_score": {"max":  7},   # kosa kata / perbendaharaan kata
            "coherence_score":  {"max": 10},   # pengolahan / wacana / pemerengganan
        },
    },
}

# Combined max (30 + 70)
SPM_MAX_TOTAL = 100

# Minimum word count required before running the full pipeline
# Essays shorter than this are considered unattempted and scored zero
MIN_WORD_COUNT = 20

# ─────────────────────────────────────────────────────────────────────────────
# BM LANGUAGE RESOURCES
# ─────────────────────────────────────────────────────────────────────────────

# ── Formal BM vocabulary (high quality language indicators) ──────────────────
FORMAL_VOCAB = [
    # Discourse markers
    "walau bagaimanapun", "oleh yang demikian", "dalam pada itu",
    "sehubungan dengan itu", "selain daripada itu", "memandangkan",
    "sekiranya", "sesungguhnya", "justeru itu", "tambahan pula",
    "malah", "bahkan", "walaupun demikian", "namun begitu",
    "dengan itu", "hal ini kerana", "lantaran itu", "maka",
    "rentetan daripada itu", "berdasarkan", "merujuk kepada",
    # Formal phrases
    "amat penting", "perlu diambil berat", "harus diakui",
    "tidak dapat dinafikan", "adalah wajar", "sememangnya",
    "tidak syak lagi", "dapat disimpulkan", "kesimpulannya",
    "sebagai rumusan", "pada pandangan saya", "secara keseluruhannya",
]

# ── Informal / colloquial words (penalised in formal essay) ──────────────────
INFORMAL_WORDS = [
    r'\btak\b', r'\bnak\b', r'\bgak\b', r'\bjer\b', r'\bje\b',
    r'(?<=\S)la\b',     # e.g. "begitu la" → hits; "Allah" → misses
    r'(?<=\S)lah\b',    # e.g. "sudahlah"  → hits; "telah" → misses
    r'\bkan\b', r'\bokay\b', r'\bok\b',
    r'\bgitu\b', r'\bgini\b', r'\bkena\b', r'\bpakai\b',
    r'\bbudak\b', r'\borang\b(?!\s+lain)',
    r'\bpegi\b', r'\bsaya\s+punya\b',
    r'\bdia\s+orang\b', r'\bkita\s+orang\b',
]

# ── Whitelist: formal BM words that share a surface form with an informal
_INFORMAL_WHITELIST: set[str] = {
    "allah", "telah", "jikalah", "adalah", "sekolah", "masalah",
    "peralatan", "perjalanan", "kehidupan", "pelajaran",
}

# ── Grammar error patterns ────────────────────────────────────────────────────
GRAMMAR_ERRORS = [
    # Wrong "di" usage (spatial vs prefix)
    (r'\bdi\s+(pergi|buat|ambil|makan|minum|beli|jual|hantar)\b',
     "kesalahan penggunaan 'di'"),
    # Double affixes
    (r'\bmen\w+kan\s+kan\b', "imbuhan berganda"),
    (r'\bber\w+\s+ber\w+\b', "awalan berganda"),
    # Repeated words
    (r'\b(\w+)\s+\1\b', "perkataan berulang"),
    # Wrong "di" / "ke" spacing
    (r'\bdi(?!antara|dalam|atas|bawah|sebalik|belakang|depan|sini|sana|mana)[a-z]{3,}\b',
     "penulisan 'di' tidak betul"),
    # Informal negation
    (r'\btak\s+\w+', "penggunaan 'tak' tidak formal"),
    # Wrong pronoun in formal essay
    (r'\b(aku|kau|hang|ang)\b', "ganti nama tidak formal"),
    # English words mixed in (code-switching)
    (r'\b(because|but|and|also|very|more|less|good|bad|make|get|put)\b',
     "percampuran bahasa Inggeris"),
]

# ── Cohesion / discourse connectors ──────────────────────────────────────────
COHESION_INTRO = [
    "pada masa kini", "akhir-akhir ini", "dewasa ini", "zaman ini",
    "tidak dapat dinafikan", "sememangnya", "sesungguhnya",
]
COHESION_BODY = [
    "pertama", "pertama sekali", "pertama-tama",
    "kedua", "ketiga", "keempat",
    "selain itu", "selain daripada itu", "di samping itu",
    "tambahan pula", "tambahan lagi", "malah", "bahkan",
    "seterusnya", "selepas itu", "kemudian",
    "hal ini", "dengan ini", "justeru",
    "namun", "namun begitu", "walau bagaimanapun",
    "walaupun demikian", "sebaliknya",
]
COHESION_CONCLUSION = [
    "kesimpulannya", "sebagai kesimpulan", "sebagai rumusan",
    "secara keseluruhannya", "ringkasnya", "pendek kata",
    "oleh itu", "oleh yang demikian", "dengan itu",
    "diharapkan", "semoga", "adalah diharapkan",
]

# ── Content quality indicators ────────────────────────────────────────────────
# Evidence of elaboration and explanation
ELABORATION_MARKERS = [
    "hal ini", "ini bermakna", "sebagai contoh", "contohnya",
    "misalnya", "antaranya", "antara", "seperti", "iaitu",
    "yang mana", "kerana", "oleh sebab", "disebabkan",
    "akibatnya", "kesannya", "implikasinya", "natijahnya",
]


# ─────────────────────────────────────────────────────────────────────────────
# LANGUAGE DETECTION
# Detects non-Malay essays and applies zero score or proportional penalty.
# Uses langdetect library which supports 55 languages.
# ─────────────────────────────────────────────────────────────────────────────

# Languages considered acceptable in SPM BM essays
# 'ms' = Malay, 'id' = Indonesian (very similar to Malay, acceptable)
_ACCEPTABLE_LANGUAGES = {"ms", "id"}

# Language code to Malay name mapping for feedback messages
_LANGUAGE_NAMES = {
    "en":    "bahasa Inggeris",
    "zh-cn": "bahasa Cina",
    "zh-tw": "bahasa Cina",
    "ta":    "bahasa Tamil",
    "ja":    "bahasa Jepun",
    "ko":    "bahasa Korea",
    "ar":    "bahasa Arab",
    "fr":    "bahasa Perancis",
    "de":    "bahasa Jerman",
    "es":    "bahasa Sepanyol",
    "pt":    "bahasa Portugis",
    "ru":    "bahasa Rusia",
    "hi":    "bahasa Hindi",
    "th":    "bahasa Thai",
    "vi":    "bahasa Vietnam",
}

def _get_language_name(lang_code: str) -> str:
    """Returns the Malay name of a language given its ISO code."""
    return _LANGUAGE_NAMES.get(lang_code, f"bahasa asing ({lang_code})")


def _detect_language(essay: str) -> tuple[str, float, list]:
    """
    Detects the primary language of the essay using langdetect.

    Returns
    -------
    primary_lang : str   — ISO code of the dominant language (e.g. "en", "ms")
    malay_ratio  : float — combined probability of Malay + Indonesian (0.0–1.0)
    all_langs    : list  — list of (lang_code, probability) tuples sorted by prob

    Notes
    -----
    langdetect is non-deterministic by default. Results are consistent enough
    for this use case but may vary slightly on short essays.
    Malay and Indonesian share high lexical overlap so both are accepted.
    """
    try:
        langs     = detect_langs(essay)   # e.g. [en:0.85, ms:0.14]
        all_langs = [(l.lang, round(l.prob, 4)) for l in langs]

        # Sum Malay + Indonesian probability — both are acceptable
        malay_ratio = sum(
            prob for lang, prob in all_langs
            if lang in _ACCEPTABLE_LANGUAGES
        )

        primary_lang = all_langs[0][0] if all_langs else "unknown"
        return primary_lang, round(malay_ratio, 4), all_langs

    except LangDetectException:
        # Detection fails on very short or symbol-heavy text — assume Malay
        return "ms", 1.0, [("ms", 1.0)]


def _language_zero_result(primary_lang: str, malay_ratio: float) -> dict:
    """
    Returns a fully-structured zero-score result when the essay is detected
    as written entirely or predominantly in a non-Malay language.
    Grade F is assigned regardless of content quality.
    """
    lang_name = _get_language_name(primary_lang)
    feedback  = (
        f"Karangan ini dikesan ditulis dalam {lang_name}. "
        "Karangan SPM Bahasa Melayu mesti ditulis sepenuhnya dalam bahasa Melayu. "
        "Sila tulis semula karangan anda dalam bahasa Melayu untuk mendapat markah."
    )
    zero_reasons = {
        "content":    feedback,
        "language":   feedback,
        "grammar":    feedback,
        "vocabulary": feedback,
        "coherence":  feedback,
    }
    zero_paper = {
        "content_score":    0.0,
        "language_score":   0.0,
        "grammar_score":    0.0,
        "vocabulary_score": 0.0,
        "coherence_score":  0.0,
        "subtotal":         0.0,
        "max_total":        0,    # filled per paper type below
        "percentage":       0.0,
        "reasons":          zero_reasons,
    }
    return {
        "karangan_pendek":  {**zero_paper, "max_total": SPM_RUBRIC["karangan_pendek"]["max_total"]},
        "karangan_panjang": {**zero_paper, "max_total": SPM_RUBRIC["karangan_panjang"]["max_total"]},
        "total_score":       0.0,
        "max_score":         SPM_MAX_TOTAL,
        "percentage":        0.0,
        "grade":             "F",
        "primary_language":  primary_lang,
        "malay_ratio":       malay_ratio,
        "language_feedback": feedback,
        "features": {
            "word_count": 0, "sentence_count": 0, "paragraph_count": 0,
            "ttr": 0.0, "complex_word_ratio": 0.0, "affix_ratio": 0.0,
            "avg_sent_len": 0.0, "formal_count": 0, "informal_count": 0,
            "total_errors": 0, "grammar_errors": [], "body_markers": 0,
            "has_intro": False, "has_conclusion": False, "elaboration": 0,
        },
    }



# ─────────────────────────────────────────────────────────────────────────────
# ZERO-SCORE RESULT BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def _zero_result() -> dict:
    """
    CHANGE 1 (helper): Returns a fully-structured result dict with all scores
    set to zero.  Used by score_essay() when the essay is blank or below the
    MIN_WORD_COUNT threshold so the caller always receives a consistent shape.
    """
    zero_reasons = {
        "content":    "Karangan terlalu pendek atau kosong untuk dinilai.",
        "language":   "Karangan terlalu pendek atau kosong untuk dinilai.",
        "grammar":    "Karangan terlalu pendek atau kosong untuk dinilai.",
        "vocabulary": "Karangan terlalu pendek atau kosong untuk dinilai.",
        "coherence":  "Karangan terlalu pendek atau kosong untuk dinilai.",
    }
    zero_paper = {
        "content_score":    0.0,
        "language_score":   0.0,
        "grammar_score":    0.0,
        "vocabulary_score": 0.0,
        "coherence_score":  0.0,
        "subtotal":         0.0,
        "percentage":       0.0,
        "reasons":          zero_reasons,
    }
    return {
        "karangan_pendek":  {**zero_paper, "max_total": SPM_RUBRIC["karangan_pendek"]["max_total"]},
        "karangan_panjang": {**zero_paper, "max_total": SPM_RUBRIC["karangan_panjang"]["max_total"]},
        "total_score": 0.0,
        "max_score":   SPM_MAX_TOTAL,
        "percentage":  0.0,
        "grade":       "F",
        "features": {
            "word_count": 0, "sentence_count": 0, "paragraph_count": 0,
            "ttr": 0.0, "complex_word_ratio": 0.0, "affix_ratio": 0.0,
            "avg_sent_len": 0.0, "formal_count": 0, "informal_count": 0,
            "total_errors": 0, "grammar_errors": [], "body_markers": 0,
            "has_intro": False, "has_conclusion": False, "elaboration": 0,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# OFF-TOPIC PENALTY
# ─────────────────────────────────────────────────────────────────────────────
OFF_TOPIC_TRAIT_MAX = 2

def off_topic_penalty(paper: dict, quiz_type: str, relevance_ratio: float) -> dict:
    if relevance_ratio >= 0.20:
        return paper

    trait_maxes = SPM_RUBRIC[quiz_type]["traits"]

    paper["original_scores"] = {
        trait: paper[trait]
        for trait in ("content_score", "language_score", "grammar_score",
                      "vocabulary_score", "coherence_score")
    }

    for trait, meta in trait_maxes.items():
        original_max = meta["max"] # from SPM_RUBRIC directly
        original_score = paper[trait]

        ratio        = original_score / original_max if original_max > 0 else 0
        paper[trait] = round(min(ratio * OFF_TOPIC_TRAIT_MAX, OFF_TOPIC_TRAIT_MAX), 1)

    # Subtotal is capped at 10, but max_total stays as original (70)
    paper["subtotal"]   = round(
        paper["content_score"] + paper["language_score"] + paper["grammar_score"] +
        paper["vocabulary_score"] + paper["coherence_score"], 1
    )
    # max_total intentionally NOT changed — keeps original 30 or 70
    paper["percentage"] = round((paper["subtotal"] / paper["max_total"]) * 100, 1)

    relevance_pct = round(relevance_ratio * 100)
    paper["reasons"]["content"] += (
        f" [PENALTI: Karangan tidak menjawab soalan ({relevance_pct}% kesesuaian) — "
        f"markah dikurangkan, maksimum efektif ialah 10 / {paper['max_total']} mata]"
    )

    paper["off_topic_penalty_applied"] = True
    return paper


# ─────────────────────────────────────────────────────────────────────────────
# FEATURE EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

def extract_features(essay: str) -> dict:
    """
    Extracts linguistic features using XLM-RoBERTa + BM-specific rules.
    Returns embedding + handcrafted metrics.
    """
    tokenizer, model = get_model()
    essay_lower      = essay.lower()

    # ── XLM-RoBERTa CLS embedding ────────────────────────────────────────────
    inputs = tokenizer(
        essay,
        max_length=512,
        truncation=True,
        padding="max_length",
        return_tensors="pt",
    )
    with torch.no_grad():
        outputs = model(**inputs)
    cls_embedding = outputs.last_hidden_state[:, 0, :].squeeze().numpy()

    # ── Basic counts ─────────────────────────────────────────────────────────
    sentences  = [s.strip() for s in re.split(r'[.!?]', essay) if len(s.strip()) > 5]
    words      = re.findall(r'\b\w+\b', essay_lower)
    word_count = len(words)
    paragraphs = [p.strip() for p in essay.split('\n') if len(p.strip()) > 20]

    # ── Vocabulary richness ───────────────────────────────────────────────────
    unique_words = set(words)
    ttr          = len(unique_words) / word_count if word_count > 0 else 0

    # Advanced vocabulary: words longer than 7 chars (complex BM words)
    complex_words      = [w for w in words if len(w) > 7]
    complex_word_ratio = len(complex_words) / word_count if word_count > 0 else 0

    # Affixed words (ber-, me-, pe-, ke-, -an, -kan, -i)
    affixed_words = [
        w for w in words
        if re.match(r'^(ber|men|mem|me|pe|pem|per|ke|ter|di)\w{3,}', w)
        or re.match(r'\w{3,}(kan|an|i|nya)$', w)
    ]
    affix_ratio = len(affixed_words) / word_count if word_count > 0 else 0

    # ── Sentence structure ────────────────────────────────────────────────────
    avg_sent_len = word_count / len(sentences) if sentences else 0

    # Sentence variety: mix of short and long sentences
    sent_lengths  = [len(re.findall(r'\b\w+\b', s)) for s in sentences]
    sent_variance = np.var(sent_lengths) if sent_lengths else 0

    # ── Formal vs informal language ───────────────────────────────────────────
    formal_count   = sum(1 for v in FORMAL_VOCAB if v in essay_lower)
    informal_count = 0
    for pattern in INFORMAL_WORDS:
        for match in re.finditer(pattern, essay_lower, re.IGNORECASE):
            token = match.group(0).strip().lower()
            if token not in _INFORMAL_WHITELIST:
                informal_count += 1

    # ── Grammar errors ────────────────────────────────────────────────────────
    grammar_errors = []
    for pattern, description in GRAMMAR_ERRORS:
        matches = re.findall(pattern, essay_lower, re.IGNORECASE)
        if matches:
            grammar_errors.append({
                "type":    description,
                "count":   len(matches),
                "samples": matches[:2],
            })
    total_errors = sum(e["count"] for e in grammar_errors)

    # ── Cohesion analysis ─────────────────────────────────────────────────────
    has_intro      = any(m in essay_lower for m in COHESION_INTRO)
    body_markers   = sum(1 for m in COHESION_BODY if m in essay_lower)
    has_conclusion = any(m in essay_lower for m in COHESION_CONCLUSION)
    elaboration    = sum(1 for m in ELABORATION_MARKERS if m in essay_lower)

    # ── Content indicators ────────────────────────────────────────────────────
    # Check for introduction, body, conclusion structure
    has_structure = len(paragraphs) >= 3

    return {
        # XLM-RoBERTa representation (internal use only — not forwarded to DB)
        "cls_embedding":     cls_embedding,

        # Basic
        "word_count":        word_count,
        "sentence_count":    len(sentences),
        "paragraph_count":   len(paragraphs),

        # Vocabulary
        "unique_words":      len(unique_words),
        "ttr":               round(ttr, 4),
        "complex_word_ratio":round(complex_word_ratio, 4),
        "affix_ratio":       round(affix_ratio, 4),

        # Sentence structure
        "avg_sent_len":      round(avg_sent_len, 2),
        "sent_variance":     round(float(sent_variance), 2),

        # Language quality
        "formal_count":      formal_count,
        "informal_count":    informal_count,

        # Grammar
        "total_errors":      total_errors,
        "grammar_errors":    grammar_errors,

        # Cohesion
        "has_intro":         has_intro,
        "body_markers":      body_markers,
        "has_conclusion":    has_conclusion,
        "elaboration":       elaboration,

        # Content
        "has_structure":     has_structure,
    }


# ─────────────────────────────────────────────────────────────────────────────
# TRAIT 1 — ISI KANDUNGAN (Content)
# Evaluates: relevance, depth, number of points, elaboration
# ─────────────────────────────────────────────────────────────────────────────

def score_content(features: dict, max_score: int, quiz_type: str, relevance_ratio: float = 1.0) -> tuple[float, str]:
    """
    Word count + paragraph structure + elaboration + relevance

    Parameters
    ----------
    features         : output of extract_features()
    max_score        : rubric max for this paper type (12 or 28)
    quiz_type        : "karangan_pendek" | "karangan_panjang"
    relevance_ratio  : float 0.0-1.0 derived from Gemini relevance check
                       (relevance_score / 5).  Default 1.0 means no question
                       text was provided (backward-compatible fallback).
 
    Weighting inside content_score
    --------------------------------
      Word count   30 %  - quantity of ideas written
      Paragraphs   25 %  - structural depth / idea organisation
      Elaboration  20 %  - quality and development of ideas
      Relevance    25 %  - how well ideas match the question (Gemini)
    """
    wc        = features["word_count"]
    para      = features["paragraph_count"]
    elab      = features["elaboration"]

    # ── Word count thresholds differ per essay type ───────────────────────────
    # Karangan Pendek: SPM target 150–200 words
    # Karangan Panjang: SPM target 350–500 words
    if quiz_type == "karangan_pendek":
        if wc >= 170:   wc_score = 1.00   # meets / exceeds target
        elif wc >= 140: wc_score = 0.85   # slightly short but acceptable
        elif wc >= 120: wc_score = 0.65   # below target
        elif wc >= 100: wc_score = 0.40   # significantly short
        elif wc >= 60:  wc_score = 0.20   # very short
        else:           wc_score = 0.05   # barely attempted
    else:  # karangan_panjang
        if wc >= 450:   wc_score = 1.00   # meets / exceeds target
        elif wc >= 350: wc_score = 0.85   # slightly short
        elif wc >= 250: wc_score = 0.65   # below target
        elif wc >= 180: wc_score = 0.45   # significantly short
        elif wc >= 100: wc_score = 0.25   # very short
        else:           wc_score = 0.05   # barely attempted
 
    # Paragraph structure (intro + body + conclusion = 3+ paragraphs)
    if para >= 4:   para_score = 1.00
    elif para == 3: para_score = 0.85
    elif para == 2: para_score = 0.60
    else:           para_score = 0.30
 
    # Elaboration (examples, reasons, explanations)
    if elab >= 6:   elab_score = 1.00
    elif elab >= 4: elab_score = 0.80
    elif elab >= 2: elab_score = 0.60
    elif elab >= 1: elab_score = 0.40
    else:           elab_score = 0.20
 
    # Relevance sub-score (0.0-1.0, passed in from Gemini check)
    # Clamped to [0, 1] in case of unexpected values
    rel_score = max(0.0, min(1.0, relevance_ratio))
 
    # Weighted combination (total weights = 1.0)
    ratio = (
        (wc_score   * 0.30) +
        (para_score * 0.25) +
        (elab_score * 0.20) +
        (rel_score  * 0.25)
    )
    score = round(min(ratio * max_score, max_score), 1)
 
    # Reason text combines quantity/quality and relevance signal
    target_wc     = "150-200" if quiz_type == "karangan_pendek" else "350-500"
    relevance_pct = round(rel_score * 100)
 
    if rel_score < 0.40:
        # Relevance failure is severe: lead the feedback with it
        reason = (
            f"Isi tidak menjawab tajuk soalan (kesesuaian: {relevance_pct}%) - "
            f"markah isi sangat terjejas walaupun karangan mengandungi {wc} patah perkataan"
        )
    elif score >= max_score * 0.80:
        reason = (
            f"Isi kandungan lengkap, relevan dan dihuraikan dengan baik "
            f"({wc} patah perkataan, kesesuaian tajuk: {relevance_pct}%)"
        )
    elif score >= max_score * 0.60:
        reason = (
            f"Isi kandungan mencukupi dan kebanyakannya relevan "
            f"({wc} patah perkataan, kesesuaian tajuk: {relevance_pct}%)"
        )
    elif score >= max_score * 0.40:
        reason = (
            f"Isi terhad atau kurang relevan dengan tajuk "
            f"({wc} patah perkataan, sasaran {target_wc}, kesesuaian tajuk: {relevance_pct}%)"
        )
    else:
        reason = (
            f"Isi sangat terhad dan/atau tidak menjawab tajuk "
            f"({wc} patah perkataan, sasaran {target_wc}, kesesuaian tajuk: {relevance_pct}%)"
        )
 
    return score, reason


# ─────────────────────────────────────────────────────────────────────────────
# TRAIT 2 — PENGGUNAAN BAHASA (Language Use)
# Evaluates: formal register, sentence variety, style
# ─────────────────────────────────────────────────────────────────────────────

def score_language(features: dict, max_score: int) -> tuple[float, str]:
    """
    Formal vocab count, informal penalty, sentence variety
    """
    formal        = features["formal_count"]
    informal      = features["informal_count"]
    sent_variance = features["sent_variance"]

    # Formal language usage
    if formal >= 8:   formal_score = 1.00
    elif formal >= 5: formal_score = 0.85
    elif formal >= 3: formal_score = 0.65
    elif formal >= 1: formal_score = 0.45
    else:             formal_score = 0.25

    # Penalty for informal/colloquial words
    if informal == 0:   informal_penalty = 1.00
    elif informal <= 2: informal_penalty = 0.80
    elif informal <= 4: informal_penalty = 0.60
    elif informal <= 6: informal_penalty = 0.40
    else:               informal_penalty = 0.20

    # Sentence variety (mix of short and long = more mature writing)
    if sent_variance >= 30:   variety_score = 1.00
    elif sent_variance >= 15: variety_score = 0.80
    elif sent_variance >= 8:  variety_score = 0.60
    else:                     variety_score = 0.40

    ratio = (formal_score * 0.45) + (informal_penalty * 0.35) + (variety_score * 0.20)
    score = round(ratio * max_score, 1)
    score = min(score, max_score)

    if score >= max_score * 0.80:
        reason = "Penggunaan bahasa formal dan mantap"
    elif score >= max_score * 0.60:
        reason = "Bahasa sesuai tetapi perlu lebih banyak kata-kata formal"
    elif score >= max_score * 0.40:
        reason = "Terdapat penggunaan bahasa tidak formal, perlu diperbaiki"
    else:
        reason = "Penggunaan bahasa tidak formal dan tidak sesuai untuk karangan SPM"

    return score, reason


# ─────────────────────────────────────────────────────────────────────────────
# TRAIT 3 — TATABAHASA (Grammar)
# Evaluates: sentence correctness, affix usage, grammatical accuracy
# ─────────────────────────────────────────────────────────────────────────────

def score_grammar(features: dict, max_score: int) -> tuple[float, str]:
    """
    Pattern-based grammar error detection
    """
    errors      = features["total_errors"]
    affix_ratio = features["affix_ratio"]
    wc          = features["word_count"]

    # Error rate (errors per 100 words)
    error_rate = (errors / wc * 100) if wc > 0 else 0

    if error_rate == 0:    error_score = 1.00
    elif error_rate <= 1:  error_score = 0.90
    elif error_rate <= 2:  error_score = 0.75
    elif error_rate <= 4:  error_score = 0.55
    elif error_rate <= 6:  error_score = 0.35
    else:                  error_score = 0.15

    # Affixation (correct use of BM affixes = grammatical competence)
    if affix_ratio >= 0.25:   affix_score = 1.00
    elif affix_ratio >= 0.18: affix_score = 0.85
    elif affix_ratio >= 0.12: affix_score = 0.65
    elif affix_ratio >= 0.06: affix_score = 0.45
    else:                     affix_score = 0.25

    ratio = (error_score * 0.65) + (affix_score * 0.35)
    score = round(ratio * max_score, 1)
    score = min(score, max_score)

    # Build specific error feedback
    error_details = features["grammar_errors"]
    if not error_details:
        reason = "Tatabahasa tepat dan betul"
    else:
        top_errors = ", ".join(e["type"] for e in error_details[:2])
        if score >= max_score * 0.70:
            reason = f"Tatabahasa baik, sedikit kesilapan: {top_errors}"
        elif score >= max_score * 0.40:
            reason = f"Terdapat beberapa kesilapan tatabahasa: {top_errors}"
        else:
            reason = f"Banyak kesilapan tatabahasa perlu dibetulkan: {top_errors}"

    return score, reason


# ─────────────────────────────────────────────────────────────────────────────
# TRAIT 4 — PERBENDAHARAAN KATA (Vocabulary)
# Evaluates: word variety, complexity, BM-specific richness
# ─────────────────────────────────────────────────────────────────────────────

def score_vocabulary(features: dict, max_score: int) -> tuple[float, str]:
    """
    TTR + complex word ratio + affix variety
    """
    ttr          = features["ttr"]
    complex_r    = features["complex_word_ratio"]
    formal_count = features["formal_count"]

    # Type-token ratio (vocabulary diversity)
    if ttr >= 0.65:   ttr_score = 1.00
    elif ttr >= 0.55: ttr_score = 0.85
    elif ttr >= 0.45: ttr_score = 0.70
    elif ttr >= 0.35: ttr_score = 0.50
    elif ttr >= 0.25: ttr_score = 0.30
    else:             ttr_score = 0.15

    # Complex / multi-syllable words
    if complex_r >= 0.35:   complex_score = 1.00
    elif complex_r >= 0.25: complex_score = 0.80
    elif complex_r >= 0.15: complex_score = 0.60
    elif complex_r >= 0.08: complex_score = 0.40
    else:                   complex_score = 0.20

    # Formal connectors as advanced vocab indicator
    if formal_count >= 5:   formal_score = 1.00
    elif formal_count >= 3: formal_score = 0.75
    elif formal_count >= 1: formal_score = 0.50
    else:                   formal_score = 0.25

    ratio = (ttr_score * 0.45) + (complex_score * 0.35) + (formal_score * 0.20)
    score = round(ratio * max_score, 1)
    score = min(score, max_score)

    if score >= max_score * 0.80:
        reason = "Perbendaharaan kata kaya dan pelbagai"
    elif score >= max_score * 0.60:
        reason = "Perbendaharaan kata mencukupi, boleh diperkayakan lagi"
    elif score >= max_score * 0.40:
        reason = "Perbendaharaan kata terhad, gunakan lebih banyak kata-kata formal"
    else:
        reason = "Perbendaharaan kata sangat terhad, perlu banyak membaca"

    return score, reason


# ─────────────────────────────────────────────────────────────────────────────
# TRAIT 5 — KOHESI & KOHERENSI (Cohesion & Coherence)
# Evaluates: logical flow, connectors, paragraph linking
# ─────────────────────────────────────────────────────────────────────────────

def score_coherence(features: dict, max_score: int) -> tuple[float, str]:
    """
    Discourse marker analysis + structural check
    """
    has_intro      = features["has_intro"]
    body_markers   = features["body_markers"]
    has_conclusion = features["has_conclusion"]
    para_count     = features["paragraph_count"]

    # All three structural components present
    structure_score = (
        (0.30 if has_intro else 0) +
        (0.40 if has_conclusion else 0) +
        (0.30 if para_count >= 3 else 0.15 if para_count == 2 else 0)
    )

    # Body paragraph connectors
    if body_markers >= 5:   marker_score = 1.00
    elif body_markers >= 3: marker_score = 0.80
    elif body_markers >= 2: marker_score = 0.60
    elif body_markers >= 1: marker_score = 0.40
    else:                   marker_score = 0.10

    ratio = (structure_score * 0.50) + (marker_score * 0.50)
    score = round(ratio * max_score, 1)
    score = min(score, max_score)

    missing = []
    if not has_intro:      missing.append("pendahuluan")
    if not has_conclusion: missing.append("penutup")
    if body_markers < 2:   missing.append("kata penghubung")

    if not missing:
        reason = "Karangan mempunyai struktur dan kohesi yang baik"
    else:
        reason = f"Perlu perbaiki: {', '.join(missing)}"

    return score, reason


# ─────────────────────────────────────────────────────────────────────────────
# GRADE MAPPING
# ─────────────────────────────────────────────────────────────────────────────

def percentage_to_grade(percentage: float) -> str:
    if percentage >= 80: return "A"
    if percentage >= 65: return "B"
    if percentage >= 50: return "C"
    if percentage >= 40: return "D"
    if percentage >= 20: return "E"
    return "F"


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPER — scores one paper type from shared features
# ─────────────────────────────────────────────────────────────────────────────
 
def _score_for_type(features: dict, quiz_type: str, relevance_ratio: float = 1.0) -> dict:
    """
    Runs all five trait scorers for a single paper type and returns a
    self-contained result block (scores, max, subtotal, per-trait reasons).

    relevance_ratio (0.0-1.0) is computed by quiz_service.py from the
    Gemini relevance check and forwarded here so that score_content can
    incorporate it directly into the content mark.    
    """
    rubric = SPM_RUBRIC[quiz_type]
    traits = rubric["traits"]
 
    content_score,    content_reason    = score_content(
        features, traits["content_score"]["max"], quiz_type, relevance_ratio
    )
    language_score,   language_reason   = score_language(
        features, traits["language_score"]["max"]
    )
    grammar_score,    grammar_reason    = score_grammar(
        features, traits["grammar_score"]["max"]
    )
    vocabulary_score, vocabulary_reason = score_vocabulary(
        features, traits["vocabulary_score"]["max"]
    )
    coherence_score,  coherence_reason  = score_coherence(
        features, traits["coherence_score"]["max"]
    )
 
    subtotal = round(
        content_score + language_score + grammar_score +
        vocabulary_score + coherence_score,
        1,
    )
    max_total = rubric["max_total"]
 
    result = {
        "content_score":    content_score,
        "language_score":   language_score,
        "grammar_score":    grammar_score,
        "vocabulary_score": vocabulary_score,
        "coherence_score":  coherence_score,
        "subtotal":         subtotal,
        "max_total":        max_total,
        "percentage":       round((subtotal / max_total) * 100, 1),
        "reasons": {
            "content":    content_reason,
            "language":   language_reason,
            "grammar":    grammar_reason,
            "vocabulary": vocabulary_reason,
            "coherence":  coherence_reason,
        },
    }

    # Apply off-topic penalty after all normal scoring is done
    result = off_topic_penalty(result, quiz_type, relevance_ratio)
    return result
 
 
# ─────────────────────────────────────────────────────────────────────────────
# MAIN — called by quiz_service.py
# ─────────────────────────────────────────────────────────────────────────────
 
def score_essay(essay: str, relevance_ratio: float = 1.0) -> dict:
    """
    Scores a BM SPM essay for both Karangan Pendek (max 30) and
    Karangan Panjang (max 70), then combines them into a single
    total mark (max 100) with an overall A–F grade.
 
    Features are extracted once and reused for both scorings to avoid
    running XLM-RoBERTa twice on the same essay text.

    Parameters
    ────────────────
    essay            : raw essay text from the student
    relevance_ratio  : float 0.0-1.0 = (Gemini relevance_score / 5).
                       Supplied by quiz_service.py after _check_relevance().
                       Defaults to 1.0 (no penalty) when called without a
                       question context.
     
    Return structure
    ────────────────
    {
        "karangan_pendek": {
            "content_score":    float,   # /12
            "language_score":   float,   # /9
            "grammar_score":    float,   # /5
            "vocabulary_score": float,   # /3
            "coherence_score":  float,   # /1
            "subtotal":         float,   # /30
            "max_total":        30,
            "percentage":       float,
            "reasons":          { "content": str, ... }
        },
        "karangan_panjang": {
            "content_score":    float,   # /28
            "language_score":   float,   # /15
            "grammar_score":    float,   # /10
            "vocabulary_score": float,   # /7
            "coherence_score":  float,   # /10
            "subtotal":         float,   # /70
            "max_total":        70,
            "percentage":       float,
            "reasons":          { "content": str, ... }
        },
        "total_score":  float,   # karangan_pendek.subtotal + karangan_panjang.subtotal  (/100)
        "max_score":    100,
        "percentage":   float,   # total_score / 100 * 100
        "grade":        str,     # A / B / C / D / E / F
        "primary_language": str,     # ISO code of detected dominant language
        "malay_ratio":      float,   # combined ms + id probability
        "language_feedback": str,    # present only if mixed/non-Malay detected
        "features": { ... }          # raw linguistic features for DB / future training
    }
    """
    
    # ── Word count guard ──────────────────────────────────
    essay = essay.strip()
    if not essay:
        return _zero_result()
 
    quick_word_count = len(re.findall(r'\b\w+\b', essay))
    if quick_word_count < MIN_WORD_COUNT:
        return _zero_result()
    
    # ── Language detection guard ──────────────────────────────────────────────
    primary_lang, malay_ratio, all_langs = _detect_language(essay)

    # Fully or predominantly non-Malay essay → zero score, Grade F
    # malay_ratio < 0.30 means less than 30% of the essay is Malay / Indonesian
    if malay_ratio < 0.30:
        return _language_zero_result(primary_lang, malay_ratio)

    # Extract features once — shared by both paper types
    features = extract_features(essay)
 
    pendek  = _score_for_type(features, "karangan_pendek", relevance_ratio)
    panjang = _score_for_type(features, "karangan_panjang", relevance_ratio)
 
     # ── Mixed language penalty (0.30 ≤ malay_ratio < 0.80) ───────────────────
    # Significant non-Malay content reduces all trait scores proportionally.
    # Scale: malay_ratio 0.79 → ~5% penalty, malay_ratio 0.30 → ~50% penalty
    language_penalty  = 1.0
    language_feedback = None

    if malay_ratio < 0.80:
        lang_name = _get_language_name(primary_lang)

        # Linear penalty: the less Malay, the heavier the deduction
        # At malay_ratio=0.80 → penalty=0%, at malay_ratio=0.30 → penalty=50%
        penalty_factor    = (0.80 - malay_ratio) / (0.80 - 0.30)   # 0.0 → 1.0
        language_penalty  = round(1.0 - (penalty_factor * 0.50), 4) # max 50% cut
        malay_pct         = round(malay_ratio * 100)
        penalty_pct       = round((1.0 - language_penalty) * 100)

        language_feedback = (
            f"Karangan anda mengandungi campuran {lang_name} yang ketara "
            f"(anggaran {100 - malay_pct}% bukan bahasa Melayu). "
            f"Markah dikurangkan sebanyak {penalty_pct}% kerana percampuran bahasa. "
            "Karangan SPM Bahasa Melayu mesti ditulis sepenuhnya dalam bahasa Melayu."
        )

        # Apply penalty to all trait scores in both paper types
        for paper in (pendek, panjang):
            for trait in ("content_score", "language_score", "grammar_score",
                          "vocabulary_score", "coherence_score"):
                paper[trait] = round(paper[trait] * language_penalty, 1)

            # Recalculate subtotal and percentage after penalty
            paper["subtotal"] = round(
                paper["content_score"] + paper["language_score"] +
                paper["grammar_score"] + paper["vocabulary_score"] +
                paper["coherence_score"], 1
            )
            paper["percentage"] = round(
                (paper["subtotal"] / paper["max_total"]) * 100, 1
            )

            # Append language warning to all trait reasons
            for key in paper["reasons"]:
                paper["reasons"][key] += (
                    f" [AMARAN: Markah dikurangkan {penalty_pct}% "
                    f"kerana percampuran {lang_name}]"
                )

    total_score = round(pendek["subtotal"] + panjang["subtotal"], 1)
    percentage  = round((total_score / SPM_MAX_TOTAL) * 100, 1)
    grade       = percentage_to_grade(percentage)
 
    result = {
        # ── Per-paper-type results ────────────────────────────────────────────
        "karangan_pendek":  pendek,
        "karangan_panjang": panjang,
 
        # ── Combined results ──────────────────────────────────────────────────
        "total_score": total_score,
        "max_score":   SPM_MAX_TOTAL,
        "percentage":  percentage,
        "grade":       grade,
 
         # ── Language detection metadata ───────────────────────────────────────
        "primary_language": primary_lang,
        "malay_ratio":      malay_ratio,

        # ── Raw features (saved to DB for future model training) ──────────────
        "features": {
            "word_count":         features["word_count"],
            "sentence_count":     features["sentence_count"],
            "paragraph_count":    features["paragraph_count"],
            "ttr":                features["ttr"],
            "complex_word_ratio": features["complex_word_ratio"],
            "affix_ratio":        features["affix_ratio"],
            "avg_sent_len":       features["avg_sent_len"],
            "formal_count":       features["formal_count"],
            "informal_count":     features["informal_count"],
            "total_errors":       features["total_errors"],
            "grammar_errors":     features["grammar_errors"],
            "body_markers":       features["body_markers"],
            "has_intro":          features["has_intro"],
            "has_conclusion":     features["has_conclusion"],
            "elaboration":        features["elaboration"],
        },
    }

    # Include language feedback in result only when a penalty was applied
    if language_feedback:
        result["language_feedback"] = language_feedback
    return result    