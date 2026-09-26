"""
SPM Bahasa Melayu Speaking Scorer — Paper 3 (Ujian Lisan).

SPM Paper 3 Lisan Format:
  - Calon diberi bahan rangsangan (gambar + petikan) untuk dibaca selama 3 minit
  - Bacaan mekanis dinilai: sebutan, intonasi, nada
  - 4 soalan diuji: 2 soalan berdasarkan bahan rangsangan + 2 soalan KBAT
  - Tempoh masa: 3–5 minit

SPM Marking Criteria (4 traits):
  1. grammar_vocabulary   — grammatical accuracy + vocabulary range        # tatabahasa & kosa kata
  2. pronunciation        — pronunciation, intonation, tone                # sebutan, intonasi & nada
  3. fluency              — fluency and smoothness of delivery             # kefasihan & kelancaran
  4. ideas                — quality, relevance, and depth of ideas         # idea & bermakna 

ASR Model: SeamlessX/malaysian-faster-whisper-small-v3

Result shape (score_speaking return value)
──────────────────────────────────────────
Each clip now returns a full per-clip breakdown:
 
clips[n] = {
    clip_id, transcription, no_speech,          ← hard gate flag
    no_speech_reason,                           ← why the gate fired (or "")
    grammar_vocabulary: {score, reason},
    pronunciation:      {score, reason, metrics},
    fluency:            {score, reason, metrics},
    ideas:              {score, reason, question_id, question_text, category} | None
}
 
Aggregated top-level keys:
    grammar_vocabulary: {score, reason, per_clip: [...]}
    pronunciation:      {score, reason, per_clip: [...]}
    fluency:            {score, reason, per_clip: [...]}
    ideas:              {score, reason, per_question: [...]}
    overall_band, overall_descriptor, processing_time_s
WER:
    Only computed for the bacaan clip, using stimulus_text as the reference.
    Exposed in clips[0].wer (bacaan clip) and at top-level result["bacaan_wer"].
    All other clips have wer = None.    
"""
import os, re, time, json, warnings, asyncio
from typing import Optional, List

import numpy as np
import torch, librosa, jiwer
from faster_whisper import WhisperModel
from huggingface_hub import snapshot_download
from silero_vad import load_silero_vad, get_speech_timestamps
from google import genai
from google.genai import types
from difflib import SequenceMatcher

# ── Suppress librosa/audioread deprecation noise ─────────────────────────────
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

MODEL_ID = "SeamlessX/malaysian-faster-whisper-small-v3-ct2"
LANG_DETECT_MODEL_ID = "small"
LANG_DETECT_SECS = 10
SAMPLE_RATE = 16_000       # Whisper requires 16 kHz mono audio
MIN_AUDIO_SECS = 3.0          # Reject clips shorter than this (not scoreable)
MAX_AUDIO_SECS = 360.0        # 6-minute cap; covers 3–5 min SPM format + buffer

# Thresholds for the no-speech gate
MIN_RMS_ENERGY  = 0.005        # Below this → treat as silence/noise
MIN_WORD_COUNT  = 5            # Below this → treat as no scoreable speech

LANG_NAME_MAP = {
    "ms": "Bahasa Melayu",
    "id": "Bahasa Indonesia",
    "en": "Bahasa Inggeris",
    "zh": "Bahasa Cina",
    "ta": "Bahasa Tamil",
    "ar": "Bahasa Arab",
}

GEMINI_MODEL = "gemma-4-31b-it" #"gemini-2.5-flash" "gemini-3.1-flash-lite-preview" "gemma-4-31b-it"


# ─────────────────────────────────────────────────────────────────────────────
# HUGGINGFACE WINDOWS FIX
# Disable symlinks on Windows to avoid WinError 1314
# ─────────────────────────────────────────────────────────────────────────────

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"


# ─────────────────────────────────────────────────────────────────────────────
# SPM LISAN RUBRIC
# Band 1–6 per trait, matching official SPM oral marking scheme
# ─────────────────────────────────────────────────────────────────────────────

SPM_BAND_DESCRIPTORS = {
    6: "Cemerlang",
    5: "Kepujian",
    4: "Baik",
    3: "Memuaskan",
    2: "Lemah",
    1: "Sangat Lemah",
}

# Per-trait band descriptors aligned with SPM Lisan criteria
SPM_TRAIT_DESCRIPTORS = {
    "grammar_vocabulary": {           # tatabahasa & kosa kata
        6: "Tatabahasa tepat sepenuhnya; kosa kata luas dan tepat.",
        5: "Tatabahasa hampir tepat; kosa kata pelbagai dan sesuai.",
        4: "Tatabahasa sebahagian besar betul; kosa kata memuaskan.",
        3: "Terdapat beberapa kesilapan tatabahasa; kosa kata terhad.",
        2: "Banyak kesilapan tatabahasa; kosa kata sangat terhad.",
        1: "Tatabahasa tidak tepat dan kosa kata sangat lemah.",
    },
    "pronunciation": {                # sebutan, intonasi & nada
        6: "Sebutan jelas, intonasi semula jadi dan nada sangat sesuai.",
        5: "Sebutan baik, intonasi baik dengan sedikit kepincangan nada.",
        4: "Sebutan memuaskan, intonasi dan nada kebanyakannya betul.",
        3: "Terdapat kesilapan sebutan; intonasi dan nada kadang tidak tepat.",
        2: "Sebutan kerap tidak jelas; intonasi monoton dan nada tidak sesuai.",
        1: "Sebutan tidak jelas, intonasi dan nada sangat lemah.",
    },
    "fluency": {                      # kefasihan & kelancaran
        6: "Fasih sepenuhnya; tiada gangguan, lancar dan spontan.",
        5: "Fasih dengan sedikit keraguan yang tidak mengganggu.",
        4: "Agak lancar; terdapat beberapa jeda yang tidak ketara.",
        3: "Kelancaran terganggu dengan jeda dan pengulangan yang kerap.",
        2: "Kerap berhenti; pertuturan terputus-putus.",
        1: "Tidak lancar; sangat kerap berhenti atau diam.",
    },
    "ideas": {                        # idea & bermakna
        6: "Idea relevan, mendalam, teratur dan sangat bermakna.",
        5: "Idea relevan dan bermakna dengan huraian yang baik.",
        4: "Idea mencukupi dan kebanyakannya relevan.",
        3: "Idea terhad; ada yang tidak relevan atau tidak dihuraikan.",
        2: "Idea sangat terhad dan kebanyakannya tidak relevan.",
        1: "Tiada idea yang jelas atau tidak menjawab soalan.",
    },
}

# Common BM filler words that reduce fluency/kelancaran score
BM_FILLERS = [
    r'\beh\b', r'\berr\b', r'\berm\b', r'\bah\b', r'\bum\b',
    r'\bkan\b', r'(?<=\S)lah\b', r'\bgitu\b', r'\bapa\b', r'\btuh\b',
    r'\bmaksud\s+saya\b',
]

# Formal BM vocabulary — signals good tatabahasa & kosa kata
FORMAL_VOCAB = [
    "walau bagaimanapun", "oleh yang demikian", "sehubungan dengan itu",
    "selain daripada itu", "memandangkan", "sekiranya", "sesungguhnya",
    "justeru itu", "tambahan pula", "lantaran itu", "rentetan daripada itu",
    "tidak dapat dinafikan", "adalah wajar", "sememangnya",
    "dapat disimpulkan", "kesimpulannya", "secara keseluruhannya",
    "berdasarkan", "merujuk kepada", "pada pandangan saya",
]

# BM Slang that reduce pronunciation/sebutan, intonasi & nada score
SLANG = [
    r'\bgila\b', r'\bweh\b', r'\bmeh\b', r'\bbro\b',
    r'\btakde\b', r'\bnak\b', r'\bgak\b', r'\blah\b',
]

_HALLUCINATION_PATTERNS = [
    r'jangan lupa like share dan subscribe',
    r'jangan lupa like share subscribe',
    r'terima kasih kerana menonton',
    r'subscribe channel ini',
    r'tonton video ini',
    r'tekan loceng',
    r'terima kasih kerana sudi meluangkan masa',
]

_BM_SPELLING_PROMPT = (
    "moden siber teknologi teknikal digital fizikal sosial kritikal "
    "ekonomi industri kreatif ekosistem komuniti inovasi produktiviti "
    "akademik sistematik strategik infrastruktur keusahawanan berleluasa "
    "landskap walau bagaimanapun"
)

WER_TRANSFORM = jiwer.Compose([
    jiwer.ToLowerCase(),
    jiwer.RemovePunctuation(),
    jiwer.SubstituteRegexes({
        r'\(.*?\)': '',         # drop parenthetical e.g. ()
        r'\be-(\w+)': r'\1',    # e-hailing → hailing, e-mel → mel
        r'-': ' ',              # hyphen → space: kerja-kerja → kerja kerja
    }),
    jiwer.RemoveMultipleSpaces(),
    jiwer.Strip(),
])


# ─────────────────────────────────────────────────────────────────────────────
# LAZY SINGLETONS
# ─────────────────────────────────────────────────────────────────────────────
_asr_pipeline = None
_lang_detector = None
_silero_vad_model = None
_gemini_client: Optional[genai.Client] = None

def get_whisper():
    """
    Loads SeamlessX/malaysian-faster-whisper-small-v3-ct2.
    Faster-Whisper handles long audio natively with streaming decode.
    """
    global _asr_pipeline
    if _asr_pipeline is None:
        print(f"Loading {MODEL_ID}... (first run only)")
        # Auto-detect GPU/CPU
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # ── Windows fix: disable symlinks ────────────────────────────────────
        model_path = snapshot_download(
            repo_id=MODEL_ID,
            local_dir_use_symlinks=False,
        )

        _asr_pipeline = WhisperModel(
            model_path,
            device=device,
            compute_type="float16" if device == "cuda" else "int8",
            local_files_only=False,
        )
        print("Malaysian Faster-Whisper ready.")
    return _asr_pipeline

def get_language_detector():
    """
    Lightweight multilingual Whisper model
    used ONLY for language detection.
    """
    global _lang_detector

    if _lang_detector is None:
        print("Loading multilingual language detector...")

        device = "cuda" if torch.cuda.is_available() else "cpu"

        _lang_detector = WhisperModel(
            LANG_DETECT_MODEL_ID,
            device=device,
            compute_type="float16" if device == "cuda" else "int8",
        )

        print("Language detector ready.")

    return _lang_detector

def detect_language(audio: np.ndarray):
    """
    Detect dominant language from audio.
    Returns:
        (language_code, probability)
    """

    lang_detector = get_language_detector()

    _, info = lang_detector.transcribe(
        audio,
        beam_size=1,
        vad_filter=False,
    )

    return info.language, info.language_probability

def get_gemini_client() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _gemini_client


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — AUDIO LOADING & VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def load_audio(file_path: str) -> tuple[Optional[np.ndarray], float, Optional[str]]:
    """
    Loads audio file, resamples to 16 kHz mono.
    Returns (audio (or None), duration_seconds, skip_reason (None if valid)).
    """
    audio, _ = librosa.load(file_path, sr=SAMPLE_RATE, mono=True)
    duration = len(audio) / SAMPLE_RATE

    if duration < MIN_AUDIO_SECS:
        return None, duration, f"Audio terlalu pendek ({duration:.1f}s). Minimum: {MIN_AUDIO_SECS}s."

    if duration > MAX_AUDIO_SECS:
        return None, duration, f"Audio terlalu panjang ({duration:.0f}s). Had maksimum: {MAX_AUDIO_SECS}s."

    return audio, duration, None

# ─────────────────────────────────────────────────────────────────────────────
# NO-SPEECH GATE HELPERS (called in score_single_clip before any trait scoring)
# ─────────────────────────────────────────────────────────────────────────────
 
def _detect_no_speech(audio: np.ndarray, transcription: str) -> tuple[bool, str]:
    """
    Returns (no_speech: bool, reason: str).
 
    Two independent checks — EITHER failure triggers the gate:
      1. RMS energy  — catches silent / pure-noise audio
      2. Word count  — catches Whisper hallucinations on silent clips
                       (e.g. returning "Terima kasih." for silence)
    """
    text_lower = transcription.lower().strip()
    normalized_text = re.sub(r'[^\w\s]', ' ', text_lower)
    normalized_text = re.sub(r'\s+', ' ', normalized_text).strip()
    words = re.findall(r'\b\w+\b', normalized_text)
    word_count = len(words)
    
    # ────── Basic Energy Check ───────────────────────────────────────────────
    rms        = float(np.sqrt(np.mean(audio ** 2)))
    if rms < MIN_RMS_ENERGY:
        return True, f"Isyarat audio terlalu lemah (RMS={rms:.4f}). Tiada pertuturan dikesan."


    # ────── Hallucination Filter(YouTube phrases) ────────────────────────────
    for pattern in _HALLUCINATION_PATTERNS:
        normalized_pattern = re.sub(r'[^\w\s]', ' ', pattern)
        normalized_pattern = re.sub(r'\s+', ' ', normalized_pattern).strip()

        if normalized_pattern in normalized_text and word_count < 15:
            return True, "Audio tidak jelas atau terlalu bising. Sila cuba lagi di tempat yang senyap."

    # ────── Repetition/Stuck Detector ─────────────────────────────────────────
    if word_count > 3:
        # Clean text specifically for regex (remove punctuation so "ya, ya" becomes "ya ya")
        clean_text_for_regex = " ".join(words) 
        
        # Regex will catch "ya, ya ya ya" because comma is removed
        consecutive_repeat = re.search(r'(\b\w+\b)( \1){3,}', clean_text_for_regex)
        
        unique_words = set(words)
        repetition_ratio = len(unique_words) / word_count

        if consecutive_repeat:
            return True, f"Transkripsi terlalu pendek. Tiada pertuturan yang mencukupi."
        
        if repetition_ratio < 0.3 and word_count > 10:
            return True, "Kadar pengulangan terlalu tinggi. Sila berikan jawapan yang bermakna."
        
    # ────── Minimum Word Count ─────────────────────────────────────────
    if word_count < MIN_WORD_COUNT:
        return True, f"Transkripsi terlalu pendek. Tiada pertuturan yang mencukupi."
    return False, ""


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — WHISPER TRANSCRIPTION
# ─────────────────────────────────────────────────────────────────────────────

def _get_silero_vad():
    """Lazily loads the standalone Silero VAD model."""
    global _silero_vad_model
    if _silero_vad_model is None:
        _silero_vad_model = load_silero_vad()
    return _silero_vad_model

# ── Split large chunks into max 30s pieces before transcribing ───────────────
MAX_CHUNK_S = 30.0

def _split_chunk(chunk: dict, max_s: float = MAX_CHUNK_S) -> list[dict]:
    """Splits a chunk longer than max_s into equal sub-chunks."""
    duration = chunk["end"] - chunk["start"]
    if duration <= max_s:
        return [chunk]
    
    n        = int(np.ceil(duration / max_s))
    step     = duration / n
    result   = []
    for i in range(n):
        result.append({
            "start": chunk["start"] + i * step,
            "end":   min(chunk["start"] + (i + 1) * step, chunk["end"]),
        })
    return result

def transcribe(audio: np.ndarray) -> tuple[str, list]:
    """
    Transcribes audio using SeamlessX/malaysian-faster-whisper-small-v3-ct2.
    Supports long audio (3–5 min SPM Lisan format).

    Returns
    -------
    transcription  : str — full decoded Malay text
    segments       : list[dict] with keys start, end, text
                     (used by kefasihan scorer for pause detection)
    """
    asr = get_whisper()
    total_audio_s = len(audio) / SAMPLE_RATE

    # ── Silero VAD — detect speech boundaries directly ───────────────
    vad          = _get_silero_vad()
    audio_tensor = torch.from_numpy(audio).float()

    speech_chunks = get_speech_timestamps(
        audio_tensor,
        vad,
        sampling_rate           = SAMPLE_RATE,
        threshold               = 0.05,    # very sensitive — only skips true silence
        min_speech_duration_ms  = 100,
        min_silence_duration_ms = 400,     # merge pauses shorter than 400ms
        speech_pad_ms           = 800,     # pad each chunk by 800ms on both sides
        return_seconds          = True,
    )

    # Fallback: treat entire audio as one chunk if VAD finds nothing
    if not speech_chunks:
        speech_chunks = [{"start": 0.0, "end": total_audio_s}]

    # ── Expand any chunks longer than 30s into sub-chunks ────────────────────
    expanded_chunks = []
    for chunk in speech_chunks:
        expanded_chunks.extend(_split_chunk(chunk))
    speech_chunks = expanded_chunks
    # ─────────────────────────────────────────────────────────────────────────

    covered_vad = sum(c["end"] - c["start"] for c in speech_chunks)
    print(f"[transcribe] Silero VAD: {len(speech_chunks)} chunks | "
          f"{covered_vad:.1f}s / {total_audio_s:.1f}s ({100*covered_vad/total_audio_s:.0f}%)")

    # ── Transcribe each chunk with Faster-Whisper ────────────────────
    segments = []
    texts    = []

    for chunk in speech_chunks:
        start_sample = int(chunk["start"] * SAMPLE_RATE)
        end_sample   = int(min(chunk["end"] * SAMPLE_RATE, len(audio)))
        chunk_audio  = audio[start_sample:end_sample]

        if len(chunk_audio) / SAMPLE_RATE < 0.5:
            continue

        chunk_gen, _ = asr.transcribe(
            chunk_audio,
            beam_size                  = 5,
            condition_on_previous_text = True,
            initial_prompt = _BM_SPELLING_PROMPT + (
                " " + " ".join(texts[-3:]) if texts else ""
            ),
            no_speech_threshold        = 0.99,    # near-maximum; Silero already confirmed speech
            vad_filter                 = False,   # VAD already done by Silero above
            language                   = "ms",
            task                       = "transcribe",
        )

        chunk_texts = []
        chunk_segs  = []

        for seg in chunk_gen:
            text = seg.text.strip()
            if not text:
                continue
            chunk_texts.append(text)
            chunk_segs.append({
                "start": float(chunk["start"] + seg.start),
                "end":   float(chunk["start"] + seg.end),
                "text":  text,
            })

        # ── If Whisper dropped the whole chunk despite Silero confirming speech,
        #    force-include it by transcribing without any confidence filtering ──────
        if not chunk_texts:
            print(f"[transcribe] Whisper dropped chunk {chunk['start']:.1f}s–{chunk['end']:.1f}s, forcing...")
            forced_gen, _ = asr.transcribe(
                chunk_audio,
                beam_size           = 5,
                no_speech_threshold = 1.0,   # never reject
                vad_filter          = False,
                language            = "ms",
                task                = "transcribe",
                initial_prompt      = _BM_SPELLING_PROMPT,
            )
            for seg in forced_gen:
                text = seg.text.strip()
                if not text:
                    continue
                chunk_texts.append(text)
                chunk_segs.append({
                    "start": float(chunk["start"] + seg.start),
                    "end":   float(chunk["start"] + seg.end),
                    "text":  text,
                })

        texts.extend(chunk_texts)
        segments.extend(chunk_segs)

    transcription = " ".join(texts).strip()

    # ── Strip hallucinations from final transcription ─────────────────────────
    transcription = _strip_hallucinations(transcription)
    segments = [
        s for s in segments
        if not any(
            re.search(p, s["text"].lower())
            for p in _HALLUCINATION_PATTERNS
        )
    ]

    # Fallback: treat entire recording as one segment
    if not segments:
        segments = [{
            "start": 0.0,
            "end":   total_audio_s,
            "text":  transcription,
        }]

    # ── DEBUG — print coverage to spot VAD gaps ───────────────────────────────
    if segments:
        covered   = sum(s["end"] - s["start"] for s in segments)
        print(f"[transcribe] {len(segments)} segments | "
              f"covered {covered:.1f}s / {total_audio_s:.1f}s total "
              f"({100*covered/total_audio_s:.0f}%)")
        gaps = [
            (segments[i-1]["end"], segments[i]["start"])
            for i in range(1, len(segments))
            if segments[i]["start"] - segments[i-1]["end"] > 1.0  # gaps > 1s
        ]
        if gaps:
            print(f"[transcribe] large gaps (>1s): {gaps}")
    # ─────────────────────────────────────────────────────────────────────────

    return transcription, segments


# ─────────────────────────────────────────────────────────────────────────────
# TRAIT 1 — GRAMMAR & VOCABULARY # tatabahasa & kosa kata
# SPM criterion: grammatical accuracy + vocabulary range
# ─────────────────────────────────────────────────────────────────────────────

def score_grammar_vocabulary(transcription: str, purity_score: float = 1.0) -> dict:
    """
    Formal vocab count + informal word penalty + affix ratio.
    Returns {score: float (0.0 - 1.0), reason: str (in BM)}
    """
    text_lower = transcription.lower()
    words      = re.findall(r'\b\w+\b', text_lower)
    word_count = len(words) if words else 1

    # Formal vocabulary usage
    formal_count = sum(1 for v in FORMAL_VOCAB if v in text_lower)

    # Informal/colloquial words (penalised in formal SPM context)
    informal_patterns = [
        r'\btak\b', r'\bnak\b', r'\bgak\b', r'\bjer\b', r'\bje\b',
        r'\bokay\b', r'\bok\b', r'\bgitu\b', r'\bgini\b',
        r'\b(aku|kau|hang|ang)\b',
    ]
    informal_count = sum(
        len(re.findall(p, text_lower)) for p in informal_patterns
    )

    # Affixed words — indicator of grammatical competence in BM
    affixed = [
        w for w in words
        if re.match(r'^(ber|men|mem|me|pe|pem|per|ke|ter|di)\w{3,}', w)
        or re.match(r'\w{3,}(kan|an|nya)$', w)
    ]
    affix_ratio = len(affixed) / word_count

    # Sub-scores
    if formal_count >= 5:   formal_score = 1.00
    elif formal_count >= 3: formal_score = 0.80
    elif formal_count >= 1: formal_score = 0.55
    else:                   formal_score = 0.30

    informal_rate = informal_count / word_count
    if informal_rate == 0:      informal_score = 1.00
    elif informal_rate <= 0.02: informal_score = 0.80
    elif informal_rate <= 0.05: informal_score = 0.60
    else:                       informal_score = 0.30

    if affix_ratio >= 0.25:   affix_score = 1.00
    elif affix_ratio >= 0.15: affix_score = 0.80
    elif affix_ratio >= 0.08: affix_score = 0.60
    else:                     affix_score = 0.35

    base_score = round(
        max(0.0, min(1.0,
            (formal_score * 0.40) + (informal_score * 0.35) + (affix_score * 0.25)
        )),
        4,
    )

    penalty = 0.0
    detail_note = ""

    if purity_score >= 0.9:
        # Excellent - No penalty
        penalty = 0.0
    elif purity_score >= 0.7:
        # Minor English/Rojak - Deduct 0.15 (Roughly 1 Band drop)
        penalty = 0.15
        detail_note = " Terdapat sedikit penggunaan bahasa asing."
    elif purity_score >= 0.4:
        # Significant Rojak - Deduct 0.40 (Roughly 2-3 Band drop)
        penalty = 0.40
        detail_note = " Gangguan bahasa asing yang ketara dikesan."
    else:
        # Mostly English/Gibberish - Deduct 0.70 (Forced Band 1/2)
        penalty = 0.70
        detail_note = " Penggunaan bahasa asing yang keterlaluan."

    final_score = round(max(0.0, base_score - penalty), 4)

    band = _score_to_band(final_score)
    reason = SPM_TRAIT_DESCRIPTORS["grammar_vocabulary"][band] + detail_note

    return {"score": final_score, "reason": reason}


# ─────────────────────────────────────────────────────────────────────────────
# TRAIT 2 — PRONUNCIATION # sebutan, intonasi & nada
# SPM criterion: pronunciation accuracy, intonation variety, appropriate tone
# Assessed primarily during bacaan mekanis (mechanical reading)
# ─────────────────────────────────────────────────────────────────────────────

def score_pronunciation(transcription: str, audio: np.ndarray) -> dict:
    text_lower = transcription.lower()
    words = transcription.split()
    
    # ── RULE-BASED PRONUNCIATION ─────────────────────────
    if not words:
        speech_quality_score = 0.3
    else:
        unique_ratio = len(set(words)) / len(words)

        slang_count = sum(
            len(re.findall(pattern, text_lower))
            for pattern in SLANG
        )

        slang_penalty = slang_count * 0.1

        speech_quality_score = (0.7 * unique_ratio) - slang_penalty + 0.3
        speech_quality_score = max(0.0, min(1.0, speech_quality_score))

    # ── ENERGY SCORE ─────────────────────────────────────
    rms = librosa.feature.rms(y=audio)[0]

    if len(rms) == 0:
        energy_score_v = 0.3
    else:
        variation = float(np.std(rms) / (np.mean(rms) + 1e-6))
        energy_score_v = 1.0 - min(variation, 1.0)
        energy_score_v = max(0.0, min(1.0, energy_score_v))

    # ── FINAL FUSION ───────────────────────────────────────────────
    final_score = (
        speech_quality_score * 0.60 +
        energy_score_v * 0.40
    )

    final_score = round(final_score, 4)

    band = _score_to_band(final_score)
    reason = SPM_TRAIT_DESCRIPTORS["pronunciation"][band]
    
    return {
        "score": final_score,
        "reason": reason,
        "metrics": { 
            "rule_based": round(speech_quality_score, 4), 
            "energy": round(energy_score_v, 4), 
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# TRAIT 3 — FLUENCY # kefasihan & kelancaran
# SPM criterion: smooth delivery, minimal hesitation, good speech rate
# ─────────────────────────────────────────────────────────────────────────────

def score_fluency(transcription: str, segments: list, duration: float) -> dict:
    """
    Speech rate (wpm) + pause ratio + filler word rate.
    Returns {score: float (0.0-1.0), reason: str (in BM), metrics: dict}    
    """
    words      = re.findall(r'\b\w+\b', transcription)
    word_count = len(words)
    text_lower = transcription.lower()

    # ── Speech rate (words per minute) ────────────────────────────────────────
    # SPM 3–5 min session; conversational Malay target: ~100–140 wpm
    wpm = float((word_count / duration) * 60) if duration > 0 else 0.0

    if wpm >= 110:   wpm_score = 1.00
    elif wpm >= 85:  wpm_score = 0.85
    elif wpm >= 65:  wpm_score = 0.65
    elif wpm >= 45:  wpm_score = 0.45
    else:            wpm_score = 0.25

    # ── Pause detection (gaps between Whisper segments > 500ms) ──────────────
    pauses           = []
    total_pause_time = 0.0
    for i in range(1, len(segments)):
        gap = segments[i]["start"] - segments[i - 1]["end"]
        if gap > 0.5:
            pauses.append(round(gap, 3))
            total_pause_time += gap

    pause_ratio = float(total_pause_time / duration) if duration > 0 else 0.0

    if pause_ratio <= 0.10:   pause_score = 1.00
    elif pause_ratio <= 0.20: pause_score = 0.80
    elif pause_ratio <= 0.35: pause_score = 0.55
    elif pause_ratio <= 0.50: pause_score = 0.30
    else:                     pause_score = 0.10

    # ── Filler word detection ─────────────────────────────────────────────────
    filler_count = sum(
        len(re.findall(p, text_lower)) for p in BM_FILLERS
    )
    filler_rate = filler_count / word_count if word_count > 0 else 0.0

    if filler_rate <= 0.02:   filler_score = 1.00
    elif filler_rate <= 0.05: filler_score = 0.80
    elif filler_rate <= 0.10: filler_score = 0.55
    else:                     filler_score = 0.30

    # ── Rhythm stability ──────────────────────────────────────────────────────
    if len(segments) < 2:
        rhythm_score_val = 0.6
    else:
        gaps = []
        for i in range(1, len(segments)):
            gap = segments[i]["start"] - segments[i - 1]["end"]
            gaps.append(max(gap, 0))

        if not gaps:
            rhythm_score_val = 0.6
        else:
            variance = float(np.std(gaps))
            rhythm_score_val = 1.0 - min(variance, 1.0)

    rhythm_score_val = round(max(0.0, rhythm_score_val), 4)

    score = round(
        (wpm_score * 0.35) +
        (pause_score * 0.35) +
        (filler_score * 0.20) +
        (rhythm_score_val * 0.10),
        4
    )

    band = _score_to_band(score)
    rubric_header = SPM_TRAIT_DESCRIPTORS["fluency"][band]

    issues = []
    if wpm < 65:
        issues.append(f"kadar pertuturan terlalu perlahan ({wpm:.0f} kata/min)")
    if pause_ratio > 0.30:
        issues.append(f"terlalu banyak jeda ({pause_ratio * 100:.0f}% masa berdiam)")
    if filler_rate > 0.05:
        issues.append(f"terlalu banyak kata pengisi ({filler_count} kali)")

    if not issues:
        reason = f"{rubric_header} Pertuturan anda lancar dan mudah difahami."
    else:
        reason = f"{rubric_header} Kelancaran terjejas kerana {'; '.join(issues)}."
    
    return {
        "score": score,
        "reason": reason,
        "metrics": {
            "wpm":           round(wpm, 1),
            "pause_count":   len(pauses),
            "total_pause_s": round(total_pause_time, 2),
            "pause_ratio":   round(pause_ratio, 4),
            "filler_count":  filler_count,
            "filler_rate":   round(filler_rate, 4),
            "word_count":    word_count,
            "duration_s":    round(duration, 2),
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# ZERO-SCORE BUILDERS
# Used when the no-speech gate fires. All numeric scores = 0.0. No Gemini calls are made.
# ─────────────────────────────────────────────────────────────────────────────
 
_ZERO_REASON = "Tiada pertuturan yang dikesan. Tiada markah diberikan."
 
def _zero_grammar()                -> dict: return {"score": 0.0, "reason": _ZERO_REASON}
def _zero_pronunciation()          -> dict: 
    return {
        "score": 0.0,
        "reason": _ZERO_REASON,
        "metrics": {"rule_based": 0, "energy": 0}
    }
def _zero_fluency(duration: float) -> dict:
    return {
        "score": 0.0,
        "reason": _ZERO_REASON,
        "metrics": {
            "wpm": 0, "pause_count": 0, "total_pause_s": 0.0,
            "pause_ratio": 1.0, "filler_count": 0,
            "filler_rate": 0.0, "word_count": 0, "duration_s": round(duration, 2),
        },
    }
def _zero_ideas(question: dict)    -> dict:
    return {
        "score":         0.0,
        "reason":        _ZERO_REASON,
        "question_id":   question["question_id"],
        "question_text": question["question_text"],
        "category":      question.get("category"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# GEMINI HELPERS
# ─────────────────────────────────────────────────────────────────────────────
 
async def _ask_gemini_json(prompt: str, temperature: float = 0.1) -> dict:
    for attempt in range(3):
        try:
            client   = get_gemini_client()
            response = client.models.generate_content(
                model    = GEMINI_MODEL,
                contents = prompt,
                config   = types.GenerateContentConfig(
                    response_mime_type = "application/json",
                    temperature        = temperature,
                ),
            )
            return json.loads(response.text.strip())
        except Exception as e:
            last_error = e
            wait = 2 * (attempt + 1)   # 2s, 4s, 6s
            print(f"[speaking_scorer] Gemini error (attempt {attempt+1}/3): {last_error} — retrying in {wait}s")
            await asyncio.sleep(wait)
            
    print(f"[speaking_scorer] Gemini error: {last_error}")
    return {}


# ─────────────────────────────────────────────────────────────────────────────
# TRAIT 4 — IDEAS # idea & bermakna
# Scored via Gemini — different rubric per question category:
#   soalan_rangsangan : answer must use information from the stimulus petikan
#   soalan_kbat       : answer must show higher-order thinking on the theme
# ─────────────────────────────────────────────────────────────────────────────

# Combined audit + rangsangan scoring
async def _score_rangsangan(
    transcription: str,
    stimulus_text: str,
    question_text: str,
) -> tuple[float, str]:
    """Scale 0-5 → 0.0-1.0. Returns (score, reason)."""
    prompt = f"""
Anda adalah pemeriksa SPM Bahasa Melayu yang menilai ujian lisan pelajar.
 
Bahan rangsangan (petikan):
\"\"\"{stimulus_text}\"\"\"
 
Soalan berdasarkan bahan rangsangan:
\"\"\"{question_text}\"\"\"
 
Jawapan lisan pelajar (transkripsi):
\"\"\"{transcription}\"\"\"
 
TUGAS:
    1. Tentukan jika jawapan adalah "OFF-TOPIC" (true/false).
       Jawab "true" HANYA jika jawapan:
       - Tidak menyentuh topik soalan sama sekali.
       - Hanya mengandungi bunyi, suku kata, atau perkataan tidak bermakna (gibberish).
       - Jelas bukan respons kepada soalan ini.
       Jawab "false" jika jawapan pelajar SEKURANG-KURANGNYA ada kaitan dengan topik
       soalan, walaupun jawapan itu lemah, tidak lengkap, atau tidak tepat.

    2. Beri "PURITY_SCORE" (0.0 - 1.0) untuk penggunaan Bahasa Melayu:
       - 1.0: Bahasa Melayu murni/formal sepenuhnya.
       - 0.7 - 0.9: Bahasa Melayu dengan sedikit istilah Inggeris yang perlu.
       - 0.4 - 0.6: Bahasa Melayu campur aduk (Bahasa Rojak/Manglish).
       - 0.0 - 0.3: Sepenuhnya bahasa asing atau bunyi tidak bermakna.

    3. Nilai sama ada jawapan lisan pelajar menjawab soalan berdasarkan bahan rangsangan.
        Skala markah kesesuaian jawapan (0-5):
        5 - Jawapan sepenuhnya menjawab soalan dengan maklumat daripada petikan
        4 - Jawapan kebanyakannya betul berdasarkan petikan, sedikit tidak tepat
        3 - Jawapan sebahagiannya menjawab soalan tetapi tidak lengkap
        2 - Jawapan ada kaitan dengan petikan tetapi tidak menjawab soalan
        1 - Jawapan hampir tidak menjawab soalan atau salah fakta
        0 - Jawapan langsung tidak berkaitan atau pelajar tidak menjawab
 
Kembalikan JSON dengan format berikut SAHAJA:
{{
  "off_topic": <true/false>,
  "purity_score": <float>,
  "relevance_score": <integer 0-5>,
  "reason": "<Berikan ulasan spesifik tentang kandungan jawapan pelajar berbanding petikan.
            Mula terus dengan analisis kandungan, jangan ulangi tahap pencapaian, 
            sebaliknya jelaskan maklumat apa yang tepat atau apa yang tertinggal dalam Bahasa Melayu.>"
}}
"""
    data   = await _ask_gemini_json(prompt)
    try:
        score = max(0, min(5, int(data.get("relevance_score", 2))))
    except (TypeError, ValueError):
        score = 2   # default to mid-range if unparseable

    return {
        "off_topic":       bool(data.get("off_topic", False)),
        "purity_score":    float(data.get("purity_score", 1.0)),
        "relevance_score": round(score / 5.0, 4),
        "reason":          data.get("reason", "Kesesuaian jawapan tidak dapat dinilai."),
    }
 
 
async def _score_kbat(transcription: str, question_text: str) -> tuple[float, str]:
    """Scale 0-5 → 0.0-1.0. Returns (score, reason)."""
    prompt = f"""
Anda adalah pemeriksa SPM Bahasa Melayu yang menilai ujian lisan pelajar.
 
Soalan KBAT:
\"\"\"{question_text}\"\"\"
 
Jawapan lisan pelajar (transkripsi):
\"\"\"{transcription}\"\"\"
 

TUGAS:
    1. Tentukan jika jawapan adalah "OFF-TOPIC" (true/false).
       Jawab "true" HANYA jika jawapan:
       - Tidak menyentuh topik soalan sama sekali.
       - Hanya mengandungi bunyi, suku kata, atau perkataan tidak bermakna (gibberish).
       - Jelas bukan respons kepada soalan ini.
       Jawab "false" jika jawapan pelajar SEKURANG-KURANGNYA ada kaitan dengan topik
       soalan, walaupun jawapan itu lemah, tidak lengkap, atau tidak tepat.

    2. Beri "PURITY_SCORE" (0.0 - 1.0) untuk penggunaan Bahasa Melayu:
       - 1.0: Bahasa Melayu murni/formal sepenuhnya.
       - 0.7 - 0.9: Bahasa Melayu dengan sedikit istilah Inggeris yang perlu.
       - 0.4 - 0.6: Bahasa Melayu campur aduk (Bahasa Rojak/Manglish).
       - 0.0 - 0.3: Sepenuhnya bahasa asing atau bunyi tidak bermakna.

    3.Nilai sama ada jawapan lisan pelajar menunjukkan pemikiran aras tinggi (KBAT) dalam menjawab soalan berikut.
      Skala markah KBAT (0-5):
        5 - Jawapan menunjukkan pemikiran kritis yang mendalam; hujah dan contoh kukuh
        4 - Jawapan menunjukkan pemikiran kritis yang baik dengan hujah munasabah
        3 - Jawapan ada unsur KBAT tetapi hujah tidak mencukupi atau tidak dihuraikan
        2 - Jawapan di peringkat pemahaman sahaja; tiada analisis atau penilaian
        1 - Jawapan sangat ringkas atau hanya mengulang soalan
        0 - Pelajar tidak menjawab atau jawapan tidak berkaitan
 
Kembalikan JSON dengan format berikut SAHAJA:
{{
  "off_topic": <true/false>,
  "purity_score": <float>,
  "relevance_score": <integer 0-5>,
  "reason": "<Jelaskan secara spesifik kekuatan atau kelemahan hujah pelajar.
            Mula terus dengan ulasan logik (Contoh: Adakah hujah itu logik? 
            Adakah contoh yang diberikan relevan?)
            Jangan gunakan ayat umum seperti 'jawapan baik'.>"
}}
"""
    data   = await _ask_gemini_json(prompt)
    try:
        score = max(0, min(5, int(data.get("relevance_score", 2))))
    except (TypeError, ValueError):
        score = 2   # default to mid-range if unparseable

    return {
        "off_topic": bool(data.get("off_topic", False)),
        "purity_score": float(data.get("purity_score", 1.0)),
        "relevance_score": round(score / 5.0, 4),
        "reason": data.get("reason", "Kesesuaian jawapan tidak dapat dinilai.")
    }


# ─────────────────────────────────────────────────────────────────────────────
# SINGLE CLIP SCORER
# ─────────────────────────────────────────────────────────────────────────────
 
async def score_single_clip(
    file_path:      str,
    clip_id:        str,                   # "bacaan" | "r1" | "r2" | "k1" | "k2"
    stimulus_text:  str,
    question:       Optional[dict] = None, # {question_id, question_text, category}
    reference_text: Optional[str]  = None, # ONLY passed for "bacaan" clip (= stimulus_text)
) -> dict:
    """
    Scores one audio clip. Returns a per-clip dict with nested trait dicts.

    Return shape
    ────────────
    {
        clip_id:            str,
        transcription:      str,
        no_speech:          bool,
        no_speech_reason:   str,
        grammar_vocabulary: {score, reason},
        pronunciation:      {score, reason, metrics},
        fluency:            {score, reason, metrics},
        ideas:              {score, reason, question_id, question_text, category} | None
        wer:                float | None,
    }
    """
    audio, duration, skip_reason = load_audio(file_path)

    # ── File-level rejection (too short / too long) ───────────────────────────
    if audio is None:
        return {
            "clip_id": clip_id,
            "transcription": "",
            "no_speech": True,
            "no_speech_reason": skip_reason,
            "grammar_vocabulary": _zero_grammar(),
            "pronunciation": _zero_pronunciation(),
            "fluency": _zero_fluency(duration),
            "ideas": _zero_ideas(question) if question else None,
            "wer": None,
        }
    
    audio_for_lang = audio[: SAMPLE_RATE * LANG_DETECT_SECS]
    detected_lang, lang_prob = detect_language(audio_for_lang)

    transcription, segments = transcribe(audio)

    # ── LANGUAGE GATE ─────────────────────────────────────
    allowed_languages = ["ms", "id"] # Malay (ms) and Indonesian (id) are allowed as they are always mixed up

    if detected_lang not in allowed_languages and lang_prob > 0.80:
        lang_name = LANG_NAME_MAP.get(detected_lang, detected_lang)

        return {
            "clip_id": clip_id,
            "transcription": transcription,
            "no_speech": True,
            "no_speech_reason": (
                f"Bahasa dikesan sebagai '{lang_name}', "
                "jawapan mesti dalam Bahasa Melayu."
            ),
            "grammar_vocabulary": _zero_grammar(),
            "pronunciation": _zero_pronunciation(),
            "fluency": _zero_fluency(duration),
            "ideas": _zero_ideas(question) if question else None,
            "wer": None,
        }

    # ── NO-SPEECH GATE ────────────────────────────────────────────────────────
    # Scores are set to 0.0 for silence/noise.
    no_speech, no_speech_reason = _detect_no_speech(audio, transcription)
 
    if no_speech:
        return {
            "clip_id":            clip_id,
            "transcription":      transcription,
            "no_speech":          True,
            "no_speech_reason":   no_speech_reason,
            "grammar_vocabulary": _zero_grammar(),
            "pronunciation":      _zero_pronunciation(),
            "fluency":            _zero_fluency(duration),
            "ideas":              _zero_ideas(question) if question else None,
            "wer":                None,
        }
 
    # ── WER — bacaan clip only, computed after speech confirmed ───────────────    
    wer_value = None
    if clip_id == "bacaan" and reference_text:
        wer_strict = compute_wer(reference_text, transcription)
        wer_lenient = compute_wer_spoken_only(reference_text, transcription)
        wer_completeness = _compute_completeness(reference_text, transcription)
        wer_value        = {
            "strict": wer_strict,       # skipped words/sentences
            "spoken_only":  wer_lenient,      # mispronunciation only
            "completeness": wer_completeness,            
        }
    
    # ── AUDIT ─────────────────────────────────────────────────────────────────
    purity_score = 1.0 # Default for non-question clips (like reading)
    is_off_topic = False
 
    # ── TRAIT 4 — ideas (question clips only) ─────────────────────────────────
    ideas_result = None
    if question is not None:
        category = question.get("category", "soalan_rangsangan")
 
        if category == "soalan_rangsangan":
            gemini_result = await _score_rangsangan(
                transcription = transcription,
                stimulus_text = stimulus_text,
                question_text = question["question_text"],
            )
        else:
            gemini_result = await _score_kbat(
                transcription = transcription,
                question_text = question["question_text"],
            )

        purity_score = gemini_result["purity_score"]
        is_off_topic = gemini_result["off_topic"]
        ai_reason    = gemini_result["reason"]

        # Hard gate: off-topic or mostly foreign language / gibberish
        if is_off_topic or purity_score < 0.2:
            return {
                "clip_id": clip_id,
                "transcription": transcription,
                "no_speech": False,
                "no_speech_reason": None,

                "grammar_vocabulary": _zero_grammar(),
                "pronunciation": _zero_pronunciation(),
                "fluency": _zero_fluency(duration),
                "ideas": {
                    "score": 0.0,
                    "reason": gemini_result["reason"],
                    "question_id": question["question_id"] if question else None,
                    "question_text": question["question_text"] if question else None,
                    "category": question.get("category") if question else None,
                } if question else None,

                "wer": None,
            }
        else:
            ideas_score = gemini_result["relevance_score"]

        # Convert raw score (0.0-1.0) to SPM Band (1-6)
        ideas_band = _score_to_band(ideas_score)

        # Fetch the Official Rubric Descriptor
        rubric_header = SPM_TRAIT_DESCRIPTORS["ideas"][ideas_band]

        # COMBINE THEM: Rubric + Specific AI Feedback
        # This ensures no "overlap" but rather "context"
        ideas_result = {
            "score":         round(ideas_score, 4),
            "reason":        f"{rubric_header} {ai_reason}",
            "question_id":   question["question_id"],
            "question_text": question["question_text"],
            "category":      category,
        }
 
    # ── TRAITS 1-3 (all clips that pass the gate) ─────────────────────────────
    grammar_result = score_grammar_vocabulary(transcription, purity_score)
    pron_result    = score_pronunciation(transcription = transcription, audio = audio)
    fluency_result = score_fluency(transcription, segments, duration)

    return {
        "clip_id":            clip_id,
        "transcription":      transcription,
        "no_speech":          False,
        "no_speech_reason":   None,
        "grammar_vocabulary": grammar_result,
        "pronunciation":      pron_result,
        "fluency":            fluency_result,
        "ideas":              ideas_result,
        "wer":                wer_value,
    }
 
 
# ─────────────────────────────────────────────────────────────────────────────
# BAND SCORE CALCULATION
# ─────────────────────────────────────────────────────────────────────────────
 
def _score_to_band(score_0_to_1: float) -> int:
    if score_0_to_1   >= 0.90: return 6
    elif score_0_to_1 >= 0.70: return 5
    elif score_0_to_1 >= 0.60: return 4
    elif score_0_to_1 >= 0.40: return 3
    elif score_0_to_1 >= 0.20: return 2
    else:                      return 1
 
 
def calculate_band(
    grammar_score: float,
    pronunciation_score: float,
    fluency_score: float,
    ideas_score: float,
) -> tuple[int, str]:
    combined     = round((grammar_score + pronunciation_score + fluency_score + ideas_score) / 4, 4)
    overall_band = _score_to_band(combined)
    return overall_band, SPM_BAND_DESCRIPTORS[overall_band]

 
# ─────────────────────────────────────────────────────────────────────────────
# WER HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _strip_hallucinations(text: str) -> str:
    """Remove known Whisper hallucination phrases before WER computation."""
    text = text.lower()
    for pattern in _HALLUCINATION_PATTERNS:
        text = re.sub(pattern, '', text)
    return text.strip()

def compute_wer(reference: str, hypothesis: str) -> float:
    """
    Word Error Rate between ground-truth (reference) and Whisper hypothesis.
    For bacaan mekanis:
        reference  = stimulus_text  (the printed text the student was asked to read)
        hypothesis = Whisper transcription of the student's reading
    A WER of 0.0 means the student read every word exactly as written.
    A WER of 1.0 means no words matched at all.
    Target for a good reader: WER ≤ 0.15 (≤ 15% of words differ).
    """
    if isinstance(reference, list):
        reference = " ".join(reference)

    if isinstance(hypothesis, list):
        hypothesis = " ".join(hypothesis)

    hypothesis = _strip_hallucinations(hypothesis)
    reference = str(reference)
    hypothesis = str(hypothesis)

    ref = WER_TRANSFORM(reference)
    hyp = WER_TRANSFORM(hypothesis)

    return float(round(jiwer.wer(ref, hyp), 2))

def compute_wer_spoken_only(reference: str, hypothesis: str) -> float:
    """
    Lenient WER that only penalizes words the student actually attempted.
    Skipped reference words (omissions) are excluded from the denominator,
    so only substitutions and insertions are counted.

    Use alongside compute_wer (strict) — this surfaces pronunciation accuracy
    while compute_wer surfaces reading completeness.
    """
    if isinstance(reference, list):
        reference = " ".join(reference)
    if isinstance(hypothesis, list):
        hypothesis = " ".join(hypothesis)

    hypothesis = _strip_hallucinations(hypothesis)
    reference = str(reference)
    hypothesis = str(hypothesis)

    ref_words = WER_TRANSFORM(reference).split()
    hyp_words = WER_TRANSFORM(hypothesis).split()

    if not ref_words or not hyp_words:
        return 1.0

    # Align ref and hyp word sequences
    matcher = SequenceMatcher(None, ref_words, hyp_words, autojunk=False)

    substitutions = 0
    insertions    = 0
    attempted     = 0   # ref words the student actually touched (matched or substituted)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        ref_len = i2 - i1
        hyp_len = j2 - j1

        if tag == 'equal':
            attempted += ref_len           # correctly read words

        elif tag == 'replace':
            # Student said something for these ref words — counts as attempted
            attempted     += ref_len
            substitutions += max(ref_len, hyp_len)  # penalize length mismatch too

        elif tag == 'insert':
            # Whisper hallucinated extra words — pure insertion penalty
            insertions += hyp_len

        elif tag == 'delete':
            # Student skipped these ref words — NOT counted in denominator
            pass

    if attempted == 0:
        return 0.0

    errors = substitutions + insertions
    return float(round(min(errors / attempted, 1.0), 2))

def _compute_completeness(reference: str, hypothesis: str) -> float:
    """
    Ratio of reference words the student actually attempted (0.0 - 1.0).
    1.0 = read everything, 0.7 = skipped ~30% of the passage.
    Used alongside wer_spoken_only to flag incomplete readings separately.
    """
    ref_words = WER_TRANSFORM(str(reference)).split()
    hyp_words = WER_TRANSFORM(str(hypothesis)).split()

    if not ref_words:
        return 0.0

    matcher = SequenceMatcher(None, ref_words, hyp_words, autojunk=False)

    attempted = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():

        ref_len = i2 - i1

        if tag == "equal":
            attempted += ref_len

        elif tag == "replace":
            attempted += ref_len

        # delete = skipped words → not counted
        # insert = extra words → ignored

    completeness = attempted / len(ref_words)
    return float(round(completeness, 2))


# ─────────────────────────────────────────────────────────────────────────────
# MAIN — score_speaking
# ─────────────────────────────────────────────────────────────────────────────
 
async def score_speaking(
    path_bacaan:       str,
    path_r1:           str,
    path_r2:           str,
    path_k1:           str,
    path_k2:           str,
    stimulus_text:     str,
    soalan_rangsangan: List[dict],   # [{question_id, question_text}]  len=2
    soalan_kbat:       List[dict],   # [{question_id, question_text}]  len=2
    reference_texts:   dict = {},    # kept for eval/testing; ignored in normal use
) -> dict:
    """
    Full SPM Paper 3 Lisan assessment across 5 clips.
 
    Aggregation (simple average across all clips, including zero-scored ones):
      grammar_vocabulary  → average of all 5 clip scores
      pronunciation       → average of all 5 clip scores
      fluency             → average of all 5 clip scores
      ideas               → one score per question clip (4 entries in per_question)
 
    Return shape
    ────────────
    {
        clips: [
            {
                clip_id, transcription, no_speech, no_speech_reason,
                grammar_vocabulary: {score, reason},
                pronunciation:      {score, reason, metrics},
                fluency:            {score, reason, metrics},
                ideas:              {score, reason, question_id, question_text, category} | None,
                wer:                float | None,
            },
            ...  # ordered: bacaan, r1, r2, k1, k2
        ],
 
        grammar_vocabulary: {
            score,          ← overall average
            reason,         ← from worst-scoring clip
            per_clip: [     ← one entry per clip
                {clip_id, score, reason},
                ...
            ],
        },
        pronunciation: {
            score, reason,
            per_clip: [{clip_id, score, reason, metrics}, ...],
        },
        fluency: {
            score, reason,
            per_clip: [{clip_id, score, reason, metrics}, ...],
        },
        ideas: {
            score,          ← average across 4 question clips
            reason,         ← from worst-scoring question
            per_question: [ ← one entry per question clip
                {clip_id, question_id, question_text, category, score, reason},
                ...
            ],
        },
        bacaan_wer:         float | None,   ← WER for bacaan clip only
        total_score:        float,
        overall_band:       int,
        overall_descriptor: str,
        processing_time_s:  float,
    }
    """
    t0 = time.time()

    r1_q = {**soalan_rangsangan[0], "category": "soalan_rangsangan"}
    r2_q = {**soalan_rangsangan[1], "category": "soalan_rangsangan"}
    k1_q = {**soalan_kbat[0],       "category": "soalan_kbat"}
    k2_q = {**soalan_kbat[1],       "category": "soalan_kbat"}

    bacaan_reference = reference_texts.get("bacaan") or stimulus_text

    clip_jobs = [
        ("bacaan", path_bacaan, None, bacaan_reference),
        ("r1",     path_r1,     r1_q, None),
        ("r2",     path_r2,     r2_q, None),
        ("k1",     path_k1,     k1_q, None),
        ("k2",     path_k2,     k2_q, None),
    ]
 
    # Score each clip sequentially (Whisper is not thread-safe)
    clip_results = []
    for clip_id, file_path, question, ref_text in clip_jobs:
        result = await score_single_clip(
            file_path      = file_path,
            clip_id        = clip_id,
            stimulus_text  = stimulus_text,
            question       = question,
            reference_text = ref_text,
        )
        clip_results.append(result)
 
    # ── Build per-clip breakdowns ──────────────────────────────────────────────
    grammar_per_clip = [
        {
            "clip_id": c["clip_id"],
            "score":   c["grammar_vocabulary"]["score"],
            "reason":  c["grammar_vocabulary"]["reason"],
        }
        for c in clip_results
    ]
    pron_per_clip = [
        {
            "clip_id":       c["clip_id"],
            "score":         c["pronunciation"]["score"],
            "reason":        c["pronunciation"]["reason"],
            "metrics":       c["pronunciation"]["metrics"],
        }
        for c in clip_results
    ]
    fluency_per_clip = [
        {
            "clip_id": c["clip_id"],
            "score":   c["fluency"]["score"],
            "reason":  c["fluency"]["reason"],
            "metrics": c["fluency"]["metrics"],
        }
        for c in clip_results
    ]
    ideas_per_question = [
        {
            "clip_id":       c["clip_id"],
            "question_id":   c["ideas"]["question_id"],
            "question_text": c["ideas"]["question_text"],
            "category":      c["ideas"]["category"],
            "score":         c["ideas"]["score"],
            "reason":        c["ideas"]["reason"],
        }
        for c in clip_results
        if c.get("ideas") is not None
    ]
 
    # ── Aggregate scores ───────────────────────────────────────────────────────
    def _avg(entries: list) -> float:
        vals = [e["score"] for e in entries]
        return float(round(sum(vals) / len(vals), 4)) if vals else 0.0
 
    def get_trait_descriptor(trait: str, avg_score: float) -> str:
        band = _score_to_band(avg_score)
        return SPM_TRAIT_DESCRIPTORS[trait][band]
 
    agg_grammar_score = _avg(grammar_per_clip)
    agg_pron_score    = _avg(pron_per_clip)
    agg_fluency_score = _avg(fluency_per_clip)
    agg_ideas_score   = _avg(ideas_per_question)
 
    total_score = float(round((agg_grammar_score + agg_pron_score + agg_fluency_score + agg_ideas_score) / 4, 2))

    # ── Overall band ───────────────────────────────────────────────────────────
    overall_band, overall_descriptor = calculate_band(
        agg_grammar_score, agg_pron_score, agg_fluency_score, agg_ideas_score
    )

    # ── Extract bacaan WER for top-level shortcut ─────────────────────────────
    bacaan_clip = next((c for c in clip_results if c["clip_id"] == "bacaan"), None)
    bacaan_wer  = bacaan_clip["wer"] if bacaan_clip else None

    return {
        "clips": clip_results,
 
        "grammar_vocabulary": {
            "score": round(agg_grammar_score, 2),
            "reason":         get_trait_descriptor("grammar_vocabulary", agg_grammar_score),
            "per_clip":       grammar_per_clip,
        },
        "pronunciation": {
            "score": round(agg_pron_score, 2),
            "reason":          get_trait_descriptor("pronunciation", agg_pron_score),
            "per_clip":       pron_per_clip,
        },
        "fluency": {
            "score": round(agg_fluency_score, 2),
            "reason":         get_trait_descriptor("fluency", agg_fluency_score),
            "per_clip":       fluency_per_clip,
        },
        "ideas": {
            "score": round(agg_ideas_score, 2),
            "reason":         get_trait_descriptor("ideas", agg_ideas_score),
            "per_question":   ideas_per_question,
        },
 
        "bacaan_wer":         bacaan_wer,   # float (0.0–1.0+) or None if gate fired
        "total_score":        total_score,
        "overall_band":       overall_band,
        "overall_descriptor": overall_descriptor,
        "processing_time_s":  round(time.time() - t0, 2),
    }
