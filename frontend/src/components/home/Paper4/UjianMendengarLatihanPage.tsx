import Layout from "../../shared/Layout";
import { useLanguage } from "../../../language";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "../../../context/AuthContext";
import { API_BASE_URL } from "../../../services/config";
import {
  startListening,
  submitLatihanListening,
  type ListeningAnswer,
} from "../../../services/api";

const BASE_BACKEND_URL = API_BASE_URL;

type Difficulty = "easy" | "medium" | "hard";

type ListeningQuestionType = "short_answer" | "mcq" | "true_false";

type ListeningQuestion = {
  question_id: string;
  question_text: string;
  question_type: ListeningQuestionType;
  marks: number;
  options?: string[] | null;
};

type ListeningPetikan = {
  title: string;
  questions: ListeningQuestion[];
};

type ListeningStartResponse = {
  session_id: string;
  task_type: string;
  tema: string;
  audio_url: string;
  petikans: ListeningPetikan[];
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
  const value =
    searchParams.get("difficulty") || localStorage.getItem("selectedDifficulty");

  if (value === "easy" || value === "medium" || value === "hard") {
    return value;
  }

  return "medium";
}

export default function UjianMendengarLatihanPage() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const [searchParams] = useSearchParams();

  const difficulty = getSelectedDifficulty(searchParams);
  const userId = user?.user_id || "guest";

  const [sessionId, setSessionId] = useState("");
  const [tema, setTema] = useState("");
  const [audioUrl, setAudioUrl] = useState("");
  const [petikans, setPetikans] = useState<ListeningPetikan[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<Result | null>(null);

  const [isGenerating, setIsGenerating] = useState(false);
  const [isMarking, setIsMarking] = useState(false);
  const [error, setError] = useState("");

  async function loadQuestions() {
    setIsGenerating(true);
    setError("");
    setResult(null);
    setAnswers({});
    setPetikans([]);
    setAudioUrl("");
    setTema("");

    try {
      localStorage.setItem("selectedDifficulty", difficulty);

      const data = (await startListening(
        "mendengar",
        userId,
        difficulty,
        "latihan"
      )) as ListeningStartResponse;

      setSessionId(data.session_id);
      setTema(data.tema || "");
      setAudioUrl(`${BASE_BACKEND_URL}${data.audio_url}`);
      setPetikans(data.petikans || []);

      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      console.error(err);
      setError("Gagal menjana soalan mendengar. Sila cuba semula.");
    } finally {
      setIsGenerating(false);
    }
  }

  useEffect(() => {
    loadQuestions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleAnswerChange(questionId: string, value: string) {
    setAnswers((prev) => ({
      ...prev,
      [questionId]: value,
    }));

    setResult(null);
    setError("");
  }

  function allQuestionsAnswered() {
    return petikans.every((petikan) =>
      petikan.questions.every((question) => answers[question.question_id]?.trim())
    );
  }

  function getFeedback(questionId: string) {
    return result?.question_feedbacks?.find(
      (feedback) => feedback.question_id === questionId
    );
  }

  async function handleSubmit() {
    if (!sessionId) {
      setError("Sesi latihan belum tersedia. Sila jana soalan semula.");
      return;
    }

    if (!allQuestionsAnswered()) {
      setError(t("mustAnswerAllQuestions"));
      return;
    }

    setIsMarking(true);
    setError("");
    setResult(null);

    try {
      const formattedAnswers: ListeningAnswer[] = [];

      petikans.forEach((petikan) => {
        petikan.questions.forEach((question) => {
          formattedAnswers.push({
            question_id: question.question_id,
            answer: answers[question.question_id] || "",
          });
        });
      });

      const data = (await submitLatihanListening(
        sessionId,
        "mendengar",
        userId,
        formattedAnswers
      )) as Result;

      setResult(data);

      setTimeout(() => {
        window.scrollTo({
          top: document.body.scrollHeight,
          behavior: "smooth",
        });
      }, 100);
    } catch (err) {
      console.error(err);
      setError(t("essayMarkError"));
    } finally {
      setIsMarking(false);
    }
  }

  function handleTryAgain() {
    setAnswers({});
    setResult(null);
    setError("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function renderAnswerInput(question: ListeningQuestion) {
    const value = answers[question.question_id] || "";
    const disabled = !!result || isMarking || isGenerating;

    if (question.question_type === "mcq" && question.options) {
      return (
        <div style={{ marginTop: "10px" }}>
          {question.options.map((option) => (
            <label
              key={option}
              style={{
                display: "block",
                marginBottom: "8px",
              }}
            >
              <input
                type="radio"
                name={question.question_id}
                checked={value === option[0]}
                disabled={disabled}
                onChange={() =>
                  handleAnswerChange(question.question_id, option[0])
                }
              />{" "}
              {option}
            </label>
          ))}
        </div>
      );
    }

    if (question.question_type === "true_false") {
      return (
        <div style={{ marginTop: "10px" }}>
          <label style={{ display: "block", marginBottom: "8px" }}>
            <input
              type="radio"
              name={question.question_id}
              checked={value === "BETUL"}
              disabled={disabled}
              onChange={() =>
                handleAnswerChange(question.question_id, "BETUL")
              }
            />{" "}
            BETUL
          </label>

          <label style={{ display: "block", marginBottom: "8px" }}>
            <input
              type="radio"
              name={question.question_id}
              checked={value === "SALAH"}
              disabled={disabled}
              onChange={() =>
                handleAnswerChange(question.question_id, "SALAH")
              }
            />{" "}
            SALAH
          </label>
        </div>
      );
    }

    return (
      <textarea
        style={{ width: "100%", minHeight: "80px" }}
        value={value}
        disabled={disabled}
        placeholder={t("answerPlaceholder")}
        onChange={(event) =>
          handleAnswerChange(question.question_id, event.target.value)
        }
      />
    );
  }

  return (
    <Layout>
      <div>
        <button
          className="update-btn button1"
          onClick={() => window.history.back()}
        >
          {t("backToHome")}
        </button>
      </div>

      <div className="page-header">
        <h1>{t("listeningPracticeTitle")}</h1>

        <p>{t("generatedPracticeNotice")}</p>

        {tema && (
          <p>
            <strong>Tema:</strong> {tema}
          </p>
        )}

        <p>
          {t("currentLevel")}: <strong>{t(difficulty)}</strong>
        </p>
      </div>

      {isGenerating && (
        <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
          <p style={{ color: "#888", fontStyle: "italic" }}>
            {t("generatingQuestion")}
          </p>
        </div>
      )}

      {!isGenerating && audioUrl && (
        <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
          <h2>{t("audio")}</h2>

          <audio controls style={{ width: "100%" }}>
            <source src={audioUrl} type="audio/mpeg" />
          </audio>

          <p style={{ marginTop: "10px" }}>{t("listenBeforeAnswering")}</p>
        </div>
      )}

      {!isGenerating &&
        petikans.map((petikan) => (
          <div
            key={petikan.title}
            className="chapter-card card-base"
            style={{ marginTop: "30px" }}
          >
            <h2>{petikan.title}</h2>

            {petikan.questions.map((question, questionIndex) => {
              const feedback = getFeedback(question.question_id);

              return (
                <div key={question.question_id} style={{ marginBottom: "28px" }}>
                  <p>
                    <strong>{questionIndex + 1}.</strong>{" "}
                    {question.question_text} [{question.marks} {t("marks")}]
                  </p>

                  {renderAnswerInput(question)}

                  {feedback && (
                    <div
                      style={{
                        marginTop: "12px",
                        padding: "14px",
                        borderRadius: "10px",
                        background: "#f8fafc",
                        border: "1px solid #dbeafe",
                      }}
                    >
                      <p>
                        <strong>{t("yourAnswer")}:</strong>{" "}
                        {feedback.user_answer || t("notAnswered")}
                      </p>

                      <p>
                        <strong>{t("correctAnswer")}:</strong>{" "}
                        {feedback.correct_answer}
                      </p>

                      <p>
                        <strong>{t("score")}:</strong>{" "}
                        {feedback.marks_awarded} / {feedback.max_marks}
                      </p>

                      <p style={{ marginBottom: 0 }}>
                        <strong>{t("feedback")}:</strong> {feedback.feedback}
                      </p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ))}

      {error && (
        <p style={{ color: "red", fontWeight: 600, marginBottom: "12px" }}>
          {error}
        </p>
      )}

      {!result && petikans.length > 0 && (
        <button
          className="button1"
          onClick={handleSubmit}
          disabled={isMarking || isGenerating}
          style={{ marginTop: "20px" }}
        >
          {isMarking ? t("markingAnswer") : t("submitAnswers")}
        </button>
      )}

      {result && (
        <div
          className="chapter-card card-base"
          style={{ marginTop: "25px", marginBottom: "25px" }}
        >
          <div className="chapter-top">{t("paper2PracticeResult")}</div>

          <h2>
            {t("score")}: {result.total_score} / {result.max_score}
          </h2>

          <p>
            <strong>{t("percentage")}:</strong> {result.percentage}%
          </p>

          <p>
            <strong>{t("grade")}:</strong> {result.grade}
          </p>

          {result.overall_feedback && (
            <>
              <h3>{t("overallFeedback")}</h3>
              <p>{result.overall_feedback}</p>
            </>
          )}

          {result.suggestions && result.suggestions.length > 0 && (
            <>
              <h3>{t("improvementSuggestions")}</h3>
              <ol>
                {result.suggestions.map((suggestion, index) => (
                  <li key={index}>{suggestion}</li>
                ))}
              </ol>
            </>
          )}

          <div
            style={{
              display: "flex",
              gap: "12px",
              justifyContent: "center",
              alignItems: "center",
              flexWrap: "wrap",
              marginTop: "18px",
            }}
          >
            <button
              className="button1"
              onClick={loadQuestions}
              disabled={isGenerating || isMarking}
            >
              {isGenerating ? t("generatingQuestion") : t("newQuestion")}
            </button>

            <button className="button1" onClick={handleTryAgain}>
              {t("tryAgainButton")}
            </button>
          </div>
        </div>
      )}

      {!isGenerating && petikans.length === 0 && (
        <button className="button1" onClick={loadQuestions}>
          {t("newQuestion")}
        </button>
      )}

      <div style={{ marginBottom: "40px" }} />
    </Layout>
  );
}