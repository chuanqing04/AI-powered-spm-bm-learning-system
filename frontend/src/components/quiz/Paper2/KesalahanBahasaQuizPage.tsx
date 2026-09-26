import Layout from "../../shared/Layout";
import { useLanguage } from "../../../language";
import { useState, useEffect, useRef } from "react";
import { startComprehension, submitComprehension, retryComprehension } from "../../../services/api";
import { useAuth } from "../../../context/AuthContext";

// ── Types ─────────────────────────────────────────
import { API_URL } from "../../../services/config";
interface QuizQuestion {
  question_id: string;
  question_text: string; // e.g. "Kenal pasti kesalahan bahasa dan tulis semula ayat dengan betul: '<ayat>'"
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

// ── Helper: extract just the sentence from question_text ─────────────────────
// Backend format: "Kenal pasti kesalahan bahasa dan tulis semula ayat dengan betul: '<ayat>'"
function extractSentence(questionText: string): string {
  const match = questionText.match(/:\s*['"](.+)['"]\s*$/);
  return match ? match[1].trim() : questionText;
}

// ── Per-question answer shape ─────────────────────────────────────────────────
interface KesalahanAnswer {
  wrong: string;
  correct: string;
}

export default function KesalahanBahasaQuizPage() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const userId = user?.user_id;  
  const [sessionId, setSessionId]       = useState<string>("");
  const [questions, setQuestions]       = useState<QuizQuestion[]>([]);
  const [answers, setAnswers]           = useState<Record<string, KesalahanAnswer>>({});
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

    setQuestions([]);
    setAnswers({});
    setSubmitResult(null);
    setError("");
    setSessionId("");
    setLoading(true);

    try {
      if (retry && retrySessionId) {
        const data = await retryComprehension(retrySessionId, "kesalahan_bahasa", userId) as StartResponse;
        setSessionId(data.session_id);
        setQuestions(data.questions);
        setLoading(false);
        return;
      }
      
      if (!forceNew) {
        const res = await fetch(
          `${API_URL}/comprehension/resume-latest?quiz_type=kesalahan_bahasa&user_id=${userId}`
        );

        if (res.status === 200) {
          const data = await res.json();
          setSessionId(data.session_id);
          setQuestions(data.questions);
          setLoading(false);
          return;
        }
      }

      const data = (await startComprehension("kesalahan_bahasa", userId)) as StartResponse;

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

  // ── Answer helpers ───────────────────────────────────────────────────────
  const handleChange = (
    question_id: string,
    field: "wrong" | "correct",
    value: string
  ) => {
    setAnswers((prev) => ({
      ...prev,
      [question_id]: { ...prev[question_id], [field]: value },
    }));
  };

  // Combine both fields into one string for the backend
  const formatAnswer = (ans: KesalahanAnswer | undefined): string => {
    if (!ans) return "";
    return `Kesalahan: ${ans.wrong || "-"} | Pembetulan: ${ans.correct || "-"}`;
  };

  // ── Submit ───────────────────────────────────────────────────────────────
  const handleSubmit = async () => {
    if (!userId) return;

    const unanswered = questions.filter((q) => {
      const ans = answers[q.question_id];
      return !ans?.wrong?.trim() || !ans?.correct?.trim();
    });
    if (unanswered.length > 0) {
      setError(
        `Sila lengkapkan semua soalan sebelum menghantar. ` +
        `(${unanswered.length} soalan belum lengkap)`
      );
      return;
    }

    setSubmitting(true);
    setError("");

    try {
      const formattedAnswers = questions.map((q) => ({
        question_id: q.question_id,
        answer: formatAnswer(answers[q.question_id]),
      }));

      const data = (await submitComprehension(
        sessionId,
        "kesalahan_bahasa",
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
          <h1>Kesalahan Bahasa Quiz</h1>
          <p>Kenal pasti kesalahan dalam ayat dan tulis pembetulan yang betul.</p>
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
              const fb      = getFeedback(q.question_id);
              const sentence = extractSentence(q.question_text);

              return (
                <div
                  key={q.question_id}
                  className="chapter-card card-base"
                  style={{ marginBottom: "25px" }}
                >
                  <div className="chapter-top">SOALAN {index + 1}</div>

                  <p><strong>Ayat:</strong> {sentence}</p>

                  {/* Kesalahan input */}
                  <div style={{ marginTop: "10px" }}>
                    <label><strong>Kesalahan:</strong></label>
                    <input
                      type="text"
                      className="text-input-kesalahan"
                      placeholder="Tulis perkataan yang salah"
                      value={answers[q.question_id]?.wrong ?? ""}
                      onChange={(e) => handleChange(q.question_id, "wrong", e.target.value)}
                      disabled={!!submitResult}
                      style={{ opacity: submitResult ? 0.7 : 1 }}
                    />
                  </div>

                  {/* Pembetulan input */}
                  <div style={{ marginTop: "10px" }}>
                    <label><strong>Pembetulan:</strong></label>
                    <input
                      type="text"
                      className="text-input-kesalahan"
                      placeholder="Tulis pembetulan yang betul"
                      value={answers[q.question_id]?.correct ?? ""}
                      onChange={(e) => handleChange(q.question_id, "correct", e.target.value)}
                      disabled={!!submitResult}
                      style={{ opacity: submitResult ? 0.7 : 1 }}
                    />
                  </div>

                  {/* Per-question feedback inline after submit */}
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
                        <strong>{fb.is_correct ? "Betul!" : "Salah"}</strong>
                      </p>
                      {fb.feedback && (
                        <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#6b7280" }}>
                          {fb.feedback}
                        </p>
                      )}
                      {!fb.is_correct && fb.correct_answer && (
                        <p style={{ margin: "8px 0 0", fontSize: "12px" }}>
                          <strong>Jawapan betul: </strong>
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