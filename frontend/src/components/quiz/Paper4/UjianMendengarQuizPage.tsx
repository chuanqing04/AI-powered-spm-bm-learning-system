import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useLanguage } from "../../../language";
import { useAuth } from "../../../context/AuthContext";
import Layout from "../../shared/Layout";
import {startListening, submitListening, retryListening, type ListeningAnswer,} from "../../../services/api";

import { API_BASE_URL } from "../../../services/config";
const BASE_BACKEND_URL = API_BASE_URL;

type Difficulty = "easy" | "medium" | "hard";
type QuestionType = "short_answer" | "mcq" | "true_false";

type ListeningQuestion = {
  question_id: string;
  question_text: string;
  question_type: QuestionType;
  marks: number;
  options?: string[] | null;
};

type ListeningPetikan = {
  title: string;
  questions: ListeningQuestion[];
};

type Feedback = {
  question_id: string;
  question_text: string;
  user_answer: string;
  correct_answer: string;
  marks_awarded: number;
  max_marks: number;
  feedback: string;
};

type Result = {
  total_score: number;
  max_score: number;
  percentage: number;
  grade: string;
  question_feedbacks: Feedback[];
  overall_feedback: string;
  suggestions: string[];
};

function getSelectedDifficulty(searchParams: URLSearchParams): Difficulty {
  const fromUrl = searchParams.get("difficulty");
  const fromStorage = localStorage.getItem("selectedDifficulty");

  const value = fromUrl || fromStorage;

  if (value === "easy" || value === "medium" || value === "hard") {
    return value;
  }

  return "medium";
}

export default function UjianMendengarQuizPage() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const [searchParams] = useSearchParams();

  const difficulty = getSelectedDifficulty(searchParams);
  const userId = user?.user_id;

  const [sessionId, setSessionId] = useState("");
  const [tema, setTema] = useState("");
  const [audioUrl, setAudioUrl] = useState("");
  const [petikans, setPetikans] = useState<ListeningPetikan[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Result | null>(null);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const lastTimeRef = useRef(0);
  const [audioDuration, setAudioDuration] = useState<number>(0);
  const [audioPlayed, setAudioPlayed] = useState<boolean>(false);
  const [audioPlaying, setAudioPlaying] = useState<boolean>(false);

  const calledOnce = useRef(false);

  const handleChange = (questionId: string, value: string) => {
    setAnswers((prev) => ({
      ...prev,
      [questionId]: value,
    }));
  };

  const getFeedbackForQuestion = (questionId: string) => {
    return result?.question_feedbacks?.find(
      (fb) => fb.question_id === questionId
    );
  };

  const fetchListeningTest = async (forceNew = false, retry = false, retrySessionId?: string) => {
    if (!userId) {
      setError("User not logged in");
      setLoading(false);
      return;
    }
    
    try {
      setLoading(true);
      setError("");
      setResult(null);
      setAnswers({});
      setPetikans([]);
      setSessionId("");

      localStorage.setItem("selectedDifficulty", difficulty);

      // ── Retry session ───────────────────────────────────────────────
      if (retry && retrySessionId) {
        const data = await retryListening(retrySessionId, "mendengar", userId) as {
          session_id: string;
          tema: string;
          audio_url: string;
          petikans: ListeningPetikan[];
        };
        setSessionId(data.session_id);
        setTema(data.tema || "");
        setAudioUrl(`${BASE_BACKEND_URL}${data.audio_url}`);
        setPetikans(data.petikans || []);
        setLoading(false);
        return;
      }

      // ── Resume latest ───────────────────────────────────────────────
      if (!forceNew) {
        const res = await fetch(
          `${BASE_BACKEND_URL}/api/listening/resume-latest?quiz_type=mendengar&user_id=${userId}`
        );

        if (res.status === 200) {
          const data = await res.json();
          setSessionId(data.session_id);
          setTema(data.tema || "");
          setAudioUrl(`${BASE_BACKEND_URL}${data.audio_url}`);
          setPetikans(data.petikans || []);
          setLoading(false);
          return;
        }
      }

      // ── Start new session ───────────────────────────────────────────      
      const data = await startListening("mendengar", userId, difficulty);

      setSessionId(data.session_id);
      setTema(data.tema || "");
      setAudioUrl(`${BASE_BACKEND_URL}${data.audio_url}`);
      setPetikans(data.petikans || []);
    } catch (err) {
      console.error(err);
      setError("Gagal menjana Ujian Mendengar. Sila cuba semula.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit() {
    if (!userId) return;

    // Flatten all questions from all petikans
    const allQuestions = petikans.flatMap((p) => p.questions);

    const unanswered = allQuestions.filter((q) => {
      const ans = answers[q.question_id];
      return !ans?.trim();
    });

    if (unanswered.length > 0) {
      setError(
        `Sila lengkapkan semua soalan sebelum menghantar. ` +
        `(${unanswered.length} soalan belum dijawab)`
      );
      return;
    }

    try {
      setSubmitting(true);
      setError("");

      const formattedAnswers: ListeningAnswer[] = Object.entries(answers).map(
        ([question_id, answer]) => ({
          question_id,
          answer,
        })
      );

      const data = await submitListening(
        sessionId,
        "mendengar",
        userId,
        formattedAnswers
      );

      setResult(data);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      console.error(err);
      setError("Gagal menghantar jawapan. Sila cuba semula.");
    } finally {
      setSubmitting(false);
    }
  }

  function handleCubaLagi() {
    setAnswers({});
    setResult(null);
    setError("");
    fetchListeningTest(false, true, sessionId);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function handleSoalanBaharu() {
    await fetchListeningTest(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  useEffect(() => {
    if (!userId || calledOnce.current) return;
    calledOnce.current = true;
    fetchListeningTest();
  }, [userId]);

  if (loading) {
    return (
      <Layout>
        <div>
          <button
            className="update-btn button1"
            onClick={() => window.history.back()}
          >
            {t("back")}
          </button>
        </div>

        <div className="page-header">
          <h1>Ujian Mendengar Quiz</h1>
          <p>Menjana skrip, soalan dan audio Ujian Mendengar...</p>
        </div>

        <div className="chapter-card card-base">
          <p>Sila tunggu sebentar. Audio sedang dijana menggunakan TTS.</p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      {/* BACK */}
      <div>
        <button
          className="update-btn button1"
          onClick={() => window.history.back()}
        >
          {t("back")}
        </button>
      </div>

      {/* HEADER */}
      <div className="hero">
        <h1>Ujian Mendengar Quiz</h1>
        <p>Dengar audio dan jawab semua soalan.</p>

        {tema && (
          <p>
            <strong>Tema:</strong> {tema}
          </p>
        )}
      </div>

      {/* AUDIO */}
      {audioUrl && petikans.length > 0 && (
        <div className="chapter-card card-base">
          <h2>Audio</h2>

        <audio
          ref={audioRef}
          src={audioUrl}
          onLoadedMetadata={() => {
            if (audioRef.current) {
              setAudioDuration(audioRef.current.duration);
            }
          }}
          onPlay={() => setAudioPlaying(true)}
          onEnded={() => {
            setAudioPlaying(false);
            setAudioPlayed(true);
          }}
          onTimeUpdate={() => {
            if (audioRef.current && audioRef.current.currentTime > lastTimeRef.current + 0.5) {
              audioRef.current.currentTime = lastTimeRef.current;
            } else if (audioRef.current && !audioRef.current.paused) {
              lastTimeRef.current = audioRef.current.currentTime;
            }
          }}
        />

        <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "8px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <button
              className="button1"
              disabled={audioPlaying || audioPlayed}
              onClick={() => {
                if (audioRef.current && audioRef.current.paused) {
                  audioRef.current.play();
                }
              }}
            >
              {audioPlayed
                ? "✔ Audio Telah Dimainkan"
                : audioPlaying
                ? "🔊 Sedang Dimainkan..."
                : "▶ Main Audio"}
            </button>

            {audioDuration > 0 && (
              <span style={{ fontSize: "13px", color: "#6b7280" }}>
                Tempoh: {Math.floor(audioDuration / 60)}:{String(Math.floor(audioDuration % 60)).padStart(2, "0")}
              </span>
            )}
          </div>

          <p style={{ fontSize: "13px", color: "#6b7280", margin: 0 }}>
            Audio hanya boleh dimainkan sekali tanpa maju pantas atau undur.
          </p>
        </div>

          {/* <audio
            controls
            controlsList="nodownload noplaybackrate"
            onContextMenu={(e) => e.preventDefault()}
            style={{ width: "100%" }}
          >
            <source src={audioUrl} type="audio/mpeg" />
            Browser anda tidak menyokong audio.
          </audio> */}

          <p style={{ marginTop: "10px" }}>
            *Sila main audio sebelum menjawab.
          </p>
        </div>
      )}

      {/* PETIKAN */}
      {petikans.map((p, i) => (
        <div
          key={i}
          className="chapter-card card-base"
          style={{ marginTop: "30px" }}
        >
          <h2>{p.title}</h2>

          {p.questions.map((q, j) => {
            const feedback = getFeedbackForQuestion(q.question_id);

            return (
              <div key={q.question_id} style={{ marginBottom: "25px" }}>
                <p>
                  <strong>{j + 1}.</strong> {q.question_text} [{q.marks} markah]
                </p>

                {q.question_type === "mcq" && q.options ? (
                  q.options.map((opt) => (
                    <label
                      key={opt}
                      style={{ display: "block", marginBottom: "8px" }}
                    >
                      <input
                        type="radio"
                        name={q.question_id}
                        checked={answers[q.question_id] === opt[0]}
                        onChange={() => handleChange(q.question_id, opt[0])}
                        disabled={!!result}
                      />{" "}
                      {opt}
                    </label>
                  ))
                ) : q.question_type === "true_false" ? (
                  <>
                    <label style={{ display: "block", marginBottom: "8px" }}>
                      <input
                        type="radio"
                        name={q.question_id}
                        checked={answers[q.question_id] === "BETUL"}
                        onChange={() => handleChange(q.question_id, "BETUL")}
                        disabled={!!result}
                      />{" "}
                      BETUL
                    </label>

                    <label style={{ display: "block", marginBottom: "8px" }}>
                      <input
                        type="radio"
                        name={q.question_id}
                        checked={answers[q.question_id] === "SALAH"}
                        onChange={() => handleChange(q.question_id, "SALAH")}
                        disabled={!!result}
                      />{" "}
                      SALAH
                    </label>
                  </>
                ) : (
                  <textarea
                    style={{ width: "100%", minHeight: "80px" }}
                    value={answers[q.question_id] || ""}
                    onChange={(e) => handleChange(q.question_id, e.target.value)}
                    disabled={!!result}
                  />
                )}

                {/* RESULT DIRECTLY UNDER THIS QUESTION */}
                {feedback && (
                  <div
                    style={{
                      marginTop: "12px",
                      padding: "10px",
                      borderRadius: "8px",
                      backgroundColor: feedback.marks_awarded === feedback.max_marks ? "#f0fdf4" : feedback.marks_awarded > 0 ? "#fefce8" : "#fef2f2",
                      border: `1px solid ${feedback.marks_awarded === feedback.max_marks ? "#bbf7d0" : feedback.marks_awarded > 0 ? "#fde68a" : "#fecaca"}`,
                    }}
                  >
                    <p style={{ margin: "0 0 4px", fontSize: "13px" }}>
                      {feedback.marks_awarded === feedback.max_marks ? "✅" : feedback.marks_awarded > 0 ? "🟡" : "❌"}{" "}
                      <strong>
                        {feedback.marks_awarded === feedback.max_marks ? "Betul!" : feedback.marks_awarded > 0 ? "Separa Betul" : "Salah"}
                      </strong>
                      <span style={{ marginLeft: "8px", color: "#6b7280", fontSize: "12px" }}>
                        ({feedback.marks_awarded} / {feedback.max_marks} markah)
                      </span>
                    </p>

                    {feedback.marks_awarded < feedback.max_marks && feedback.correct_answer && (
                      <p style={{ margin: "8px 0 0", fontSize: "12px" }}>
                        <strong>Jawapan betul: </strong>
                        <span style={{ color: "#166534" }}>{feedback.correct_answer}</span>
                      </p>
                    )}

                    {feedback.feedback && (
                      <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#6b7280" }}>
                        {feedback.feedback}
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ))}

      {/* Error */}
      {error && <p style={{ color: "red" }}>{error}</p>}

      {/* Submit button */}  
      {!result && (
        <button
          className="button1"
          onClick={error && petikans.length === 0 ? () => {
            setError("");
            calledOnce.current = false;
            fetchListeningTest(true);
          } : handleSubmit}
          disabled={submitting}
          style={{ marginTop: "20px" }}
        >
          {submitting
            ? t("markingAnswer")
            : error && petikans.length === 0
            ? t("TryAgain")
            : t("checkAnswer")
          }
        </button>
      )}

      {/* RESULT SUMMARY ONLY */}
      {result && (
        <>
          {/* Score breakdown table */}
          <div className="card-base" style={{ marginTop: "24px", padding: "24px", marginBottom: "20px" }}>

            {/* Grade banner */}
            <div style={{ textAlign: "center", marginBottom: "24px" }}>
              <h2 style={{ fontSize: "2rem", margin: 0 }}>Gred: {result.grade}</h2>
              <p style={{ fontSize: "1.1rem", color: "#555" }}>
                Markah: {result.total_score} / {result.max_score}
                {" "}({result.percentage}%)
              </p>
            </div>

            <hr />

            {/* Overall feedback */}
            <div style={{ marginTop: "20px" }}>
              <h3>Maklum Balas Keseluruhan</h3>
              <p style={{ lineHeight: "1.7", color: "#333" }}>{result.overall_feedback}</p>
            </div>

            <hr />

            {/* Suggestions */}
            {result.suggestions?.length > 0 && (
              <div style={{ marginTop: "20px" }}>
                <h3>Cadangan Penambahbaikan</h3>
                <ul style={{ paddingLeft: "20px", lineHeight: "1.8" }}>
                  {result.suggestions.map((s, i) => (
                    <li key={i} style={{ color: "#333", marginBottom: "6px" }}>{s}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Buttons */}
            <div style={{ marginTop: "24px", display: "flex", gap: "12px", justifyContent: "center" }}>
              <button className="button1" onClick={handleCubaLagi}>
                {t("TryAgain")}
              </button>
              <button className="button1" onClick={handleSoalanBaharu}>
                {t("generateMoreQuestionsButton")}
              </button>
            </div>
          </div>
        </>
      )}

      <div style={{ marginBottom: "40px" }} />
    </Layout>
  );
}