import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { useLanguage, type Language } from "../../language";

export default function Navbar() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const { language, setLanguage, t } = useLanguage();

  const profileInitial = user?.email?.trim().charAt(0).toUpperCase() || "U";

  function handleLanguageChange(nextLanguage: Language) {
    setLanguage(nextLanguage);
  }

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <div className="logo">
          <Link
            to="/"
            className={location.pathname === "/" ? "active" : ""}
          >
            <img src="/book icon.png" alt="EasyLearn Logo" className="logo-img" />
            EasyLearn
          </Link>
        </div>

        <div className="nav-center">
          <Link
            to="/"
            className={location.pathname === "/" ? "active" : ""}
          >
            {t("home")}
          </Link>

          <Link
            to="/quiz"
            className={location.pathname === "/quiz" ? "active" : ""}
          >
            {t("quiz")}
          </Link>

          <Link
            to="/dashboard"
            className={location.pathname === "/dashboard" ? "active" : ""}
          >
            {t("dashboard")}
          </Link>
        </div>

        <div className="nav-right">
          <div className="language-switch" aria-label={t("languageLabel")}>
            <button
              type="button"
              className={language === "en" ? "active" : ""}
              onClick={() => handleLanguageChange("en")}
            >
              {t("english")}
            </button>

            <button
              type="button"
              className={language === "bm" ? "active" : ""}
              onClick={() => handleLanguageChange("bm")}
            >
              {t("bahasaMelayu")}
            </button>
          </div>

          <div className="nav-auth">
            {user ? (
              <div className="user-box">
                {user.picture ? (
                  <img
                    src={user.picture}
                    alt={user.email}
                    title={user.email}
                    className="profile-avatar-img"
                    referrerPolicy="no-referrer"
                  />
                ) : (
                  <span
                    className="profile-avatar-fallback"
                    title={user.email}
                    aria-label={`Signed in as ${user.email}`}
                  >
                    {profileInitial}
                  </span>
                )}

                <button
                  type="button"
                  className="logout-icon-btn"
                  onClick={logout}
                  title={t("logout")}
                  aria-label={t("logout")}
                >
                  <svg
                    className="logout-svg"
                    viewBox="0 0 24 24"
                    fill="none"
                    aria-hidden="true"
                  >
                    <path
                      d="M10 17L15 12L10 7"
                      stroke="currentColor"
                      strokeWidth="2.2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    <path
                      d="M15 12H3"
                      stroke="currentColor"
                      strokeWidth="2.2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                    <path
                      d="M12 3H19C20.1046 3 21 3.89543 21 5V19C21 20.1046 20.1046 21 19 21H12"
                      stroke="currentColor"
                      strokeWidth="2.2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </button>
              </div>
            ) : (
              <div className="user-placeholder">{t("pleaseSignIn")}</div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}