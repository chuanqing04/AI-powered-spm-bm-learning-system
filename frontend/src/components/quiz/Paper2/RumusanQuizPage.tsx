import Layout from "../../shared/Layout";
import { useLanguage } from "../../../language";
import { useState, useEffect, useRef } from "react";
import { startComprehension, submitComprehension, retryComprehension } from "../../../services/api";
import { useAuth } from "../../../context/AuthContext";

// ── Types ─────────────────────────────────────────
import { API_URL } from "../../../services/config";
interface QuizQuestion {
  question_id: string;
  question_text: string;
  question_type: string;
  difficulty: string;
  options: string[] | null;
  passage: string | null;
}

interface StartResponse {
  session_id: string;
  quiz_type: string;
  title: string;
  instructions: string;
  questions: QuizQuestion[];
}

interface RumusanIsi {
  isi_number: number;
  isi_text: string;
  bahan_sumber: string;
  marks_awarded: number;
  reason: string;
}

interface SubmitResponse {
  session_id: string;
  quiz_type: string;
  isi_list: RumusanIsi[];
  isi_score: number;
  isi_count: number;
  bahan_coverage: Record<string, number>;
  bahasa_score: number;
  bahasa_feedback: string;
  total_score: number;
  max_score: number;
  percentage: number;
  grade: string;
  word_count: number;
  overall_feedback: string;
  suggestions: string[];
}

// ── Helper: split combined passage into 3 bahan ──────────────────────────────
// Backend format: "[BAHAN_1]\n<text>\n\n[BAHAN_2]\n<text>\n\n[BAHAN_3]\n<text>"
function splitPassage(passage: string): { bahan1: string; bahan2: string; bahan3: string } {
  const bahan1Match = passage.match(/\[BAHAN_1\]\n([\s\S]*?)(?=\n\n\[BAHAN_2\])/);
  const bahan2Match = passage.match(/\[BAHAN_2\]\n([\s\S]*?)(?=\n\n\[BAHAN_3\])/);
  const bahan3Match = passage.match(/\[BAHAN_3\]\n([\s\S]*)/);
  return {
    bahan1: bahan1Match ? bahan1Match[1].trim() : "",
    bahan2: bahan2Match ? bahan2Match[1].trim() : "",
    bahan3: bahan3Match ? bahan3Match[1].trim() : "",
  };
}

export default function RumusanQuizPage() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const userId = user?.user_id;
  const [sessionId, setSessionId]       = useState<string>("");
  const [question, setQuestion]         = useState<QuizQuestion | null>(null);
  const [passage, setPassage]           = useState<{ bahan1: string; bahan2: string; bahan3: string }>({ bahan1: "", bahan2: "", bahan3: "" });
  const [rumusan, setRumusan]           = useState<string>("");
  const [submitResult, setSubmitResult] = useState<SubmitResponse | null>(null);
  const [loading, setLoading]           = useState(true);
  const [submitting, setSubmitting]     = useState(false);
  const [error, setError]               = useState<string>("");
  const calledOnce                      = useRef(false);

  // ── Fetch questions ──────────────────────────────────────────────────────
  const fetchQuestions = async (forceNew = false, retry = false, retrySessionId?: string) => {
    if (!userId) {
      setError("User not logged in");
      setLoading(false);
      return;
    }

    setQuestion(null);
    setPassage({ bahan1: "", bahan2: "", bahan3: "" });
    setRumusan("");
    setSubmitResult(null);
    setError("");
    setSessionId("");
    setLoading(true);

    try {
      if (retry && retrySessionId) {
        const data = await retryComprehension(retrySessionId, "rumusan", userId) as StartResponse;
        setSessionId(data.session_id);
        const q = data.questions[0] ?? null;
        setQuestion(q);
        if (q?.passage) {
          setPassage(splitPassage(q.passage));
        }
        setLoading(false);
        return;
      }

      if (!forceNew) {
        const res = await fetch(
          `${API_URL}/comprehension/resume-latest?quiz_type=rumusan&user_id=${userId}`
        );

        if (res.status === 200) {
          const data = await res.json();
          setSessionId(data.session_id);

          const q = data.questions?.[0] ?? null;
          setQuestion(q);

          if (q?.passage) {
            setPassage(splitPassage(q.passage));
          }

          setLoading(false);
          return;
        }
      }

      const data = (await startComprehension("rumusan", userId)) as StartResponse;
      setSessionId(data.session_id);

      // Rumusan only has one question
      const q = data.questions[0] ?? null;
      setQuestion(q);

      if (q?.passage) {
        setPassage(splitPassage(q.passage));
      }

    } catch (err) {
      setError("Gagal memuatkan soalan. Sila cuba semula.");
      console.error(err);

    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!userId || calledOnce.current) return;
    calledOnce.current = true;
    fetchQuestions();
  }, [userId]);

  // ── Submit ───────────────────────────────────────────────────────────────
  const handleSubmit = async () => {
    if (!userId) return;
    
    if (!rumusan.trim()) {
      setError("Sila tulis rumusan anda sebelum menghantar.");
      return;
    }

    setSubmitting(true);
    setError("");

    try {
      const data = (await submitComprehension(
        sessionId,
        "rumusan",
        userId,
        [{ question_id: question!.question_id, answer: rumusan }]
      )) as SubmitResponse;

      setSubmitResult(data);

    } catch (err) {
      setError("Gagal menghantar rumusan. Sila cuba semula.");
      console.error(err);

    } finally {
      setSubmitting(false);
    }
  };

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <Layout>
      <div className="container no-top-gap">

        {/* Back button */}
        <div>
          <button
            className="update-btn button1"
            onClick={() => {
              setQuestion(null);
              setRumusan("");
              setSubmitResult(null);
              setError("");
              window.history.back();
            }}
          >
            {t("back")}
          </button>
        </div>

        {/* Header */}
        <div className="hero">
          <h1>Rumusan Quiz</h1>
          <p>
            Baca dan teliti setiap bahan yang diberikan, kemudian buat satu rumusan yang
            panjangnya tidak melebihi 120 patah perkataan. Anda digalakkan supaya menggunakan
            ayat anda sendiri tanpa mengubah maksud asal setiap bahan.
          </p>
        </div>

        {/* Loading */}
        {loading && (
          <div className="chapter-card card-base">
            <p style={{ color: "#888", fontStyle: "italic" }}>Memuatkan soalan...</p>
          </div>
        )}

        {!loading && question && (
          <>
            {/* ── Bahan 1 ── */}
            <div className="chapter-card card-base" style={{ marginBottom: "20px" }}>
              <div className="chapter-top">BAHAN 1</div>
              <p style={{ lineHeight: "1.8", whiteSpace: "pre-line" }}>{passage.bahan1}</p>
            </div>

            {/* ── Bahan 2 ── */}
            <div className="chapter-card card-base" style={{ marginBottom: "20px" }}>
              <div className="chapter-top">BAHAN 2</div>
              <p style={{ lineHeight: "1.8", whiteSpace: "pre-line" }}>{passage.bahan2}</p>
            </div>

            {/* ── Bahan 3 ── */}
            <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
              <div className="chapter-top">BAHAN 3</div>
              <p style={{ lineHeight: "1.8", whiteSpace: "pre-line" }}>{passage.bahan3}</p>
            </div>

            {/* ── Rumusan textarea ── */}
            <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
              <div className="chapter-top" style={{ marginBottom: "25px" }}>RUMUSAN</div>

              <div className="text-area-karangan">
                <textarea
                  placeholder="Tulis rumusan anda di sini..."
                  value={rumusan}
                  onChange={(e) => setRumusan(e.target.value)}
                  disabled={!!submitResult}
                  style={{ opacity: submitResult ? 0.7 : 1 }}
                />
              </div>

              {/* Live word count */}
              <p style={{ fontSize: "12px", color: "#9ca3af", marginTop: "6px", textAlign: "right" }}>
                {rumusan.trim() ? rumusan.trim().split(/\s+/).length : 0} / 120 patah perkataan
              </p>
            </div>
          </>
        )}

        {!loading && (
          <>
            {/* Error */}
            {error && <p style={{ color: "red" }}>{error}</p>}

            {/* Submit button — hidden after submit */}
            {!submitResult && (
              <button
                className="button1"
                onClick={error && !question ? () => {
                  setError("");
                  calledOnce.current = false;
                  fetchQuestions(true);
                } : handleSubmit}
                disabled={submitting}
              >
                {submitting
                  ? t("markingAnswer")
                  : error && !question
                  ? t("TryAgain")
                  : t("checkAnswer")
                }
              </button>
            )}
          </>
        )}        

        {/* ── Result card (after submit) ── */}
        {submitResult && (
          <>
            {/* Isi breakdown */}
            <div className="card-base" style={{ marginTop: "24px", padding: "24px" }}>
              <h3 style={{ marginBottom: "12px" }}>Senarai Isi</h3>
              <p style={{ fontSize: "12px", color: "#6b7280", marginBottom: "12px" }}>
                Kiraan perkataan (setakat 120): <strong>{submitResult.word_count}</strong>
              </p>

              {submitResult.isi_list.length === 0 ? (
                <p style={{ color: "#9ca3af", fontStyle: "italic" }}>Tiada isi yang dikenal pasti.</p>
              ) : (
                <ul style={{ listStyle: "none", padding: 0 }}>
                  {submitResult.isi_list.map((isi) => (
                    <li
                      key={isi.isi_number}
                      style={{
                        padding: "10px",
                        marginBottom: "10px",
                        borderRadius: "8px",
                        backgroundColor: isi.marks_awarded === 2 ? "#f0fdf4" : "#fef2f2",
                        border: `1px solid ${isi.marks_awarded === 2 ? "#bbf7d0" : "#fecaca"}`,
                      }}
                    >
                      <p style={{ margin: "0 0 4px", fontSize: "13px", fontWeight: "bold" }}>
                        Isi {isi.isi_number} — {isi.bahan_sumber}
                        <span style={{ marginLeft: "8px" }}>
                          {isi.marks_awarded === 2 ? "✅" : "❌"} {isi.marks_awarded}m
                        </span>
                      </p>
                      <p style={{ margin: "0 0 4px", fontSize: "13px" }}>{isi.isi_text}</p>
                      <p style={{ margin: 0, fontSize: "12px", color: "#6b7280" }}>{isi.reason}</p>
                    </li>
                  ))}
                </ul>
              )}

              {/* Bahan coverage */}
              <div style={{ marginTop: "12px", display: "flex", gap: "10px", flexWrap: "wrap" }}>
                {Object.entries(submitResult.bahan_coverage).map(([bahan, count]) => (
                  <span
                    key={bahan}
                    style={{
                      padding: "4px 10px",
                      borderRadius: "999px",
                      backgroundColor: count > 0 ? "#dbeafe" : "#fee2e2",
                      fontSize: "12px",
                      color: count > 0 ? "#1e40af" : "#991b1b",
                    }}
                  >
                    {bahan}: {count} isi
                  </span>
                ))}
              </div>
            </div>

            {/* Summary card */}
            <div className="card-base" style={{ marginTop: "24px", padding: "24px" }}>

              {/* Grade banner */}
              <div style={{ textAlign: "center", marginBottom: "24px" }}>
                <h2 style={{ fontSize: "2rem", margin: 0 }}>Gred: {submitResult.grade}</h2>
                <p style={{ fontSize: "1.1rem", color: "#555" }}>
                  Markah: {submitResult.total_score} / {submitResult.max_score}
                  {" "}({submitResult.percentage.toFixed(1)}%)
                </p>
              </div>

              <hr />

              {/* Score breakdown */}
              <div style={{ marginTop: "20px" }}>
                <h3>Pecahan Markah</h3>
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <tbody>
                    <tr style={{ borderBottom: "1px solid #eee" }}>
                      <td style={{ padding: "10px 0", fontWeight: 500 }}>Isi ({submitResult.isi_count} isi)</td>
                      <td style={{ padding: "10px 0", textAlign: "right" }}>{submitResult.isi_score} / 20</td>
                    </tr>
                    <tr style={{ borderBottom: "1px solid #eee" }}>
                      <td style={{ padding: "10px 0", fontWeight: 500 }}>Bahasa</td>
                      <td style={{ padding: "10px 0", textAlign: "right" }}>{submitResult.bahasa_score} / 10</td>
                    </tr>
                    <tr style={{ fontWeight: "bold", borderTop: "2px solid #ccc" }}>
                      <td style={{ padding: "12px 0" }}>Jumlah</td>
                      <td style={{ padding: "12px 0", textAlign: "right" }}>
                        {submitResult.total_score} / {submitResult.max_score}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <hr />

              {/* Bahasa feedback */}
              <div style={{ marginTop: "20px" }}>
                <h3>Ulasan Bahasa</h3>
                <p style={{ lineHeight: "1.7", color: "#333" }}>{submitResult.bahasa_feedback}</p>
              </div>

              <hr />

              {/* Overall feedback */}
              <div style={{ marginTop: "20px" }}>
                <h3>Maklum Balas Keseluruhan</h3>
                <p style={{ lineHeight: "1.7", color: "#333" }}>{submitResult.overall_feedback}</p>
              </div>

              <hr />

              {/* Suggestions */}
              {submitResult.suggestions.length > 0 && (
                <div style={{ marginTop: "20px" }}>
                  <h3>Cadangan Penambahbaikan</h3>
                  <ul style={{ paddingLeft: "20px", lineHeight: "1.8" }}>
                    {submitResult.suggestions.map((s, i) => (
                      <li key={i} style={{ color: "#333", marginBottom: "6px" }}>{s}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Cuba Lagi and Soalan Baharu */}
              <div style={{ marginTop: "24px", display: "flex", gap: "12px", justifyContent: "center" }}>
                <button
                  className="button1"
                  onClick={() => {
                    setSubmitResult(null);
                    setRumusan("");
                    setError("");
                    fetchQuestions(false, true, sessionId);
                    window.scrollTo({ top: 0, behavior: "smooth" });
                  }}
                >
                  {t("TryAgain")}
                </button>
                <button
                  className="button1"
                  onClick={() => {
                    setSubmitResult(null);
                    setRumusan("");
                    setError("");
                    calledOnce.current = false;
                    fetchQuestions(true);
                    window.scrollTo({ top: 0, behavior: "smooth" });
                  }}
                >
                  {t("generateMoreQuestionsButton")}
                </button>
              </div>
            </div>
          </>
        )}

        <div style={{ marginBottom: "40px" }} />
      </div>
    </Layout>
  );
}