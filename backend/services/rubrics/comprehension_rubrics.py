"""
spm_rubrics.py

Centralised SPM Bahasa Melayu rubric store.

WHY THIS EXISTS (agentic reasoning):
  Previously, rubric criteria were scattered as plain text inside prompt
  strings in comprehension_service.py. This meant:
    - Updating a rubric = hunting through prompt strings
    - No validation that the model used the correct rubric
    - No way to version or swap rubrics per exam year

  As a tool, the agent explicitly CALLS get_spm_rubric() before scoring.
  This makes the rubric selection visible in logs, testable in isolation,
  and easy to update without touching prompt logic.
"""

from dataclasses import dataclass


@dataclass
class SPMRubric:
    quiz_type:     str
    difficulty:    str
    max_score:     int
    scoring_guide: str        # injected directly into the prompt


# ── Rubric definitions ────────────────────────────────────────────────────────

_RUBRICS: dict[tuple[str, str], SPMRubric] = {

    # ── golongan_kata ─────────────────────────────────────────────────────────
    ("golongan_kata", "low"): SPMRubric(
        quiz_type="golongan_kata", difficulty="low", max_score=1,
        scoring_guide=(
            "Markah penuh (1): Golongan kata yang dipilih adalah tepat.\n"
            "Tiada markah (0): Golongan kata salah atau tiada jawapan."
        ),
    ),
    ("golongan_kata", "medium"): SPMRubric(
        quiz_type="golongan_kata", difficulty="medium", max_score=1,
        scoring_guide=(
            "Markah penuh (1): Golongan kata tepat dan pelajar dapat membezakan "
            "antara kata nama am dan kata nama khas jika berkaitan.\n"
            "Tiada markah (0): Golongan kata salah."
        ),
    ),
    ("golongan_kata", "high"): SPMRubric(
        quiz_type="golongan_kata", difficulty="high", max_score=1,
        scoring_guide=(
            "Markah penuh (1): Golongan kata tepat untuk perkataan berimbuhan atau "
            "kata majmuk yang memerlukan analisis morfologi.\n"
            "Tiada markah (0): Golongan kata salah."
        ),
    ),

    # ── bina_ayat ─────────────────────────────────────────────────────────────
    ("bina_ayat", "low"): SPMRubric(
        quiz_type="bina_ayat", difficulty="low", max_score=1,
        scoring_guide=(
            "Markah penuh (1): Ayat lengkap, gramatis, dan perkataan digunakan dengan betul.\n"
            "Tiada markah (0): Ayat tidak lengkap, tidak gramatis, atau perkataan "
            "digunakan dalam konteks yang salah."
        ),
    ),
    ("bina_ayat", "medium"): SPMRubric(
        quiz_type="bina_ayat", difficulty="medium", max_score=1,
        scoring_guide=(
            "Markah penuh (1): Ayat lengkap, gramatis, menggunakan perkataan dengan "
            "tepat dan menunjukkan pemahaman makna kontekstual.\n"
            "Tiada markah (0): Ayat salah dari segi tatabahasa atau makna."
        ),
    ),
    ("bina_ayat", "high"): SPMRubric(
        quiz_type="bina_ayat", difficulty="high", max_score=1,
        scoring_guide=(
            "Markah penuh (1): Ayat kompleks, gramatis, perkataan digunakan dengan "
            "tepat dalam konteks yang menunjukkan penguasaan bahasa tinggi.\n"
            "Tiada markah (0): Ayat tidak menepati kriteria di atas."
        ),
    ),

    # ── jenis_ayat ────────────────────────────────────────────────────────────
    ("jenis_ayat", "low"): SPMRubric(
        quiz_type="jenis_ayat", difficulty="low", max_score=1,
        scoring_guide=(
            "Markah penuh (1): Jenis ayat dikenal pasti atau penukaran ayat dilakukan "
            "dengan betul.\n"
            "Tiada markah (0): Jawapan salah atau tiada jawapan."
        ),
    ),
    ("jenis_ayat", "medium"): SPMRubric(
        quiz_type="jenis_ayat", difficulty="medium", max_score=1,
        scoring_guide=(
            "Markah penuh (1): Penukaran ayat (aktif/pasif atau cakap langsung/pindah) "
            "dilakukan dengan tepat tanpa ralat tatabahasa.\n"
            "Tiada markah (0): Penukaran tidak tepat atau ada ralat tatabahasa."
        ),
    ),
    ("jenis_ayat", "high"): SPMRubric(
        quiz_type="jenis_ayat", difficulty="high", max_score=1,
        scoring_guide=(
            "Markah penuh (1): Penukaran atau pembinaan ayat kompleks dilakukan dengan "
            "tepat, menunjukkan penguasaan struktur ayat majmuk.\n"
            "Tiada markah (0): Jawapan tidak menepati kriteria."
        ),
    ),

    # ── kesalahan_bahasa ──────────────────────────────────────────────────────
    ("kesalahan_bahasa", "low"): SPMRubric(
        quiz_type="kesalahan_bahasa", difficulty="low", max_score=1,
        scoring_guide=(
            "Markah penuh (1): Kesalahan ejaan atau tatabahasa dikenal pasti dengan tepat "
            "dan pembetulan perkataan yang betul diberikan.\n"
            "Jawapan boleh dalam bentuk: perkataan salah + pembetulan.\n"
            "Tiada markah (0): Kesalahan tidak dikenal pasti atau pembetulan salah."
        ),
    ),
    ("kesalahan_bahasa", "medium"): SPMRubric(
        quiz_type="kesalahan_bahasa", difficulty="medium", max_score=1,
        scoring_guide=(
            "Markah penuh (1): Kesalahan penggunaan kata atau imbuhan dikenal pasti dengan tepat "
            "dan pembetulan diberikan dalam bentuk perkataan.\n"
            "Jawapan tidak perlu menulis semula ayat penuh.\n"
            "Tiada markah (0): Jawapan tidak tepat atau tidak lengkap."
        ),
    ),
    ("kesalahan_bahasa", "high"): SPMRubric(
        quiz_type="kesalahan_bahasa", difficulty="high", max_score=1,
        scoring_guide=(
            "Markah penuh (1): Kesalahan sintaksis atau penggunaan kata dikenal pasti dengan tepat "
            "dan pembetulan perkataan diberikan dengan betul.\n"
            "Jawapan hanya perlu: kesalahan + pembetulan, bukan ayat penuh.\n"
            "Tiada markah (0): Jawapan tidak tepat atau tidak lengkap."
        ),
    ),

    # ── pemahaman ─────────────────────────────────────────────────────────────
    # Pemahaman uses a fixed 4-question format regardless of difficulty,
    # so only one rubric entry is needed (difficulty="standard").
    ("pemahaman", "standard"): SPMRubric(
        quiz_type="pemahaman", difficulty="standard", max_score=13,
        scoring_guide=(
            "Soalan 1 [2 markah]:\n"
            "  - 1 markah: makna rangkai kata yang tepat\n"
            "  - 1 markah: penggunaan bahasa yang betul\n\n"
            "Soalan 2 [3 markah]:\n"
            "  - 1 markah: isi berdasarkan Bahan 1\n"
            "  - 1 markah: isi berdasarkan Bahan 2\n"
            "  - 1 markah: penggunaan bahasa\n\n"
            "Soalan 3 [4 markah]:\n"
            "  - 3 markah: isi jawapan KBAT yang lengkap\n"
            "  - 1 markah: penggunaan bahasa\n\n"
            "Soalan 4 [4 markah]:\n"
            "  - 3 markah: isi jawapan KBAT yang lengkap\n"
            "  - 1 markah: penggunaan bahasa"
        ),
    ),

    # ── rumusan ───────────────────────────────────────────────────────────────
    ("rumusan", "standard"): SPMRubric(
        quiz_type="rumusan", difficulty="standard", max_score=30,
        scoring_guide=(
        "ISI [20 markah] — merangkumi pendahuluan, isi dan kesimpulan:\n"
        "  Pendahuluan [2 markah]:\n"
        "    - 2 markah: menyebut KEDUA-DUA fokus dengan tepat\n"
        "    - 1 markah: menyebut SATU fokus sahaja\n\n"
        "  Isi [16 markah]:\n"
        "    - 2 markah bagi setiap isi yang tepat dan lengkap\n"
        "    - Maksimum 8 isi diterima\n"
        "    - Calon MESTI mengambil sekurang-kurangnya 1 isi daripada "
            "setiap fokus DAN daripada setiap bahan\n"
        "    - Periksa setakat 120 patah perkataan sahaja\n\n"
        "  Kesimpulan [2 markah]:\n"
        "    - 2 markah: kesimpulan lengkap merangkumi kedua-dua fokus\n"
        "    - 1 markah: kesimpulan separa (satu fokus sahaja)\n\n"
        "Panduan mengira perkataan (setiap item ini = 1 perkataan):\n"
        "  nama khas, perkataan berganda, kata sendi (di/ke), tarikh, "
        "angka, gelaran, penanda wacana\n\n"
        "BAHASA [10 markah] — dinilai secara holistik:\n"
        "  Cemerlang (8-10): kesinambungan sangat baik, sangat gramatis, "
            "kosa kata luas, pengolahan sangat menarik\n"
        "  Baik      (5-7):  kesinambungan baik, masih gramatis, "
            "kosa kata masih luas, pengolahan masih menarik\n"
        "  Sederhana (3-4):  kesinambungan kurang baik, kurang gramatis, "
            "kosa kata kurang luas\n"
        "  Lemah     (1-2):  serba kekurangan / tidak memuaskan\n\n"
        "Peraturan khas bahasa:\n"
        "  - Jawab dalam bentuk poin/fakta → bahasa automatik peringkat Lemah\n"
        "  - Markah isi ≤ 5 tetapi bahasa sangat baik → markah bahasa maksimum 5\n"
        "  - Disalin bulat-bulat perkataan demi perkataan → bahasa = 0\n"
        "  - Rumusan kurang 120 patah perkataan → bahasa dinilai seperti biasa"
        ),
    ),
}

# Fallback: if an exact (quiz_type, difficulty) pair is not in the store,
# return the "medium" or "standard" variant for that quiz type.
_FALLBACK_DIFFICULTY: dict[str, str] = {
    "golongan_kata":    "medium",
    "bina_ayat":        "medium",
    "jenis_ayat":       "medium",
    "kesalahan_bahasa": "medium",
    "pemahaman":        "standard",
    "rumusan":          "standard",
}


# ── Public tool function ──────────────────────────────────────────────────────

def get_comprehension_rubrics(quiz_type: str, difficulty: str = "medium") -> SPMRubric:
    """
    Retrieve the SPM rubric for a given quiz type and difficulty.

    This is called as a TOOL by the scoring agents in comprehension_service.py
    before building the scoring prompt, ensuring rubric criteria are always
    fetched explicitly rather than hardcoded into prompt strings.

    Args:
        quiz_type:  One of golongan_kata, bina_ayat, jenis_ayat,
                    kesalahan_bahasa, pemahaman, rumusan.
        difficulty: low / medium / high / standard.
                    Pemahaman and rumusan always use "standard".

    Returns:
        SPMRubric dataclass with scoring_guide ready to inject into a prompt.

    Raises:
        ValueError: if quiz_type is not recognised.
    """
    valid_types = {
        "golongan_kata", "bina_ayat", "jenis_ayat",
        "kesalahan_bahasa", "pemahaman", "rumusan",
    }
    if quiz_type not in valid_types:
        raise ValueError(
            f"Unknown quiz_type '{quiz_type}'. "
            f"Valid types: {sorted(valid_types)}"
        )

    # Normalise difficulty for types that don't use low/medium/high
    if quiz_type in ("pemahaman", "rumusan"):
        difficulty = "standard"

    rubric = _RUBRICS.get((quiz_type, difficulty))

    if rubric is None:
        # Graceful fallback instead of KeyError
        fallback = _FALLBACK_DIFFICULTY.get(quiz_type, "medium")
        rubric = _RUBRICS.get((quiz_type, fallback))

    return rubric