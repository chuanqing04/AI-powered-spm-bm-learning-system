import Layout from "../shared/Layout";
// import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useLanguage } from "../../language";

// type Difficulty = "easy" | "medium" | "hard";

// const DIFFICULTY_STORAGE_KEY = "selectedDifficulty";

// function getSavedDifficulty(): Difficulty {
//   const saved = localStorage.getItem(DIFFICULTY_STORAGE_KEY);
//   return saved === "easy" || saved === "medium" || saved === "hard" ? saved : "medium";
// }

export default function QuizPage() {
  const navigate = useNavigate();
  const { t } = useLanguage();

  // const [selectedDifficulty, setSelectedDifficulty] = useState<Difficulty>(getSavedDifficulty);

  // const difficultyLabels: Record<Difficulty, string> = {
  //   easy: t("easy"),
  //   medium: t("medium"),
  //   hard: t("hard"),
  // };

  // const difficultyDescriptions: Record<Difficulty, string> = {
  //   easy: t("easyDescription"),
  //   medium: t("mediumDescription"),
  //   hard: t("hardDescription"),
  // };

  // function handleDifficultyChange(difficulty: Difficulty) {
  //   setSelectedDifficulty(difficulty);
  //   localStorage.setItem(DIFFICULTY_STORAGE_KEY, difficulty);
  // }

  function goToQuiz(route: string) {
    // localStorage.setItem(DIFFICULTY_STORAGE_KEY, selectedDifficulty);
    // navigate(`${route}?difficulty=${selectedDifficulty}`);
    navigate(route);
    window.scrollTo(0, 0);
  }

  // useEffect(() => {
  //   localStorage.setItem(DIFFICULTY_STORAGE_KEY, selectedDifficulty);
  // }, [selectedDifficulty]);

  return (
    <Layout>
      <div className="quiz-page">
        <div className="quiz-header">
          <h1>{t("quizPageTitle")}</h1>
          <p>{t("quizPageSubtitle")}</p>
        </div>

        {/* <div className="difficulty-panel card-base">
          <div className="difficulty-panel-text">
            <h3>{t("chooseQuizLevel")}</h3>
            <p>{t("chooseQuizLevelDescription")}</p>
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
          {t("currentQuizLevel")}: <strong>{difficultyLabels[selectedDifficulty]}</strong>
        </div> */}

        <div className="quiz-section">
          <h2 className="section-title">{t("paper1Writing")}</h2>

          <div className="quiz-list">
            <div className="quiz-card card-base">
              {/* <span className={`difficulty-badge ${selectedDifficulty}`}>
                {difficultyLabels[selectedDifficulty]}
              </span> */}
              <h3>{t("karanganPendek")}</h3>
              <p>{t("karanganPendekMeta")}</p>
              <button
                className="quiz-btn"
                onClick={() => goToQuiz("/karangan-pendek-quiz")}
              >
                {t("start")}
              </button>
            </div>

            <div className="quiz-card card-base">
              {/* <span className={`difficulty-badge ${selectedDifficulty}`}>
                {difficultyLabels[selectedDifficulty]}
              </span> */}
              <h3>{t("karanganPanjang")}</h3>
              <p>{t("karanganPanjangMeta")}</p>
              <button
                className="quiz-btn"
                onClick={() => goToQuiz("/karangan-panjang-quiz")}
              >
                {t("start")}
              </button>
            </div>
          </div>
        </div>

        <div className="quiz-section">
          <h2 className="section-title">{t("paper2GrammarReading")}</h2>

          <div className="quiz-list">
            <div className="quiz-card card-base">
              {/* <span className={`difficulty-badge ${selectedDifficulty}`}>
                {difficultyLabels[selectedDifficulty]}
              </span> */}
              <h3>{t("quizGolonganKata")}</h3>
              <p>{t("quizGolonganKataMeta")}</p>
              <button
                className="quiz-btn"
                onClick={() => goToQuiz("/golongan-kata-quiz")}
              >
                {t("start")}
              </button>
            </div>

            <div className="quiz-card card-base">
              {/* <span className={`difficulty-badge ${selectedDifficulty}`}>
                {difficultyLabels[selectedDifficulty]}
              </span> */}
              <h3>{t("quizBinaAyat")}</h3>
              <p>{t("quizBinaAyatMeta")}</p>
              <button
                className="quiz-btn"
                onClick={() => goToQuiz("/bina-ayat-quiz")}
              >
                {t("start")}
              </button>
            </div>

            <div className="quiz-card card-base">
              {/* <span className={`difficulty-badge ${selectedDifficulty}`}>
                {difficultyLabels[selectedDifficulty]}
              </span> */}
              <h3>{t("quizJenisAyat")}</h3>
              <p>{t("quizJenisAyatMeta")}</p>
              <button
                className="quiz-btn"
                onClick={() => goToQuiz("/jenis-ayat-quiz")}
              >
                {t("start")}
              </button>
            </div>

            <div className="quiz-card card-base">
              {/* <span className={`difficulty-badge ${selectedDifficulty}`}>
                {difficultyLabels[selectedDifficulty]}
              </span> */}
              <h3>{t("quizKesalahanBahasa")}</h3>
              <p>{t("quizKesalahanBahasaMeta")}</p>
              <button
                className="quiz-btn"
                onClick={() => goToQuiz("/kesalahan-bahasa-quiz")}
              >
                {t("start")}
              </button>
            </div>

            <div className="quiz-card card-base">
              {/* <span className={`difficulty-badge ${selectedDifficulty}`}>
                {difficultyLabels[selectedDifficulty]}
              </span> */}
              <h3>{t("quizPemahaman")}</h3>
              <p>{t("quizPemahamanMeta")}</p>
              <button
                className="quiz-btn"
                onClick={() => goToQuiz("/pemahaman-quiz")}
              >
                {t("start")}
              </button>
            </div>

            <div className="quiz-card card-base">
              {/* <span className={`difficulty-badge ${selectedDifficulty}`}>
                {difficultyLabels[selectedDifficulty]}
              </span> */}
              <h3>{t("quizRumusan")}</h3>
              <p>{t("quizRumusanMeta")}</p>
              <button
                className="quiz-btn"
                onClick={() => goToQuiz("/rumusan-quiz")}
              >
                {t("start")}
              </button>
            </div>
          </div>
        </div>

        <div className="quiz-section">
          <h2 className="section-title">{t("paper3Speaking")}</h2>

          <div className="quiz-list">
            <div className="quiz-card card-base">
              {/* <span className={`difficulty-badge ${selectedDifficulty}`}>
                {difficultyLabels[selectedDifficulty]}
              </span> */}
              <h3>{t("quizUjianBertutur")}</h3>
              <p>{t("quizUjianBertuturMeta")}</p>
              <button
                className="quiz-btn"
                onClick={() => goToQuiz("/ujian-bertutur-quiz")}
              >
                {t("start")}
              </button>
            </div>
          </div>
        </div>

        <div className="quiz-section">
          <h2 className="section-title">{t("paper4Listening")}</h2>

          <div className="quiz-list">
            <div className="quiz-card card-base">
              {/* <span className={`difficulty-badge ${selectedDifficulty}`}>
                {difficultyLabels[selectedDifficulty]}
              </span> */}
              <h3>{t("quizUjianMendengar")}</h3>
              <p>{t("quizUjianMendengarMeta")}</p>
              <button
                className="quiz-btn"
                onClick={() => goToQuiz("/ujian-mendengar-quiz")}
              >
                {t("start")}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}