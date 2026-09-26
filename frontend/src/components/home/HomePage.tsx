import Layout from "../shared/Layout";
import { useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { getHomeRecommendations } from "../../services/api";
import { useLanguage } from "../../language";

type Difficulty = "easy" | "medium" | "hard";

interface RecommendationItem {
  title: string;
  paper: string;
  route: string;
  icon: string;
  color: "blue" | "green" | "orange";
  reason: string;
}

interface HomeRecommendationResponse {
  mode: "first_time" | "personalized";
  message: string;
  items: RecommendationItem[];
}

const DIFFICULTY_STORAGE_KEY = "selectedDifficulty";

function getSavedDifficulty(): Difficulty {
  const saved = localStorage.getItem(DIFFICULTY_STORAGE_KEY);

  if (saved === "easy" || saved === "medium" || saved === "hard") {
    return saved;
  }

  return "medium";
}

export default function HomePage() {
  const navigate = useNavigate();
  const { t } = useLanguage();

  const [recommendations, setRecommendations] = useState<RecommendationItem[]>([]);
  const [recommendationMessage, setRecommendationMessage] = useState("");
  const [loadingRecommendations, setLoadingRecommendations] = useState(true);

  const [selectedDifficulty, setSelectedDifficulty] =
    useState<Difficulty>(getSavedDifficulty);

  const difficultyLabels: Record<Difficulty, string> = {
    easy: t("easy"),
    medium: t("medium"),
    hard: t("hard"),
  };

  const difficultyDescriptions: Record<Difficulty, string> = {
    easy: t("easyDescription"),
    medium: t("mediumDescription"),
    hard: t("hardDescription"),
  };

  async function loadRecommendations() {
    setLoadingRecommendations(true);

    try {
      const data = (await getHomeRecommendations()) as HomeRecommendationResponse;
      setRecommendations(data.items ?? []);
      setRecommendationMessage(data.message ?? "");
    } catch (error) {
      console.error(error);
      setRecommendations([]);
      setRecommendationMessage(t("recommendationLoadError"));
    } finally {
      setLoadingRecommendations(false);
    }
  }

  function handleDifficultyChange(difficulty: Difficulty) {
    setSelectedDifficulty(difficulty);
    localStorage.setItem(DIFFICULTY_STORAGE_KEY, difficulty);
  }

  function goToPage(route: string) {
    navigate(route);
    window.scrollTo(0, 0);
  }

  function goToLatihan(route: string) {
    localStorage.setItem(DIFFICULTY_STORAGE_KEY, selectedDifficulty);
    navigate(`${route}?difficulty=${selectedDifficulty}`);
    window.scrollTo(0, 0);
  }

  function getLatihanButtonText() {
    return `${t("practice")} ${difficultyLabels[selectedDifficulty]}`;
  }

  useEffect(() => {
    localStorage.setItem(DIFFICULTY_STORAGE_KEY, selectedDifficulty);
  }, [selectedDifficulty]);

  useEffect(() => {
    loadRecommendations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Layout>
      <div className="hero">
        <h1>{t("homeHeroTitle")}</h1>
        <p>{t("homeHeroSubtitle")}</p>
      </div>

      <div className="difficulty-panel card-base">
        <div className="difficulty-panel-text">
          <h3>{t("choosePracticeLevel")}</h3>
          <p>{t("choosePracticeLevelDescription")}</p>
        </div>

        <div className="difficulty-options">
          {(["easy", "medium", "hard"] as Difficulty[]).map((difficulty) => (
            <button
              key={difficulty}
              type="button"
              className={`difficulty-option ${
                selectedDifficulty === difficulty ? "active" : ""
              }`}
              onClick={() => handleDifficultyChange(difficulty)}
            >
              <strong>{difficultyLabels[difficulty]}</strong>
              <span>{difficultyDescriptions[difficulty]}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="selected-difficulty-note">
        {t("currentLevel")}:{" "}
        <strong>{difficultyLabels[selectedDifficulty]}</strong>
      </div>

      <div className="recommendation-header">
        <div>
          <h3>{t("recommendedForYou")}</h3>
          <p className="recommendation-message">{recommendationMessage}</p>
        </div>

        <button className="update-btn" onClick={loadRecommendations}>
          {loadingRecommendations ? t("updating") : t("updateRecommendations")}
        </button>
      </div>

      <div className="recommendations">
        {loadingRecommendations ? (
          <div className="recommend-empty card-base">
            {t("loadingRecommendations")}
          </div>
        ) : recommendations.length > 0 ? (
          recommendations.map((item) => (
            <button
              key={`${item.paper}-${item.title}`}
              className="recommend-card card-base recommend-card-button"
              onClick={() => goToLatihan(item.route)}
            >
              <div className={`recommend-icon ${item.color}`}>{item.icon}</div>

              <div className="recommend-content">
                <small>{item.paper}</small>
                <h4>{item.title}</h4>
                <p>{item.reason}</p>
              </div>
            </button>
          ))
        ) : (
          <div className="recommend-empty card-base">
            {t("noRecommendationAvailable")}
          </div>
        )}
      </div>

      <div className="chapter-header">
        <h3>{t("paper1")}</h3>
      </div>

      <div className="chapters">
        <div className="chapter-card card-base">
          <div className="chapter-card-header">
            <div className="chapter-top">{t("paper1Upper")}</div>
            <span className={`difficulty-badge ${selectedDifficulty}`}>
              {difficultyLabels[selectedDifficulty]}
            </span>
          </div>

          <h2>{t("longEssayTitle")}</h2>
          <p>{t("longEssayDescription")}</p>

          <div className="chapter-actions">
            <button
              className="button1"
              onClick={() => goToPage("/karangan-panjang-contoh")}
            >
              {t("exampleEssay")}
            </button>

            <button
              className="button2"
              onClick={() => goToLatihan("/karangan-panjang-latihan")}
            >
              {getLatihanButtonText()}
            </button>
          </div>
        </div>

        <div className="chapter-card card-base">
          <div className="chapter-card-header">
            <div className="chapter-top">{t("paper1Upper")}</div>
            <span className={`difficulty-badge ${selectedDifficulty}`}>
              {difficultyLabels[selectedDifficulty]}
            </span>
          </div>

          <h2>{t("shortEssayTitle")}</h2>
          <p>{t("shortEssayDescription")}</p>

          <div className="chapter-actions">
            <button
              className="button1"
              onClick={() => goToPage("/karangan-pendek-contoh")}
            >
              {t("exampleEssay")}
            </button>

            <button
              className="button2"
              onClick={() => goToLatihan("/karangan-pendek-latihan")}
            >
              {getLatihanButtonText()}
            </button>
          </div>
        </div>
      </div>

      <div className="chapter-header">
        <h3>{t("paper2")}</h3>
      </div>

      <div className="chapters">
        <div className="chapter-card card-base">
          <div className="chapter-card-header">
            <div className="chapter-top">{t("paper2Upper")}</div>
            <span className={`difficulty-badge ${selectedDifficulty}`}>
              {difficultyLabels[selectedDifficulty]}
            </span>
          </div>

          <h2>{t("golonganKataTitle")}</h2>
          <p>{t("golonganKataDescription")}</p>

          <div className="chapter-actions">
            <button
              className="button1"
              onClick={() => goToPage("/golongan-kata-tips")}
            >
              {t("tipsNotes")}
            </button>

            <button
              className="button2"
              onClick={() => goToLatihan("/golongan-kata-latihan")}
            >
              {getLatihanButtonText()}
            </button>
          </div>
        </div>

        <div className="chapter-card card-base">
          <div className="chapter-card-header">
            <div className="chapter-top">{t("paper2Upper")}</div>
            <span className={`difficulty-badge ${selectedDifficulty}`}>
              {difficultyLabels[selectedDifficulty]}
            </span>
          </div>

          <h2>{t("binaAyatTitle")}</h2>
          <p>{t("binaAyatDescription")}</p>

          <div className="chapter-actions">
            <button
              className="button1"
              onClick={() => goToPage("/bina-ayat-tips")}
            >
              {t("tipsNotes")}
            </button>

            <button
              className="button2"
              onClick={() => goToLatihan("/bina-ayat-latihan")}
            >
              {getLatihanButtonText()}
            </button>
          </div>
        </div>

        <div className="chapter-card card-base">
          <div className="chapter-card-header">
            <div className="chapter-top">{t("paper2Upper")}</div>
            <span className={`difficulty-badge ${selectedDifficulty}`}>
              {difficultyLabels[selectedDifficulty]}
            </span>
          </div>

          <h2>{t("jenisAyatTitle")}</h2>
          <p>{t("jenisAyatDescription")}</p>

          <div className="chapter-actions">
            <button
              className="button1"
              onClick={() => goToPage("/jenis-ayat-tips")}
            >
              {t("tipsNotes")}
            </button>

            <button
              className="button2"
              onClick={() => goToLatihan("/jenis-ayat-latihan")}
            >
              {getLatihanButtonText()}
            </button>
          </div>
        </div>

        <div className="chapter-card card-base">
          <div className="chapter-card-header">
            <div className="chapter-top">{t("paper2Upper")}</div>
            <span className={`difficulty-badge ${selectedDifficulty}`}>
              {difficultyLabels[selectedDifficulty]}
            </span>
          </div>

          <h2>{t("kesalahanBahasaTitle")}</h2>
          <p>{t("kesalahanBahasaDescription")}</p>

          <div className="chapter-actions">
            <button
              className="button1"
              onClick={() => goToPage("/kesalahan-bahasa-tips")}
            >
              {t("tipsNotes")}
            </button>

            <button
              className="button2"
              onClick={() => goToLatihan("/kesalahan-bahasa-latihan")}
            >
              {getLatihanButtonText()}
            </button>
          </div>
        </div>

        <div className="chapter-card card-base">
          <div className="chapter-card-header">
            <div className="chapter-top">{t("paper2Upper")}</div>
            <span className={`difficulty-badge ${selectedDifficulty}`}>
              {difficultyLabels[selectedDifficulty]}
            </span>
          </div>

          <h2>{t("pemahamanTitle")}</h2>
          <p>{t("pemahamanDescription")}</p>

          <div className="chapter-actions">
            <button
              className="button1"
              onClick={() => goToPage("/pemahaman-tips")}
            >
              {t("tipsNotes")}
            </button>

            <button
              className="button2"
              onClick={() => goToLatihan("/pemahaman-latihan")}
            >
              {getLatihanButtonText()}
            </button>
          </div>
        </div>

        <div className="chapter-card card-base">
          <div className="chapter-card-header">
            <div className="chapter-top">{t("paper2Upper")}</div>
            <span className={`difficulty-badge ${selectedDifficulty}`}>
              {difficultyLabels[selectedDifficulty]}
            </span>
          </div>

          <h2>{t("rumusanTitle")}</h2>
          <p>{t("rumusanDescription")}</p>

          <div className="chapter-actions">
            <button
              className="button1"
              onClick={() => goToPage("/rumusan-tips")}
            >
              {t("tipsNotes")}
            </button>

            <button
              className="button2"
              onClick={() => goToLatihan("/rumusan-latihan")}
            >
              {getLatihanButtonText()}
            </button>
          </div>
        </div>
      </div>

      <div className="chapter-header">
        <h3>{t("paper3")}</h3>
      </div>

      <div className="chapters">
        <div className="chapter-card card-base">
          <div className="chapter-card-header">
            <div className="chapter-top">{t("paper3Upper")}</div>
            <span className={`difficulty-badge ${selectedDifficulty}`}>
              {difficultyLabels[selectedDifficulty]}
            </span>
          </div>

          <h2>{t("speakingSectionTitle")}</h2>
          <p>{t("speakingSectionDescription")}</p>

          <div className="chapter-actions">
            <button
              className="button1"
              onClick={() => goToPage("/ujian-bertutur-tips")}
            >
              {t("tipsNotes")}
            </button>

            <button
              className="button2"
              onClick={() => goToLatihan("/ujian-bertutur-latihan")}
            >
              {getLatihanButtonText()}
            </button>
          </div>
        </div>
      </div>

      <div className="chapter-header">
        <h3>{t("paper4")}</h3>
      </div>

      <div className="chapters">
        <div className="chapter-card card-base">
          <div className="chapter-card-header">
            <div className="chapter-top">{t("paper4Upper")}</div>
            <span className={`difficulty-badge ${selectedDifficulty}`}>
              {difficultyLabels[selectedDifficulty]}
            </span>
          </div>

          <h2>{t("listeningSectionTitle")}</h2>
          <p>{t("listeningSectionDescription")}</p>

          <div className="chapter-actions">
            <button
              className="button1"
              onClick={() => goToPage("/ujian-mendengar-tips")}
            >
              {t("tipsNotes")}
            </button>

            <button
              className="button2"
              onClick={() => goToLatihan("/ujian-mendengar-latihan")}
            >
              {getLatihanButtonText()}
            </button>
          </div>
        </div>
      </div>
    </Layout>
  );
}