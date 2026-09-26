import { useEffect, useMemo, useState } from "react";
import Layout from "../shared/Layout";
import { getDashboardOverview } from "../../services/api";
import { useLanguage } from "../../language";

interface DashboardTrendPoint {
  date?: string;
  label: string;
  title: string;
  percentage: number;
  grade: string;
  attempts?: number;
  full_date?: string;
  topics?: string[];
}

interface DashboardBreakdownItem {
  quiz_type: string;
  title: string;
  average_percentage: number;
  attempts: number;
}

interface DashboardOverview {
  user_id: string;
  summary: {
    average_score: number | null;
    total_questions: number;
    grade_predictor: string | null;
    predicted_percentage: number | null;
    confidence: "low" | "medium" | "high";
    total_attempts: number;
  };
  trend: DashboardTrendPoint[];
  breakdown: DashboardBreakdownItem[];
  latest_result: {
    title: string;
    percentage: number;
    grade: string;
    saved_at: string;
  } | null;
}

type ChartPoint = DashboardTrendPoint & {
  x: number;
  y: number;
};

function SimpleTrendChart({ points }: { points: DashboardTrendPoint[] }) {
  const chartWidth = 760;
  const chartHeight = 250;
  const padding = 28;
  const [hoveredPoint, setHoveredPoint] = useState<ChartPoint | null>(null);

  const coordinates = useMemo<ChartPoint[]>(() => {
    if (!points.length) return [];
    const stepX =
      points.length === 1 ? 0 : (chartWidth - padding * 2) / (points.length - 1);

    return points.map((point, index) => {
      const x = points.length === 1 ? chartWidth / 2 : padding + index * stepX;
      const y =
        chartHeight -
        padding -
        (point.percentage / 100) * (chartHeight - padding * 2);

      return { ...point, x, y };
    });
  }, [points]);

  const polyline = coordinates.map((point) => `${point.x},${point.y}`).join(" ");
  const yLines = [0, 25, 50, 75, 100];

  return (
    <div className="trend-chart-shell">
      <div className="trend-chart-wrap">
        <svg
          viewBox={`0 0 ${chartWidth} ${chartHeight}`}
          className="trend-chart-svg"
          onMouseLeave={() => setHoveredPoint(null)}
        >
          {yLines.map((value) => {
            const y =
              chartHeight - padding - (value / 100) * (chartHeight - padding * 2);

            return (
              <g key={value}>
                <line
                  x1={padding}
                  y1={y}
                  x2={chartWidth - padding}
                  y2={y}
                  className="trend-grid-line"
                />
                <text x={10} y={y + 4} className="trend-axis-label">
                  {value}
                </text>
              </g>
            );
          })}

          {coordinates.length > 1 && (
            <polyline points={polyline} className="trend-line" />
          )}

          {coordinates.map((point) => (
            <g key={`${point.label}-${point.title}-${point.percentage}`}>
              <circle
                cx={point.x}
                cy={point.y}
                r={12}
                className="trend-dot-hit-area"
                onMouseEnter={() => setHoveredPoint(point)}
                onFocus={() => setHoveredPoint(point)}
                tabIndex={0}
              />
              <circle cx={point.x} cy={point.y} r={5} className="trend-dot" />
              <text
                x={point.x}
                y={chartHeight - 8}
                textAnchor="middle"
                className="trend-axis-label"
              >
                {point.label}
              </text>
            </g>
          ))}
        </svg>

        {hoveredPoint && (
          <div
            className="trend-tooltip"
            style={{
              left: `${(hoveredPoint.x / chartWidth) * 100}%`,
              top: `${(hoveredPoint.y / chartHeight) * 100}%`,
            }}
          >
            <strong>{hoveredPoint.full_date ?? hoveredPoint.label}</strong>
            <span>{hoveredPoint.percentage}% daily average</span>
            <span>Grade {hoveredPoint.grade}</span>
            <span>{hoveredPoint.attempts ?? 1} attempt(s)</span>
            {hoveredPoint.topics?.length ? (
              <small>{hoveredPoint.topics.join(", ")}</small>
            ) : null}
          </div>
        )}
      </div>

      <div className="trend-legend">
        {points.map((point, index) => (
          <div key={`${point.label}-${index}`} className="trend-legend-item">
            <strong>{point.full_date ?? point.label}</strong>
            <span>
              {point.percentage}% daily average • {point.grade}
            </span>
            <span>{point.attempts ?? 1} attempt(s)</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { t } = useLanguage();

  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    let mounted = true;

    async function loadDashboard() {
      setLoading(true);
      setHasError(false);

      try {
        const data = (await getDashboardOverview()) as DashboardOverview;
        if (mounted) setOverview(data);
      } catch (err) {
        console.error(err);
        if (mounted) {
          setHasError(true);
        }
      } finally {
        if (mounted) setLoading(false);
      }
    }

    loadDashboard();

    return () => {
      mounted = false;
    };
  }, []);

  const topStrength = overview?.breakdown[0] ?? null;
  const improvementArea =
    overview && overview.breakdown.length > 1
      ? overview.breakdown[overview.breakdown.length - 1]
      : null;

  return (
    <Layout>
      <div className="dashboard-header">
        <h1>{t("dashboardTitle")}</h1>
        <p>{t("dashboardSubtitle")}</p>
      </div>

      {loading && (
        <div className="performance-panel card-base">
          <div className="performance-placeholder">{t("dashboardLoading")}</div>
        </div>
      )}

      {!loading && hasError && (
        <div className="performance-panel card-base">
          <div className="performance-placeholder">{t("dashboardLoadError")}</div>
        </div>
      )}

      {!loading && !hasError && overview && (
        <>
          <div className="dashboard-top-grid">
            <div className="dashboard-top-card card-base">
              <div className="dashboard-icon purple">📊</div>
              <div>
                <p className="dashboard-label">{t("averageQuizScore")}</p>
                <h2>
                  {overview.summary.average_score !== null
                    ? `${overview.summary.average_score}%`
                    : "-"}
                </h2>
              </div>
            </div>

            <div className="dashboard-top-card card-base">
              <div className="dashboard-icon green">💡</div>
              <div>
                <p className="dashboard-label">{t("totalQuestions")}</p>
                <h2>{overview.summary.total_questions}</h2>
              </div>
            </div>

            <div className="dashboard-top-card card-base">
              <div className="dashboard-icon gray">🎯</div>
              <div>
                <p className="dashboard-label">{t("gradePredictor")}</p>
                <h2>{overview.summary.grade_predictor ?? "-"}</h2>
                <p className="dashboard-subtext">
                  {t("basedOnRecentQuizPerformance")}
                </p>
              </div>
            </div>
          </div>

          <div className="performance-panel card-base">
            <div className="dashboard-section-head">
              <div>
                <h2>{t("performanceTrend")}</h2>
                <p className="dashboard-subtext">Daily average score by date</p>
              </div>
              <span>
                {overview.summary.total_attempts} {t("attemptsSaved")}
              </span>
            </div>

            {overview.trend.length ? (
              <SimpleTrendChart points={overview.trend} />
            ) : (
              <div className="performance-placeholder">
                {t("noQuizHistory")}
              </div>
            )}
          </div>

          <div className="dashboard-bottom-grid">
            <div className="dashboard-info-card card-base">
              <h3>{t("quickInsight")}</h3>
              {overview.latest_result ? (
                <>
                  <p>
                    {t("latestResult")}: <strong>{overview.latest_result.title}</strong>{" "}
                    {t("scored")} <strong>{overview.latest_result.percentage}%</strong>{" "}
                    {t("withGrade")} <strong>{overview.latest_result.grade}</strong>.
                  </p>
                  <p>
                    {t("savedOn")} {overview.latest_result.saved_at}.
                  </p>
                </>
              ) : (
                <p>{t("noResultSaved")}</p>
              )}
            </div>

            <div className="dashboard-info-card card-base">
              <h3>{t("strengthVsFocusArea")}</h3>
              <p>
                {t("strongestTopic")}: <strong>{topStrength?.title ?? "-"}</strong>
                {topStrength
                  ? ` (${topStrength.average_percentage}% ${t("average")})`
                  : ""}
              </p>

              <p>
                {t("focusNextOn")}:{" "}
                <strong>{improvementArea?.title ?? topStrength?.title ?? "-"}</strong>
                {improvementArea
                  ? ` (${improvementArea.average_percentage}% ${t("average")})`
                  : ""}
              </p>
            </div>
          </div>
        </>
      )}
    </Layout>
  );
}