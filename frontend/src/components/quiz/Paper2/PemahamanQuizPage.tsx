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
  marks: number;
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

interface PemahamanFeedback {
  question_id: string;
  question_text: string;
  user_answer: string;
  marks_awarded: number;
  max_marks: number;
  breakdown: Record<string, number>;
  feedback: string;
}

interface SubmitResponse {
  session_id: string;
  quiz_type: string;
  total_score: number;
  max_score: number;
  percentage: number;
  grade: string;
  question_feedbacks: PemahamanFeedback[];
  overall_feedback: string;
  suggestions: string[];
}

// ── Helper: split combined passage into Bahan 1 and Bahan 2 ─────────────────
// Backend format: "[BAHAN_1]\n<text>\n\n[BAHAN_2]\n<text>"
function splitPassage(passage: string): { bahan1: string; bahan2: string } {
  const bahan1Match = passage.match(/\[BAHAN_1\]\n([\s\S]*?)(?=\n\n\[BAHAN_2\])/);
  const bahan2Match = passage.match(/\[BAHAN_2\]\n([\s\S]*)/);
  return {
    bahan1: bahan1Match ? bahan1Match[1].trim() : "",
    bahan2: bahan2Match ? bahan2Match[1].trim() : "",
  };
}

export default function PemahamanQuizPage() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const userId = user?.user_id;
  const [sessionId, setSessionId]       = useState<string>("");
  const [questions, setQuestions]       = useState<QuizQuestion[]>([]);
  const [passage, setPassage]           = useState<{ bahan1: string; bahan2: string }>({ bahan1: "", bahan2: "" });
  const [answers, setAnswers]           = useState<Record<string, string>>({});
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
    setPassage({ bahan1: "", bahan2: "" });
    setLoading(true);

    try {
      if (retry && retrySessionId) {
        const data = await retryComprehension(retrySessionId, "pemahaman", userId) as StartResponse;
        setSessionId(data.session_id);
        setQuestions(data.questions);
        if (data.questions.length > 0 && data.questions[0].passage) {
          setPassage(splitPassage(data.questions[0].passage));
        }
        setLoading(false);
        return;
      }

      if (!forceNew) {
        const res = await fetch(
          `${API_URL}/comprehension/resume-latest?quiz_type=pemahaman&user_id=${userId}`
        );

        if (res.status === 200) {
          const data = await res.json();
          setSessionId(data.session_id);
          setQuestions(data.questions);

          if (data.questions.length > 0 && data.questions[0].passage) {
            setPassage(splitPassage(data.questions[0].passage));
          }

          setLoading(false);
          return;
        }
      }

      const data = (await startComprehension("pemahaman", userId)) as StartResponse;

      setSessionId(data.session_id);
      setQuestions(data.questions);

      // Parse passage from first question (all questions share the same passage)
      if (data.questions.length > 0 && data.questions[0].passage) {
        setPassage(splitPassage(data.questions[0].passage));
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
        "pemahaman",
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
          <h1>Pemahaman Quiz</h1>
          <p>Baca kedua-dua bahan berikut dengan teliti dan jawab soalan yang diberikan.</p>
        </div>

        {/* Loading */}
        {loading && (
          <div className="chapter-card card-base">
            <p style={{ color: "#888", fontStyle: "italic" }}>Memuatkan soalan...</p>
          </div>
        )}

        {!loading && questions.length > 0 && (
          <>
            {/* ── Bahan 1 ── */}
            <div className="chapter-card card-base" style={{ marginBottom: "20px" }}>
              <div className="chapter-top">BAHAN 1</div>
              <p style={{ lineHeight: "1.8", whiteSpace: "pre-line" }}>{passage.bahan1}</p>
            </div>

            {/* ── Bahan 2 ── */}
            <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
              <div className="chapter-top">BAHAN 2</div>
              <p style={{ lineHeight: "1.8", whiteSpace: "pre-line" }}>{passage.bahan2}</p>
            </div>

            {/* ── Questions ── */}
            {questions.map((q, index) => {
              const fb = getFeedback(q.question_id);

              return (
                <div
                  key={q.question_id}
                  className="chapter-card card-base"
                  style={{ marginBottom: "25px" }}
                >
                  <div className="chapter-top">
                    SOALAN {index + 1}
                    {q.marks && (
                      <span style={{ marginLeft: "8px", fontWeight: "normal" }}>
                        [{q.marks} markah]
                      </span>
                    )}
                  </div>

                  <p>{q.question_text}</p>

                  <div className="text-area-pemahaman">
                    <textarea
                      rows={4}
                      placeholder="Tulis jawapan anda di sini..."
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

                  {/* Per-question feedback after submit */}
                  {fb && (
                    <div
                      style={{
                        marginTop: "12px",
                        padding: "12px",
                        borderRadius: "8px",
                        backgroundColor: fb.marks_awarded === fb.max_marks ? "#f0fdf4" : fb.marks_awarded > 0 ? "#fffbeb" : "#fef2f2",
                        border: `1px solid ${fb.marks_awarded === fb.max_marks ? "#bbf7d0" : fb.marks_awarded > 0 ? "#fde68a" : "#fecaca"}`,
                      }}
                    >
                      {/* Marks awarded */}
                      <p style={{ margin: "0 0 6px", fontSize: "13px", fontWeight: "bold" }}>
                        Markah: {fb.marks_awarded} / {fb.max_marks}
                        {" "}
                        {fb.marks_awarded === fb.max_marks ? "✅" : fb.marks_awarded > 0 ? "🟡" : "❌"}
                      </p>

                      {/* Breakdown */}
                      {Object.keys(fb.breakdown).length > 0 && (
                        <div style={{ margin: "6px 0", fontSize: "12px", color: "#374151" }}>
                          {Object.entries(fb.breakdown).map(([key, val]) => (
                            <span
                              key={key}
                              style={{
                                display: "inline-block",
                                marginRight: "10px",
                                padding: "2px 6px",
                                borderRadius: "4px",
                                backgroundColor: "#f3f4f6",
                              }}
                            >
                              {key}: {val}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Feedback */}
                      {fb.feedback && (
                        <p style={{ margin: "6px 0 0", fontSize: "12px", color: "#6b7280" }}>
                          {fb.feedback}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </>
        )}

        {!loading &&(
          <>
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