import Layout from "../../shared/Layout";
import { useLanguage } from "../../../language";
import { useEffect, useState, useRef } from "react";
import { startEssay, submitEssay, retryEssay } from "../../../services/api";
import { useAuth } from "../../../context/AuthContext";

// ── Types ────────────────────────────────────────────────────────────────
import { API_URL } from "../../../services/config";
interface EssayRubric {
  content_score: number;
  language_score: number;
  grammar_score: number;
  vocabulary_score: number;
  coherence_score: number;
  total_score: number;
  max_score: number;
  grade: string;
}

interface SubmitResult {
  total_score: number;
  max_score: number;
  percentage: number;
  grade: string;
  essay_rubric: EssayRubric;
  overall_feedback: string;
  suggestions: string[];
}

export default function KaranganPendekQuizPage() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const userId = user?.user_id;
  const [sessionId, setSessionId] = useState<string>("");
  const [questionId, setQuestionId] = useState<string>("");
  const [question, setQuestion] = useState<string>("");
  const [essayText, setEssayText] = useState<string>("");
  const [result, setResult] = useState<SubmitResult | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string>("");
  const calledOnce = useRef(false); //Prevent double API call in Strict Mode

  // ── Fetch question ─────────────────────────────────────────────────────
  const fetchQuestion = async (forceNew = false, retry = false, retrySessionId?: string) => {
    if (!userId) {
      setError("User not logged in");
      setLoading(false);
      return;
    }

    // Reset question immediately
    setQuestion("");
    setQuestionId("");
    setEssayText("");
    setResult(null);
    setError("");
    setSessionId("");
    setLoading(true);

    try {
      // ── Retry ─────────────────────────────────────────
      if (retry && retrySessionId) {
        const data = await retryEssay(retrySessionId, "karangan_pendek", userId) as {
          session_id: string;
          questions: { question_id: string; question_text: string }[];
        };

        setSessionId(data.session_id);
        setQuestionId(data.questions[0]?.question_id ?? "");
        setQuestion(data.questions[0]?.question_text ?? "");
        return;
      }

      // ── Resume latest ─────────────────────────────────
      if (!forceNew) {
        const res = await fetch(
          `${API_URL}/essay/resume-latest?quiz_type=karangan_pendek&user_id=${userId}`
        );

        if (res.status === 200) {
          const data = await res.json();

          setSessionId(data.session_id);
          setQuestionId(data.questions[0]?.question_id ?? "");
          setQuestion(data.questions[0]?.question_text ?? "");
          return;
        }
      }

      // ── Start new ─────────────────────────────────────
      const data = await startEssay("karangan_pendek", userId) as {
        session_id: string;
        questions: { question_id: string; question_text: string }[];
      };

      setSessionId(data.session_id);
      setQuestionId(data.questions[0]?.question_id ?? "");
      setQuestion(data.questions[0]?.question_text ?? "");

    } catch (err) {
      console.error("fetchQuestion failed:", err);
      setError("Gagal memuatkan soalan. Sila cuba semula.");

    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!userId || calledOnce.current) return;
    calledOnce.current = true;
    fetchQuestion();
  }, [userId]);

  // ── Submit ─────────────────────────────────────────────────────────────
  async function handleSubmit() {
    if (!userId) return;

    if (!essayText.trim()) {
      setError("Sila tulis karangan anda sebelum menghantar.");
      return;
    }

    setSubmitting(true);
    setError("");

    try {
      const data = await submitEssay(sessionId, "karangan_pendek", userId, [
        { question_id: questionId, answer: essayText },
      ]);

      setResult(data as SubmitResult);

    } catch (err) {
      console.error("submitEssay failed:", err);
      setError("Gagal menghantar karangan. Sila cuba semula.");

    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Layout>
      {/* Back button */}
      <div>
        <button className="update-btn button1" 
          onClick={() => {
            setQuestion("");     // clear question
            setEssayText("");    // clear essay
            setResult(null);     // clear previous result
            setError("");        // clear error
            window.history.back();
          }}
        >
          {t("back")}
        </button>
      </div>

      {/* Header */}
      <div className="page-header">
        <h1>Karangan Pendek Quiz</h1>
        <p>Tulis sebuah karangan antara 150 hingga 200 patah perkataan.</p>
      </div>

      {/* Question */}
      <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
        {loading ? (
          <p style={{ color: "#888", fontStyle: "italic" }}>Memuatkan soalan...</p>
        ) : question ? (
          <div style={{ lineHeight: "1.8", textAlign: "justify" }}>
            {(() => {
              const lines = question.split("\n");

              return lines.map((line, i) => {
                const trimmed = line.trim();

                // Empty line → spacer
                if (!trimmed) return <div key={i} style={{ marginBottom: "12px" }} />;

                // Email headers: Daripada / Kepada / Subjek
                if (/^(Daripada|Kepada|Subjek):/.test(trimmed)) {
                  return (
                    <p key={i} style={{ margin: "2px 0", fontFamily: "monospace", fontSize: "0.9rem", color: "#374151" }}>
                      {trimmed}
                    </p>
                  );
                }

                // Email sign-off: Yang benar / Sahabatmu / etc.
                if (/^(Yang benar|Yang ikhlas|Sahabatmu|Sekian|Terima kasih),?$/.test(trimmed)) {
                  return (
                    <p key={i} style={{ margin: "4px 0", color: "#374151" }}>
                      {trimmed}
                    </p>
                  );
                }

                // Bullet points: lines starting with -
                if (trimmed.startsWith("-")) {
                  return (
                    <p key={i} style={{ margin: "2px 0 2px 16px", color: "#333" }}>
                      {"• " + trimmed.replace(/^-\s*/, "")}
                    </p>
                  );
                }

                // Arahan line — after a spacer (\n\n) and is the last non-empty line
                const prevLine = lines[i - 1]?.trim() ?? "";
                const isAfterSpacer = prevLine === "";
                const remainingLines = lines.slice(i + 1).filter(l => l.trim());
                const isLastBlock = remainingLines.length === 0;
                if (isAfterSpacer && isLastBlock) {
                  return (
                    <p key={i} style={{ margin: "4px 0", fontWeight: "500" }}>
                      {trimmed}
                    </p>
                  );
                }

                // First line — bold title (short, no period)
                if (i === 0 && trimmed.length < 80 && !trimmed.endsWith(".")) {
                  return (
                    <p key={i} style={{ fontWeight: "bold", fontSize: "1.05rem", marginBottom: "8px" }}>
                      {trimmed}
                    </p>
                  );
                }

                // Normal prose
                return <p key={i} style={{ margin: "4px 0", color: "#333" }}>{trimmed}</p>;
              });
            })()}
          </div>
        ) : (
          <p>Tiada soalan ditemui.</p>
        )}
      </div>

      {/* Textarea — hide after submission */}
      {!loading && !result && (
        <>
          <div className="text-area-karangan">
            <textarea
              placeholder="Tulis karangan anda di sini..."
              value={essayText}
              onChange={(e) => setEssayText(e.target.value)}
            />
          </div>

          {/* Live word count */}
          <p style={{ fontSize: "12px", color: "#9ca3af", marginTop: "6px", textAlign: "right" }}>
            {essayText.trim() ? essayText.trim().split(/\s+/).length : 0} / 200 patah perkataan
          </p>
        </>
      )}

      {/* Error + button — always visible when not loading and no result */}
      {!loading && !result && (
        <>
          {error && <p style={{ color: "red", marginTop: "8px" }}>{error}</p>}

          <button
            className="button1"
            onClick={error && !question ? () => {
              setError("");
              calledOnce.current = false;
              fetchQuestion(true);
            } : handleSubmit}
            disabled={submitting}
          >
            {submitting
              ? `${t("markingEssay")}...`
              : error && !question
              ? t("TryAgain")
              : t("submitEssay")
            }
          </button>
        </>
      )}

      {/* Submitted Essay */}
      {result && (
        <div className="card-base" style={{ marginTop: "24px", padding: "24px" }}>
          <h3 style={{ marginBottom: "12px" }}>Karangan Anda</h3>
          <p style={{ lineHeight: "1.8", color: "#333", whiteSpace: "pre-wrap" }}>
            {essayText}
          </p>
        </div>
      )}

      {/* Result card */}
      {result && (
        <div className="card-base" style={{ marginTop: "24px", padding: "24px" }}>
          
          {/* Grade banner */}          
          <div style={{ textAlign: "center", marginBottom: "24px" }}>
            <h2 style={{ fontSize: "2rem", margin: 0 }}>Gred: {result.essay_rubric.grade}</h2>
            <p style={{ fontSize: "1.1rem", color: "#555" }}>
              Markah Karangan: {result.essay_rubric.total_score} / {result.essay_rubric.max_score} ({result.percentage.toFixed(1)}%)
            </p>
          </div>

          <hr />

          {/* Rubric breakdown */}
          <div style={{ marginTop: "20px" }}>
            <h3>Pecahan Markah Rubrik</h3>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <tbody>
                {[
                  { label: "Kandungan (Content)",      score: result.essay_rubric.content_score,    max: 12 },
                  { label: "Bahasa (Language)",        score: result.essay_rubric.language_score,   max: 9  },
                  { label: "Tatabahasa (Grammar)",     score: result.essay_rubric.grammar_score,    max: 5  },
                  { label: "Kosa Kata (Vocabulary)",   score: result.essay_rubric.vocabulary_score, max: 3  },
                  { label: "Kohesi (Coherence)",       score: result.essay_rubric.coherence_score,  max: 1  },
                ].map(({ label, score, max }) => (
                  <tr key={label} style={{ borderBottom: "1px solid #eee" }}>
                    <td style={{ padding: "10px 0", fontWeight: 500 }}>{label}</td>
                    <td style={{ padding: "10px 0", textAlign: "right" }}>{score} / {max}</td>
                  </tr>
                ))}
                {/* Total row */}
                <tr style={{ fontWeight: "bold", borderTop: "2px solid #ccc" }}>
                  <td style={{ padding: "12px 0" }}>Jumlah</td>
                  <td style={{ padding: "12px 0", textAlign: "right" }}>
                    {result.essay_rubric.total_score} / {result.essay_rubric.max_score}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <hr />

          {/* Feedback */}
          <div style={{ marginTop: "20px" }}>
            <h3>Maklum Balas</h3>
            <p style={{ lineHeight: "1.7", color: "#333", whiteSpace: "pre-line" }}>{result.overall_feedback}</p>
          </div>

          <hr />

          {/* Suggestions */}
          {result.suggestions.length > 0 && (
            <div style={{ marginTop: "20px" }}>
              <h3>Cadangan Penambahbaikan</h3>
              <ul style={{ paddingLeft: "20px", lineHeight: "1.8" }}>
                {result.suggestions.map((s, i) => (
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
                if (!sessionId) {
                  setError("No session to retry");
                  return;
                }

                setResult(null);
                setEssayText("");
                setError("");
                fetchQuestion(false, true, sessionId);
                window.scrollTo({ top: 0, behavior: "smooth" });
              }}
            >
              {t("TryAgain")}
            </button>
            <button
              className="button1"
              onClick={() => {
                setResult(null);
                setEssayText("");
                setError("");
                calledOnce.current = false; // allow re-fetch
                fetchQuestion(true); // get new question
                window.scrollTo({ top: 0, behavior: "smooth" });
              }}
            >
              {t("generateMoreQuestionsButton")}
            </button>
          </div>
        </div>
      )}

      <div style={{ marginBottom: "40px" }} />
    </Layout>
  );
}