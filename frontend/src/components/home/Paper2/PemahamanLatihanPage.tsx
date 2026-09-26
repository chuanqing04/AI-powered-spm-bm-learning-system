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

type DisplayQuestion = GeneratedQuestion & {
  display_question_text: string;
  display_marks?: number | null;
};

type PemahamanDisplay = {
  bahan1: string;
  bahan2: string;
  questions: DisplayQuestion[];
};

const quizType = "pemahaman";

function getDifficulty(searchParams: URLSearchParams): Difficulty {
  const value =
    searchParams.get("difficulty") || localStorage.getItem("selectedDifficulty");

  if (value === "easy" || value === "medium" || value === "hard") {
    return value;
  }

  return "medium";
}

function cleanMarksFromText(text: string): string {
  return text
    .replace(/\[\s*\d+\s*(?:marks?|markah)\s*\]/gi, "")
    .trim();
}

function extractMarks(text: string): number | null {
  const match = text.match(/\[\s*(\d+)\s*(?:marks?|markah)\s*\]/i);
  return match ? Number(match[1]) : null;
}

function looksLikeQuestion(text: string): boolean {
  const cleaned = text.trim();

  return (
    cleaned.includes("?") ||
    /^(berikan|nyatakan|jelaskan|huraikan|apakah|mengapakah|bagaimanakah|kenal pasti|bandingkan|senaraikan|tulis|pilih)/i.test(cleaned)
  );
}

function splitMarkedPemahamanText(text: string): {
  bahan1: string;
  bahan2: string;
  questionText: string;
  marks: number | null;
} {
  const normalised = text.replace(/\r\n/g, "\n");
  const marks = extractMarks(normalised);

  const bahan1Match = normalised.match(/\[BAHAN_?1\]\s*\n([\s\S]*?)(?=\n\s*\[BAHAN_?2\])/i);
  const bahan2Match = normalised.match(/\[BAHAN_?2\]\s*\n([\s\S]*)/i);

  if (!bahan1Match || !bahan2Match) {
    return {
      bahan1: "",
      bahan2: "",
      questionText: cleanMarksFromText(normalised),
      marks,
    };
  }

  const bahan1 = bahan1Match[1].trim();
  const afterBahan2 = bahan2Match[1].trim();

  const blocks = afterBahan2
    .split(/\n\s*\n/g)
    .map((block) => block.trim())
    .filter(Boolean)
    .filter((block) => !/^\[\s*\d+\s*(?:marks?|markah)\s*\]$/i.test(block));

  let questionIndex = -1;

  for (let i = blocks.length - 1; i >= 0; i -= 1) {
    if (looksLikeQuestion(blocks[i])) {
      questionIndex = i;
      break;
    }
  }

  if (questionIndex === -1) {
    questionIndex = Math.max(blocks.length - 1, 0);
  }

  const bahan2 = blocks.slice(0, questionIndex).join("\n\n").trim();
  const questionText = cleanMarksFromText(blocks[questionIndex] || "");

  return {
    bahan1,
    bahan2,
    questionText,
    marks,
  };
}

function splitPassageOnly(passage: string): { bahan1: string; bahan2: string } {
  const normalised = passage.replace(/\r\n/g, "\n");

  const bahan1Match = normalised.match(/\[BAHAN_?1\]\s*\n([\s\S]*?)(?=\n\s*\[BAHAN_?2\])/i);
  const bahan2Match = normalised.match(/\[BAHAN_?2\]\s*\n([\s\S]*)/i);

  return {
    bahan1: bahan1Match ? bahan1Match[1].trim() : "",
    bahan2: bahan2Match ? bahan2Match[1].trim() : "",
  };
}

function buildPemahamanDisplay(questions: GeneratedQuestion[]): PemahamanDisplay {
  if (questions.length === 0) {
    return {
      bahan1: "",
      bahan2: "",
      questions: [],
    };
  }

  let bahan1 = "";
  let bahan2 = "";

  const firstQuestion = questions[0];

  if (firstQuestion.passage) {
    const splitPassage = splitPassageOnly(firstQuestion.passage);
    bahan1 = splitPassage.bahan1;
    bahan2 = splitPassage.bahan2;
  }

  const displayQuestions = questions.map((question, index) => {
    const parsed = splitMarkedPemahamanText(question.question_text);

    if (index === 0) {
      if (!bahan1 && parsed.bahan1) {
        bahan1 = parsed.bahan1;
      }

      if (!bahan2 && parsed.bahan2) {
        bahan2 = parsed.bahan2;
      }
    }

    return {
      ...question,
      display_question_text: parsed.questionText || cleanMarksFromText(question.question_text),
      display_marks: question.marks ?? parsed.marks,
    };
  });

  return {
    bahan1,
    bahan2,
    questions: displayQuestions,
  };
}

export default function PemahamanLatihanPage() {
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

  const pemahamanDisplay = buildPemahamanDisplay(questions);

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
          <h1>{t("pemahamanTitle")}</h1>
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

        {!isGenerating && pemahamanDisplay.bahan1 && (
          <div className="chapter-card card-base" style={{ marginBottom: "20px" }}>
            <div className="chapter-top">BAHAN 1</div>
            <p style={{ lineHeight: "1.8", whiteSpace: "pre-line" }}>
              {pemahamanDisplay.bahan1}
            </p>
          </div>
        )}

        {!isGenerating && pemahamanDisplay.bahan2 && (
          <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
            <div className="chapter-top">BAHAN 2</div>
            <p style={{ lineHeight: "1.8", whiteSpace: "pre-line" }}>
              {pemahamanDisplay.bahan2}
            </p>
          </div>
        )}

        {!isGenerating &&
          pemahamanDisplay.questions.map((question, index) => {
            const feedback = getFeedback(question.question_id);

            return (
              <div
                key={question.question_id}
                className="chapter-card card-base"
                style={{ marginBottom: "25px" }}
              >
                <div className="chapter-top">
                  SOALAN {index + 1}
                  {question.display_marks && (
                    <span style={{ marginLeft: "8px", fontWeight: "normal" }}>
                      [{question.display_marks} markah]
                    </span>
                  )}
                </div>

                <p className="practice-question-text">
                  {question.display_question_text}
                </p>

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
                      placeholder="Tulis jawapan anda di sini..."
                      value={answers[question.question_id] || ""}
                      disabled={!!result || isMarking}
                      onChange={(event) =>
                        handleAnswerChange(
                          question.question_id,
                          event.target.value
                        )
                      }
                      style={{ opacity: result ? 0.7 : 1 }}
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
                      {feedback.max_marks ? " / " + feedback.max_marks : " / 1"}
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
