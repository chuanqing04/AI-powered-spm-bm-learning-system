import Layout from "../../shared/Layout";
import { useLanguage } from "../../../language";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "../../../context/AuthContext";
import {
  startComprehension,
  submitLatihanComprehension,
} from "../../../services/api";

type Difficulty = "easy" | "medium" | "hard";

type GeneratedQuestion = {
  question_id: string;
  question_text: string;
  question_type?: string;
  difficulty?: string;
  options?: string[] | null;
  passage?: string | null;
  marks?: number | null;
};

type StartResponse = {
  session_id: string;
  quiz_type: string;
  questions: GeneratedQuestion[];
};

type QuestionFeedback = {
  question_id: string;
  question_text?: string;
  user_answer?: string;
  correct_answer?: string;
  is_correct?: boolean;
  score?: number;
  marks_awarded?: number;
  max_marks?: number;
  feedback?: string;
};

type PracticeResult = {
  total_score?: number;
  max_score?: number;
  percentage?: number;
  grade?: string;
  question_feedbacks?: QuestionFeedback[];
  overall_feedback?: string;
  suggestions?: string[];
};

const quizType = "jenis_ayat";

function getDifficulty(searchParams: URLSearchParams): Difficulty {
  const value =
    searchParams.get("difficulty") || localStorage.getItem("selectedDifficulty");

  if (value === "easy" || value === "medium" || value === "hard") {
    return value;
  }

  return "medium";
}

export default function JenisAyatLatihanPage() {
  const [searchParams] = useSearchParams();
  const difficulty = getDifficulty(searchParams);

  const { t } = useLanguage();
  const { user } = useAuth();
  const userId = user?.user_id || "guest";

  const [sessionId, setSessionId] = useState("");
  const [questions, setQuestions] = useState<GeneratedQuestion[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<PracticeResult | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isMarking, setIsMarking] = useState(false);
  const [error, setError] = useState("");

  async function loadQuestions() {
    setIsGenerating(true);
    setError("");
    setResult(null);
    setAnswers({});

    try {
      localStorage.setItem("selectedDifficulty", difficulty);

      const data = (await startComprehension(
        quizType,
        userId,
        difficulty,
        "latihan"
      )) as StartResponse;

      if (!data.questions || data.questions.length === 0) {
        throw new Error("No generated questions returned.");
      }

      setSessionId(data.session_id);
      setQuestions(data.questions);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      console.error(err);
      setError(t("essayGenerateError"));
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
    return questions.every((question) => answers[question.question_id]?.trim());
  }

  function getFeedback(questionId: string) {
    return result?.question_feedbacks?.find(
      (feedback) => feedback.question_id === questionId
    );
  }

  async function handleSubmit() {
    if (!allQuestionsAnswered()) {
      setError(t("mustAnswerAllQuestions"));
      return;
    }

    setIsMarking(true);
    setError("");
    setResult(null);

    try {
      const formattedAnswers = questions.map((question) => ({
        question_id: question.question_id,
        answer: answers[question.question_id] || "",
      }));

      const data = (await submitLatihanComprehension(
        sessionId,
        quizType,
        userId,
        formattedAnswers
      )) as PracticeResult;

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

  return (
    <Layout>
      <div className="container no-top-gap">
        <button
          className="update-btn button1"
          onClick={() => window.history.back()}
        >
          {t("backToHome")}
        </button>

        <div className="hero">
          <h1>{t("jenisAyatTitle")}</h1>
          <p>{t("generatedPracticeNotice")}</p>
          <p>
            {t("currentLevel")}: <strong>{t(difficulty)}</strong>
          </p>
        </div>

        {isGenerating && (
          <div className="chapter-card card-base">
            <p style={{ color: "#888", fontStyle: "italic" }}>
              {t("generatingQuestion")}
            </p>
          </div>
        )}

        {!isGenerating &&
          questions.map((question, index) => {
            const feedback = getFeedback(question.question_id);

            return (
              <div
                key={question.question_id}
                className="chapter-card card-base"
                style={{ marginBottom: "25px" }}
              >
                <div className="chapter-top">
                  {t("question")} {index + 1}
                </div>

                {question.passage && (
                  <div style={{ marginBottom: "14px", whiteSpace: "pre-line" }}>
                    {question.passage}
                  </div>
                )}

                <p className="practice-question-text">{question.question_text}</p>

                {question.marks && (
                  <p>
                    [{question.marks} {t("marks")}]
                  </p>
                )}

                {question.options && question.options.length > 0 ? (
                  <div className="select-wrapper" style={{ marginTop: "10px" }}>
                    <select
                      value={answers[question.question_id] || ""}
                      onChange={(event) =>
                        handleAnswerChange(
                          question.question_id,
                          event.target.value
                        )
                      }
                      className="styled-select"
                      disabled={!!result || isMarking}
                    >
                      <option value="">{t("selectAnswer")}</option>
                      {question.options.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                  </div>
                ) : (
                  <div className="text-area-pemahaman">
                    <textarea
                      rows={4}
                      placeholder={t("answerPlaceholder")}
                      value={answers[question.question_id] || ""}
                      disabled={!!result || isMarking}
                      onChange={(event) =>
                        handleAnswerChange(
                          question.question_id,
                          event.target.value
                        )
                      }
                    />
                  </div>
                )}

                {feedback && (
                  <div
                    style={{
                      marginTop: "14px",
                      background: "#f8fafc",
                      padding: "14px",
                      borderRadius: "10px",
                      border: "1px solid #e5e7eb",
                    }}
                  >
                    <p>
                      <strong>{t("yourAnswer")}:</strong>{" "}
                      {feedback.user_answer || t("notAnswered")}
                    </p>

                    {feedback.correct_answer && (
                      <p>
                        <strong>{t("correctAnswer")}:</strong>{" "}
                        {feedback.correct_answer}
                      </p>
                    )}

                    <p>
                      <strong>{t("score")}:</strong>{" "}
                      {feedback.marks_awarded ?? feedback.score ?? 0}
                      {feedback.max_marks ? ` / ${feedback.max_marks}` : " / 1"}
                    </p>

                    {feedback.feedback && (
                      <p>
                        <strong>{t("feedback")}:</strong> {feedback.feedback}
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })}

        {error && (
          <p style={{ color: "red", fontWeight: 600, marginBottom: "12px" }}>
            {error}
          </p>
        )}

        {!result && questions.length > 0 && (
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
              {t("score")}: {result.total_score ?? 0} / {result.max_score ?? 0}
            </h2>

            {typeof result.percentage === "number" && (
              <p>
                <strong>{t("percentage")}:</strong> {result.percentage}%
              </p>
            )}

            {result.grade && (
              <p>
                <strong>{t("grade")}:</strong> {result.grade}
              </p>
            )}

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
                disabled={isGenerating}
              >
                {isGenerating ? t("generatingQuestion") : t("newQuestion")}
              </button>

              <button className="button1" onClick={handleTryAgain}>
                {t("tryAgainButton")}
              </button>
            </div>
          </div>
        )}

        {!isGenerating && questions.length === 0 && (
          <button className="button1" onClick={loadQuestions}>
            {t("newQuestion")}
          </button>
        )}

        <div style={{ marginBottom: "40px" }} />
      </div>
    </Layout>
  );
}