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
  options: string[];     // ["Kata Nama", "Kata Kerja", "Kata Adjektif", "Kata Tugas"]
  question_type: string;
  difficulty: string;
  passage: string | null;
}

interface StartResponse {
  session_id: string;
  quiz_type: string;
  title: string;
  instructions: string;
  questions: QuizQuestion[];
}

interface QuestionFeedback {
  question_id: string;
  user_answer: string;
  correct_answer: string;
  is_correct: boolean;
  score: number;
  feedback: string;
}

interface SubmitResponse {
  session_id: string;
  total_score: number;
  max_score: number;
  percentage: number;
  grade: string;
  question_feedbacks: QuestionFeedback[];
  overall_feedback: string;
  suggestions: string[];
}

// ── Helper: extract the *word* from question_text ─────────────────────────────
// Backend wraps the target word with asterisks: "Budak itu *berlari* dengan pantas."
function extractWord(questionText: string): string {
  const match = questionText.match(/\*(.+?)\*/);
  return match ? match[1] : questionText;
}

// ── Helper: render question_text with the *word* bolded ───────────────────────
function renderSentence(questionText: string) {
  const parts = questionText.split(/\*(.+?)\*/);
  return parts.map((part, i) =>
    i % 2 === 1
      ? <strong key={i} style={{ color: "#4f46e5" }}>{part}</strong>
      : <span key={i}>{part}</span>
  );
}

// ── Helper: clean unwanted instruction text ────────────────────────────────
function cleanQuestionText(text: string): string {
  return text.replace(
    /^(Kenal pasti golongan kata bagi perkataan yang dicetak tebal:|Tentukan golongan kata.*?)\s*:\s*/i,
    ""
  ).trim();
}

export default function GolonganKataQuizPage() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const userId = user?.user_id;
  const [sessionId, setSessionId] = useState<string>("");
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});   // question_id → chosen category
  const [draggedId, setDraggedId] = useState<string | null>(null);
  const [submitResult, setSubmitResult] = useState<SubmitResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string>("");
  const calledOnce = useRef(false);

  // ── Fetch questions ────────────────────────────────────────────────
  const fetchQuestions = async (forceNew = false, retry = false, retrySessionId?: string) => {
    if (!userId) {
      setError("User not logged in");
      setLoading(false);
      return;
    }
    
    setQuestions([]);
    setCategories([]);
    setAnswers({});
    setSubmitResult(null);
    setError("");
    setSessionId("");
    setLoading(true);

    try {
      if (retry && retrySessionId) {
        const data = await retryComprehension(retrySessionId, "golongan_kata", userId) as StartResponse;
        setSessionId(data.session_id);
        setQuestions(data.questions);

        if (data.questions.length > 0) {
          setCategories(data.questions[0].options ?? []);
        }

        setLoading(false);
        return;
      }

      if (!forceNew) {
        const res = await fetch(
          `${API_URL}/comprehension/resume-latest?quiz_type=golongan_kata&user_id=${userId}`
        );

        if (res.status === 200) {
          const data = await res.json();
          setSessionId(data.session_id);
          setQuestions(data.questions);

          if (data.questions.length > 0) {
            setCategories(data.questions[0].options ?? []);
          }

          setLoading(false);
          return;
        }
      }

      const data = (await startComprehension("golongan_kata", userId)) as StartResponse;
      setSessionId(data.session_id);
      setQuestions(data.questions);

      if (data.questions.length > 0) {
        setCategories(data.questions[0].options ?? []);
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


  // ── Drag handlers ───────────────────────────────────────────────────────────
  const handleDragStart = (questionId: string) => setDraggedId(questionId);

  const handleDrop = (category: string) => {
    if (draggedId) {
      setAnswers((prev) => ({ ...prev, [draggedId]: category }));
      setDraggedId(null);
    }
  };

  // ── Submit ──────────────────────────────────────────────────────────────────
  const handleSubmit = async () => {
    if (!userId) return;
    
    const unanswered = questions.filter((q) => !answers[q.question_id]?.trim());

    if (unanswered.length > 0) {
      setError(
        `Sila jawab semua soalan sebelum menghantar. ` +
        `(${unanswered.length} soalan belum dijawab)`
      );
      return;
    }

    setSubmitting(true);
    setError("");
    
    try {
      const formattedAnswers = questions.map((q) => ({
        question_id: q.question_id,
        answer: answers[q.question_id] ?? "",
      }));

      const data = (await submitComprehension(
        sessionId,
        "golongan_kata",
        userId,
        formattedAnswers
      )) as SubmitResponse;

      setSubmitResult(data);

    } catch (err) {
      setError("Gagal menghantar jawapan. Sila cuba semula.");
      console.error(err);

    } finally {
      setSubmitting(false);
    }
  };

  // ── Helper: get feedback for a question ────────────────────────────────────
  const getFeedback = (questionId: string) =>
    submitResult?.question_feedbacks.find((f) => f.question_id === questionId);

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <Layout>
      <div className="container no-top-gap">

        {/* Back button */}
        <div>
          <button
            className="update-btn button1"
            onClick={() => {
              setQuestions([]);
              setAnswers({});
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
          <h1>Golongan Kata Quiz</h1>
          <p>Seret perkataan yang <strong>ditebalkan</strong> ke dalam kategori yang betul.</p>
        </div>

        {/* Loading */}
        {loading && (
          <div className="chapter-card card-base">
            <p style={{ color: "#888", fontStyle: "italic" }}>Memuatkan soalan...</p>
          </div>
        )}

        {!loading && questions.length > 0 && (
          <>
            {/* Word Pool: shows full sentence with highlighted word */}
            <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
              <h2 style={{ marginBottom: "20px" }}>Pilih Perkataan</h2>

              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {questions.map((q) => {
                  const placed = !!answers[q.question_id];
                  return (
                    <div
                      key={q.question_id}
                      draggable={!placed}
                      onDragStart={() => handleDragStart(q.question_id)}
                      style={{
                        padding: "10px 14px",
                        borderRadius: "10px",
                        cursor: placed ? "default" : "grab",
                        backgroundColor: placed ? "#e5e7eb" : "#f3f4f6",
                        border: "1px solid #e5e7eb",
                        opacity: placed ? 0.6 : 1,
                        fontSize: "14px",
                      }}
                    >
                      {renderSentence(cleanQuestionText(q.question_text))}
                      {placed && (
                        <span style={{ marginLeft: "10px", color: "#6b7280", fontSize: "12px" }}>
                          → {answers[q.question_id]}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </>
        )}

        {!loading && (
          <>
            {/* ── Category Drop Zones ── */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
                gap: "15px",
                marginBottom: "20px",
              }}
            >
              {categories.map((cat) => (
                <div
                  key={cat}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={() => handleDrop(cat)}
                  className="card-base"
                  style={{
                    minHeight: "120px",
                    padding: "12px",
                    borderRadius: "12px",
                    backgroundColor: "#f9fafb",
                    border: "1px dashed #9ca3af",
                  }}
                >
                  <h4 style={{ marginBottom: "10px" }}>{cat}</h4>
                  <ul style={{ paddingLeft: "15px", fontSize: "13px" }}>
                    {Object.entries(answers)
                      .filter(([, chosen]) => chosen === cat)
                      .map(([qid]) => {
                        const q = questions.find((q) => q.question_id === qid);
                        return (
                          <li
                            key={qid}
                            onClick={() => {
                              if (!submitResult) {
                                setAnswers((prev) => {
                                  const updated = { ...prev };
                                  delete updated[qid];
                                  return updated;
                                });
                              }
                            }}
                            title={submitResult ? "" : "Klik untuk buang jawapan"}
                            style={{
                              cursor: submitResult ? "default" : "pointer",
                              display: "flex",
                              alignItems: "center",
                              gap: "4px",
                              padding: "2px 4px",
                              borderRadius: "4px",
                              transition: "background 0.15s",
                            }}
                            onMouseEnter={(e) => {
                              if (!submitResult)
                                (e.currentTarget as HTMLLIElement).style.background = "#e2f1fe";
                            }}
                            onMouseLeave={(e) => {
                              (e.currentTarget as HTMLLIElement).style.background = "transparent";
                            }}
                          >
                            <em style={{ color: "#374151" }}>
                              {q ? extractWord(cleanQuestionText(q.question_text)) : qid}
                            </em>
                            {!submitResult && (
                              <span style={{ fontSize: "10px", color: "#9ca3af" }}>✕</span>
                            )}
                          </li>
                        );
                      })}
                  </ul>
                </div>
              ))}
            </div>

            {/* Error */}
            {error && <p style={{ color: "red" }}>{error}</p>}

            {/* Submit button — hidden after submit */}
            {!submitResult && (
              <button
                className="button1"
                onClick={error && questions.length === 0 ? () => {
                  setError("");
                  calledOnce.current = false;
                  fetchQuestions(true);
                } : handleSubmit}
                disabled={submitting}
              >
                {submitting
                  ? t("markingAnswer")
                  : error && questions.length === 0
                  ? t("TryAgain")
                  : t("checkAnswer")
                }
              </button>
            )}
          </>
        )}

        {/* ── Results (after submit) ── */}
        {submitResult && (
          <>
            {/* Per-question breakdown */}
            <div className="card-base" style={{ marginTop: "24px", padding: "24px" }}>
              <h3 style={{ marginBottom: "12px" }}>Keputusan</h3>

              <ul style={{ listStyle: "none", padding: 0 }}>
                {questions.map((q) => {
                  const fb = getFeedback(q.question_id);
                  return (
                    <li
                      key={q.question_id}
                      style={{
                        padding: "10px",
                        marginBottom: "10px",
                        borderRadius: "8px",
                        backgroundColor: fb?.is_correct ? "#f0fdf4" : "#fef2f2",
                        border: `1px solid ${fb?.is_correct ? "#bbf7d0" : "#fecaca"}`,
                      }}
                    >
                      <p style={{ margin: "0 0 4px" }}>
                        {renderSentence(cleanQuestionText(q.question_text))}
                      </p>
                      <p style={{ margin: "0 0 4px", fontSize: "13px" }}>
                        Jawapan anda: <strong>{answers[q.question_id] || "Tiada"}</strong>
                        {" "}→ Betul: <strong>{fb?.correct_answer}</strong>
                        {" "}{fb?.is_correct ? "✅" : "❌"}
                      </p>
                      {fb?.feedback && (
                        <p style={{ margin: 0, fontSize: "12px", color: "#6b7280" }}>
                          {fb.feedback}
                        </p>
                      )}
                    </li>
                  );
                })}
              </ul>
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

              {/* Feedback */}
              <div style={{ marginTop: "20px" }}>
                <h3>Maklum Balas</h3>
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
                    setAnswers({});
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
                    setAnswers({});
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
