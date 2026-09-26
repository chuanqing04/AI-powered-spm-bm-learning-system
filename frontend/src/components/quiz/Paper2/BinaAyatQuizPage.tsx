import Layout from "../../shared/Layout";
import { useLanguage } from "../../../language";
import { useState, useEffect, useRef } from "react";
import { startComprehension, submitComprehension, retryComprehension } from "../../../services/api";
import { useAuth } from "../../../context/AuthContext";

// ── Types ─────────────────────────────────────────
import { API_URL } from "../../../services/config";
interface QuizQuestion {
  question_id: string;
  question_text: string; // e.g. "Bina ayat yang lengkap dan gramatis menggunakan perkataan: <perkataan>"
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

// ── Helper: extract the target word from question_text ────────────────────────
// Backend format: "Bina ayat yang lengkap dan gramatis menggunakan perkataan: *perkataan*"
function extractWord(questionText: string): string {
  const match = questionText.match(/perkataan:\s*(.+)/i);
  return match ? match[1].trim() : questionText;
}

export default function BinaAyatQuizPage() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const userId = user?.user_id;
  const [sessionId, setSessionId] = useState<string>("");
  const [questions, setQuestions] = useState<QuizQuestion[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitResult, setSubmitResult] = useState<SubmitResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string>("");
  const calledOnce = useRef(false);

  // ── Fetch questions ──────────────────────────────────────────────────────
  const fetchQuestions = async (forceNew = false, retry = false, retrySessionId?: string) => {
    if (!userId) {
      setError("User not logged in");
      setLoading(false);
      return;
    }
    
    setQuestions([]);
    setAnswers({});
    setSubmitResult(null);
    setError("");
    setSessionId("");
    setLoading(true);

    try {
      // If cuba lagi
      if (retry && retrySessionId) {
        const data = await retryComprehension(retrySessionId, "bina_ayat", userId) as StartResponse;
        setSessionId(data.session_id);
        setQuestions(data.questions);
        setLoading(false);
        return;
      }

      if (!forceNew) {
        // Resume-latest
        const res = await fetch(
          `${API_URL}/comprehension/resume-latest?quiz_type=bina_ayat&user_id=${userId}`
        );

        if (res.status === 200) {
          const data = await res.json();          
          setSessionId(data.session_id);
          setQuestions(data.questions);
          setLoading(false);
          return;
        }
      }

      // Start new session      
      const data = (await startComprehension("bina_ayat", userId)) as StartResponse;
      setSessionId(data.session_id);
      setQuestions(data.questions);

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
        "bina_ayat",
        userId,
        formattedAnswers,        
      )) as SubmitResponse;

      setSubmitResult(data);

    } catch (err) {
      setError("Gagal menghantar jawapan. Sila cuba semula.");
      console.error(err);

    } finally {
      setSubmitting(false);
    }
  };

  const getFeedback = (questionId: string) =>
    submitResult?.question_feedbacks.find((f) => f.question_id === questionId);

  // ── Render ───────────────────────────────────────────────────────────────
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
          <h1>Bina Ayat Quiz</h1>
          <p>Quiz untuk membina ayat yang gramatis dan lengkap.</p>
        </div>

        {/* Loading */}
        {loading && (
          <div className="chapter-card card-base">
            <p style={{ color: "#888", fontStyle: "italic" }}>Memuatkan soalan...</p>
          </div>
        )}

        {/* ── Quiz section ── */}
        {!loading && (
          <>
            {questions.map((q, index) => {
              const fb = getFeedback(q.question_id);
              const word = extractWord(q.question_text);

              return (
                <div
                  key={q.question_id}
                  className="chapter-card card-base"
                  style={{ marginBottom: "20px" }}
                >
                  <div className="chapter-top">SOALAN {index + 1}</div>

                  <h4>Bina satu ayat lengkap menggunakan kata berikut:</h4>
                  <h4>Kata: <strong> {word} </strong></h4>

                  <div className="text-area-bina-ayat">
                    <textarea
                      rows={2}
                      placeholder="Bina ayat lengkap..."
                      value={answers[q.question_id] ?? ""}
                      onChange={(e) =>
                        setAnswers((prev) => ({
                          ...prev,
                          [q.question_id]: e.target.value,
                        }))
                      }
                      disabled={!!submitResult}
                      style={{ opacity: submitResult ? 0.7 : 1 }}
                    />
                  </div>

                  {/* Per-question feedback shown inline after submit */}
                  {fb && (
                    <div
                      style={{
                        marginTop: "12px",
                        padding: "10px",
                        borderRadius: "8px",
                        backgroundColor: fb.is_correct ? "#f0fdf4" : "#fef2f2",
                        border: `1px solid ${fb.is_correct ? "#bbf7d0" : "#fecaca"}`,
                      }}
                    >
                      <p style={{ margin: "0 0 4px", fontSize: "13px" }}>
                        {fb.is_correct ? "✅" : "❌"}{" "}
                        <strong>{fb.is_correct ? "Betul!" : "Kurang tepat"}</strong>
                      </p>
                      {fb.feedback && (
                        <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#6b7280" }}>
                          {fb.feedback}
                        </p>
                      )}
                      {!fb.is_correct && fb.correct_answer && (
                        <p style={{ margin: "8px 0 0", fontSize: "12px" }}>
                          <strong>Contoh jawapan: </strong>
                          <span style={{ color: "#166534" }}>{fb.correct_answer}</span>
                        </p>
                      )}
                    </div>
                  )}
                </div>
              );
            })}

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

        {/* ── Summary card (after submit) ── */}
        {submitResult && (
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
                  if (!sessionId) {
                    setError("No session to retry");
                    return;
                  }

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
        )}

        <div style={{ marginBottom: "40px" }} />
      </div>
    </Layout>
  );
}