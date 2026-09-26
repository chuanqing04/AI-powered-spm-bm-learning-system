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

type RumusanIsi = {
  isi_number: number;
  isi_text: string;
  bahan_sumber: string;
  marks_awarded: number;
  reason: string;
};

type PracticeResult = {
  session_id?: string;
  quiz_type?: string;
  isi_list?: RumusanIsi[];
  isi_score?: number;
  isi_count?: number;
  bahan_coverage?: Record<string, number>;
  bahasa_score?: number;
  bahasa_feedback?: string;
  total_score?: number;
  max_score?: number;
  percentage?: number;
  grade?: string;
  word_count?: number;
  overall_feedback?: string;
  suggestions?: string[];
};

type RumusanMaterial = {
  label: string;
  content: string[];
};

const quizType = "rumusan";

function getDifficulty(searchParams: URLSearchParams): Difficulty {
  const value =
    searchParams.get("difficulty") || localStorage.getItem("selectedDifficulty");

  if (value === "easy" || value === "medium" || value === "hard") {
    return value;
  }

  return "medium";
}

function countWords(text: string): number {
  return text
    .trim()
    .split(/\s+/)
    .filter(Boolean).length;
}

function splitGeneratedMaterials(passage?: string | null): RumusanMaterial[] {
  if (!passage) return [];

  const parts = passage
    .split(/\[(BAHAN_1|BAHAN_2|BAHAN_3)\]/g)
    .map((part) => part.trim())
    .filter(Boolean);

  const materials: RumusanMaterial[] = [];

  for (let i = 0; i < parts.length; i += 2) {
    const label = parts[i]
      .replace("BAHAN_1", "BAHAN 1")
      .replace("BAHAN_2", "BAHAN 2")
      .replace("BAHAN_3", "BAHAN 3");

    const content = parts[i + 1]
      ? parts[i + 1]
          .split("\n")
          .map((line) => line.trim())
          .filter(Boolean)
      : [];

    materials.push({
      label,
      content,
    });
  }

  if (!materials.length) {
    return [
      {
        label: "BAHAN",
        content: [passage],
      },
    ];
  }

  return materials;
}

export default function RumusanLatihanPage() {
  const [searchParams] = useSearchParams();
  const difficulty = getDifficulty(searchParams);

  const { t } = useLanguage();
  const { user } = useAuth();
  const userId = user?.user_id || "guest";

  const [sessionId, setSessionId] = useState("");
  const [question, setQuestion] = useState<GeneratedQuestion | null>(null);
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<PracticeResult | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isMarking, setIsMarking] = useState(false);
  const [error, setError] = useState("");

  const materials = splitGeneratedMaterials(question?.passage);

  async function loadQuestion() {
    setIsGenerating(true);
    setError("");
    setResult(null);
    setAnswer("");

    try {
      localStorage.setItem("selectedDifficulty", difficulty);

      const data = (await startComprehension(
        quizType,
        userId,
        difficulty,
        "latihan"
      )) as StartResponse;

      if (!data.questions || data.questions.length === 0) {
        throw new Error("No generated question returned.");
      }

      setSessionId(data.session_id);
      setQuestion(data.questions[0]);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      console.error(err);
      setError(t("essayGenerateError"));
    } finally {
      setIsGenerating(false);
    }
  }

  useEffect(() => {
    loadQuestion();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSubmit() {
    if (!question) {
      setError(t("essayGenerateError"));
      return;
    }

    if (!answer.trim()) {
      setError(t("emptyEssayError"));
      return;
    }

    setIsMarking(true);
    setError("");
    setResult(null);

    try {
      const data = (await submitLatihanComprehension(
        sessionId,
        quizType,
        userId,
        [
          {
            question_id: question.question_id,
            answer,
          },
        ]
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
    setAnswer("");
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
          <h1>{t("rumusanTitle")}</h1>
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
          materials.map((material) => (
            <div
              key={material.label}
              className="chapter-card card-base"
              style={{ marginBottom: "22px" }}
            >
              <div className="chapter-top">{material.label}</div>

              {material.content.map((paragraph, index) => (
                <p key={index}>{paragraph}</p>
              ))}
            </div>
          ))}

        {!isGenerating && question && (
          <div className="chapter-card card-base">
            <div className="chapter-top">{t("question")} 1</div>

            <p className="practice-question-text">{question.question_text}</p>

            {question.marks && (
              <p>
                [{question.marks} {t("marks")}]
              </p>
            )}

            <div className="text-area-pemahaman">
              <textarea
                rows={8}
                placeholder={t("answerPlaceholder")}
                value={answer}
                disabled={!!result || isMarking}
                onChange={(event) => {
                  setAnswer(event.target.value);
                  setResult(null);
                  setError("");
                }}
              />
            </div>

            <p style={{ marginTop: "8px" }}>
              {t("wordCount")}: {countWords(answer)}
            </p>
          </div>
        )}

        {error && (
          <p style={{ color: "red", fontWeight: 600, marginBottom: "12px" }}>
            {error}
          </p>
        )}

        {!result && question && (
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

            {typeof result.word_count === "number" && (
              <p>
                <strong>{t("wordCount")}:</strong> {result.word_count}
              </p>
            )}

            {typeof result.isi_score === "number" && (
              <p>
                <strong>Isi:</strong> {result.isi_score}
              </p>
            )}

            {typeof result.bahasa_score === "number" && (
              <p>
                <strong>Bahasa:</strong> {result.bahasa_score}
              </p>
            )}

            {result.bahasa_feedback && (
              <>
                <h3>{t("feedback")}</h3>
                <p>{result.bahasa_feedback}</p>
              </>
            )}

            {result.overall_feedback && (
              <>
                <h3>{t("overallFeedback")}</h3>
                <p>{result.overall_feedback}</p>
              </>
            )}

            {result.isi_list && result.isi_list.length > 0 && (
              <>
                <h3>Isi</h3>
                <ol>
                  {result.isi_list.map((isi) => (
                    <li key={isi.isi_number}>
                      <strong>{isi.bahan_sumber}:</strong> {isi.isi_text}
                      <br />
                      {isi.reason}
                    </li>
                  ))}
                </ol>
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
                onClick={loadQuestion}
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

        {!isGenerating && !question && (
          <button className="button1" onClick={loadQuestion}>
            {t("newQuestion")}
          </button>
        )}

        <div style={{ marginBottom: "40px" }} />
      </div>
    </Layout>
  );
}