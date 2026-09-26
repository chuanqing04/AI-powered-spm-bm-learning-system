import Layout from "../../shared/Layout";
import { useLanguage } from "../../../language";
import { useSearchParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { useAuth } from "../../../context/AuthContext";
import {
  markLatihanEssay,
  startEssay,
  type LatihanEssayMarkResponse,
} from "../../../services/api";

type Difficulty = "easy" | "medium" | "hard";

interface EssayTask {
  instruction: string;
  source?: string;
  stimulus: string[];
  question: string;
  placeholder: string;
}

type EssayStartResponse = {
  session_id: string;
  quiz_type: string;
  title: string;
  description: string;
  instructions: string;
  questions: {
    question_id: string;
    question_text: string;
    question_type: string;
    difficulty: string;
    options?: string[] | null;
    passage?: string | null;
  }[];
};

function getDifficulty(searchParams: URLSearchParams): Difficulty {
  const value =
    searchParams.get("difficulty") ||
    localStorage.getItem("selectedDifficulty");

  if (value === "easy" || value === "medium" || value === "hard") {
    return value;
  }

  return "medium";
}

export default function KaranganPanjangLatihanPage() {
  const [searchParams] = useSearchParams();
  const difficulty = getDifficulty(searchParams);

  const { t } = useLanguage();
  const { user } = useAuth();

  const userId = user?.user_id || "guest";

  const [task, setTask] = useState<EssayTask | null>(null);
  const [answer, setAnswer] = useState("");
  const [isMarking, setIsMarking] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [result, setResult] = useState<LatihanEssayMarkResponse | null>(null);
  const [error, setError] = useState("");

  const [isGeneratedQuestion, setIsGeneratedQuestion] = useState(false);
  const [hasAttemptedGeneratedQuestion, setHasAttemptedGeneratedQuestion] =
    useState(false);

  const mustAttemptBeforeNew =
    isGeneratedQuestion && !hasAttemptedGeneratedQuestion && !result;

  async function loadGeneratedQuestion() {
    if (mustAttemptBeforeNew) {
      setError(t("mustAttemptBeforeNewQuestion"));
      return;
    }

    setError("");
    setResult(null);
    setAnswer("");
    setIsGenerating(true);

    try {
      localStorage.setItem("selectedDifficulty", difficulty);

      const response = (await startEssay(
        "karangan_panjang",
        userId,
        difficulty,
        "latihan"
      )) as EssayStartResponse;

      const generatedQuestion = response.questions?.[0]?.question_text;

      if (!generatedQuestion) {
        throw new Error(t("generatedQuestionError"));
      }

      setTask({
        instruction: t("longGeneratedInstruction"),
        stimulus: [t("generatedPracticeNotice")],
        question: generatedQuestion,
        placeholder: t("longGeneratedPlaceholder"),
      });

      setIsGeneratedQuestion(true);
      setHasAttemptedGeneratedQuestion(false);

      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setError(err instanceof Error ? err.message : t("essayGenerateError"));
    } finally {
      setIsGenerating(false);
    }
  }

  useEffect(() => {
    loadGeneratedQuestion();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSubmit() {
    setError("");
    setResult(null);

    if (!task) {
      setError(t("generatedQuestionError"));
      return;
    }

    if (!answer.trim()) {
      setError(t("emptyEssayError"));
      return;
    }

    if (answer.trim().split(/\s+/).length < 50) {
      setError(t("longEssayTooShortError"));
      return;
    }

    setIsMarking(true);

    try {
      const marking = await markLatihanEssay({
        essay_type: "karangan_panjang",
        difficulty,
        question: task.question,
        answer,
      });

      setResult(marking);

      if (isGeneratedQuestion) {
        setHasAttemptedGeneratedQuestion(true);
      }

      setTimeout(() => {
        window.scrollTo({
          top: document.body.scrollHeight,
          behavior: "smooth",
        });
      }, 100);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("essayMarkError"));
    } finally {
      setIsMarking(false);
    }
  }

  async function handleSoalanBaharu() {
    await loadGeneratedQuestion();
  }

  function handleCubaLagi() {
    setAnswer("");
    setResult(null);
    setError("");

    if (isGeneratedQuestion) {
      setHasAttemptedGeneratedQuestion(false);
    }

    window.scrollTo({ top: 0, behavior: "smooth" });
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
        <h1>
          {t("longEssayPracticeTitle")} - {t(difficulty)}
        </h1>

        <p>{task?.instruction || t("generatingQuestion")}</p>

        {task?.source && <p>{task.source}</p>}

        <p>
          {t("currentLevel")}: <strong>{t(difficulty)}</strong>
          {task?.stimulus.map((line, index) => <p key={index}>{line}</p>)}
        </p>
      </div>

      <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
        {isGenerating ? (
          <p style={{ color: "#888", fontStyle: "italic" }}>{t("generatingQuestion")}</p>
        ) : (
          <>
            {task?.question && (
              <div style={{ lineHeight: "1.8", textAlign: "justify" }}>
                {(() => {
                  const lines = task.question.split("\n");
                  const firstLine = lines[0]?.trim() ?? "";
                  const isTitle = firstLine.length < 80 && !firstLine.endsWith(".");

                  return lines.map((line, i) => {
                    const trimmed = line.trim();

                    if (!trimmed) return <div key={i} style={{ marginBottom: "12px" }} />;

                    if (trimmed.startsWith("Sumber:")) {
                      return (
                        <p key={i} style={{ color: "#6b7280", fontStyle: "italic", margin: "4px 0 8px 0", fontSize: "0.9rem" }}>
                          {trimmed}
                        </p>
                      );
                    }

                    if (i === 0 && isTitle) {
                      return (
                        <p key={i} style={{ fontWeight: "bold", fontSize: "1.05rem", marginBottom: "10px" }}>
                          {trimmed}
                        </p>
                      );
                    }

                    const prevLine = lines[i - 1]?.trim() ?? "";
                    const isAfterSpacer = prevLine === "" || prevLine.startsWith("Sumber:");
                    if (isAfterSpacer) {
                      return (
                        <p key={i} style={{ margin: "4px 0", fontWeight: "500" }}>
                          {trimmed}
                        </p>
                      );
                    }

                    return <p key={i} style={{ margin: "4px 0", color: "#333" }}>{trimmed}</p>;
                  });
                })()}
              </div>
            )}
          </>
        )}
      </div>

      <div className="text-area-karangan">
        <textarea
          placeholder={task?.placeholder || t("longGeneratedPlaceholder")}
          value={answer}
          disabled={isMarking || isGenerating || !task}
          onChange={(e) => {
            setAnswer(e.target.value);
            setResult(null);
            setError("");

            if (isGeneratedQuestion) {
              setHasAttemptedGeneratedQuestion(false);
            }
          }}
        />
      </div>

      <div style={{ marginTop: "10px" }}>
        <small>
          {t("wordCount")}:{" "}
          {answer.trim() ? answer.trim().split(/\s+/).length : 0}
        </small>
      </div>

      {error && (
        <div
          className="chapter-card card-base"
          style={{ marginTop: "20px", color: "#b91c1c" }}
        >
          {error}
        </div>
      )}

      {!result && (
        <button
          className="button1"
          style={{ marginTop: "20px" }}
          onClick={error && !task ? () => {
            setError("");
            loadGeneratedQuestion();
          } : handleSubmit}
          disabled={isMarking || isGenerating || (!task && !error)}
        >
          {isMarking
            ? t("markingEssay")
            : error && !task
            ? t("newQuestion")
            : t("submitEssay")
          }
        </button>
      )}

      {result && (
        <div
          className="chapter-card card-base"
          style={{
            marginTop: "25px",
            marginBottom: "25px",
            padding: "24px",
          }}
        >
          <h2>{t("essayResultTitle")}</h2>

          <p>
            <strong>{t("score")}:</strong> {result.mark} / {result.max_mark}
          </p>

          <p>
            <strong>{t("percentage")}:</strong> {result.percentage}%
          </p>

          <p>
            <strong>{t("grade")}:</strong> {result.grade}
          </p>

          <p>
            <strong>{t("wordCount")}:</strong> {result.word_count}
          </p>

          <p>
            <strong>{t("topicRelevance")}:</strong>{" "}
            {result.relevance.percentage}%
          </p>

          {result.relevance.is_off_topic && (
            <p style={{ color: "#b91c1c", fontWeight: 700 }}>
              {t("offTopicWarning")}
            </p>
          )}

          <hr />

          <h3>{t("essayFeedback")}</h3>
          <p>{result.feedback}</p>

          <h3>{t("improvementSuggestions")}</h3>
          <ol>
            {result.suggestions.map((suggestion, index) => (
              <li key={index}>{suggestion}</li>
            ))}
          </ol>

          <h3>{t("rubric")}</h3>

          <p>
            {t("rubricContent")}: {result.rubric.content_score}
          </p>
          <p>
            {t("rubricLanguage")}: {result.rubric.language_score}
          </p>
          <p>
            {t("rubricGrammar")}: {result.rubric.grammar_score}
          </p>
          <p>
            {t("rubricVocabulary")}: {result.rubric.vocabulary_score}
          </p>
          <p>
            {t("rubricCoherence")}: {result.rubric.coherence_score}
          </p>

          <div
            style={{
              display: "flex",
              gap: "12px",
              justifyContent: "center",
              alignItems: "center",
              flexWrap: "wrap",
              marginTop: "20px",
            }}
          >
            <button
              className="button1"
              onClick={handleSoalanBaharu}
              disabled={isGenerating || mustAttemptBeforeNew}
            >
              {isGenerating ? t("generatingQuestion") : t("newQuestion")}
            </button>

            <button className="button1" onClick={handleCubaLagi}>
              {t("tryAgainButton")}
            </button>
          </div>
        </div>
      )}

      <div style={{ marginBottom: "40px" }} />
    </Layout>
  );
}