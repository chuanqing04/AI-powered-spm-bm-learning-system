import Layout from "../../shared/Layout";
import { useLanguage } from "../../../language";
import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "../../../context/AuthContext";
import {
  startSpeaking,
  submitLatihanSpeaking,
} from "../../../services/api";

type Difficulty = "easy" | "medium" | "hard";

type QuestionItem = {
  id: "bacaan" | "r1" | "r2" | "k1" | "k2";
  title: string;
  text: string;
  category: "bacaan" | "rangsangan" | "kbat";
  audioFile: File | Blob | null;
};

type SpeakingStartResponse = {
  session_id: string;
  task_type: string;
  tema: string;
  stimulus_text: string;
  soalan_rangsangan: {
    question_id: string;
    question_text: string;
  }[];
  soalan_kbat: {
    question_id: string;
    question_text: string;
  }[];
};

type WerResult = {
  strict: number;
  spoken_only: number;
  completeness: number;
}

type SpeakingResult = {
  bacaan_wer: WerResult | null;
  total_score: number;
  overall_band: number;
  overall_descriptor: string;

  grammar_vocabulary: {
    score: number;
    reason: string;
    per_clip: {
      clip_id: string;
      score: number;
      reason: string;
    }[];
  };

  pronunciation: {
    score: number;
    reason: string;
    per_clip: {
      clip_id: string;
      score: number;
      reason: string;
      metrics: any;
    }[];
  };

  fluency: {
    score: number;
    reason: string;
    per_clip: {
      clip_id: string;
      score: number;
      reason: string;
      metrics: any;
    }[];
  };

  ideas: {
    score: number;
    reason: string;
    per_question: {
      clip_id: string;
      question_id: string;
      question_text: string;
      category: string;
      score: number;
      reason: string;
    }[];
  };

  clips: {
    clip_id: string;
    transcription: string;
    no_speech: boolean;
    no_speech_reason: string | null;
    wer: WerResult | null;
  }[];
}


function getSelectedDifficulty(searchParams: URLSearchParams): Difficulty {
  const fromUrl = searchParams.get("difficulty");
  const fromStorage = localStorage.getItem("selectedDifficulty");

  const value = fromUrl || fromStorage;

  if (value === "easy" || value === "medium" || value === "hard") {
    return value;
  }

  return "medium";
}

export default function UjianBertuturLatihanPage() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const [searchParams] = useSearchParams();

  const difficulty = getSelectedDifficulty(searchParams);
  const userId = user?.user_id || "guest";

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const [sessionId, setSessionId] = useState("");
  const [stimulus, setStimulus] = useState("");
  const [soalanRangsangan, setSoalanRangsangan] = useState<any[]>([]);
  const [soalanKbat, setSoalanKbat] = useState<any[]>([]);
  const [questions, setQuestions] = useState<QuestionItem[]>([]);

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [recordingId, setRecordingId] = useState<string | null>(null);
  const [result, setResult] = useState<SpeakingResult | null>(null);
  const [error, setError] = useState("");

  const MIN_AUDIO_SECS = 3.0;
  const MAX_AUDIO_SECS = 300.0;

  const [audioWarning, setAudioWarning] = useState<Record<string, string>>({});

  async function loadQuestions() {
    setLoading(true);
    setError("");
    setResult(null);
    setStimulus("");
    setSoalanRangsangan([]);
    setSoalanKbat([]);
    setQuestions([]);
    setAudioWarning({});

    try {
      localStorage.setItem("selectedDifficulty", difficulty);

      const data = (await startSpeaking(
        "lisan",
        userId,
        difficulty,
        "latihan"
      )) as SpeakingStartResponse;

      setSessionId(data.session_id);
      setStimulus(data.stimulus_text);
      setSoalanRangsangan(data.soalan_rangsangan);
      setSoalanKbat(data.soalan_kbat);

      setQuestions([
        {
          id: "bacaan",
          title: "Bacaan Mekanis",
          text: data.stimulus_text,
          category: "bacaan",
          audioFile: null,
        },
        {
          id: "r1",
          title: "Soalan Rangsangan 1",
          text: data.soalan_rangsangan[0]?.question_text || "",
          category: "rangsangan",
          audioFile: null,
        },
        {
          id: "r2",
          title: "Soalan Rangsangan 2",
          text: data.soalan_rangsangan[1]?.question_text || "",
          category: "rangsangan",
          audioFile: null,
        },
        {
          id: "k1",
          title: "Soalan KBAT 1",
          text: data.soalan_kbat[0]?.question_text || "",
          category: "kbat",
          audioFile: null,
        },
        {
          id: "k2",
          title: "Soalan KBAT 2",
          text: data.soalan_kbat[1]?.question_text || "",
          category: "kbat",
          audioFile: null,
        },
      ]);

      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      console.error(err);
      setError("Gagal menjana soalan ujian bertutur. Sila cuba lagi.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadQuestions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function updateAudioFile(questionId: QuestionItem["id"], file: File | Blob | null) {
    setQuestions((prev) =>
      prev.map((question) =>
        question.id === questionId
          ? {
              ...question,
              audioFile: file,
            }
          : question
      )
    );

    setError("");
  }

  const validateAudioDuration = (
    file: Blob,
    onInvalid: (msg: string) => void
  ): Promise<boolean> => {
    return new Promise((resolve) => {
      const url = URL.createObjectURL(file);
      const audio = new Audio(url);

      audio.onloadedmetadata = () => {
        const duration = audio.duration;

        if (duration < MIN_AUDIO_SECS) {
          onInvalid("Rakaman terlalu pendek. Sila rakam semula (min 3 saat).");
          resolve(false);
          return;
        }

        if (duration > MAX_AUDIO_SECS) {
          onInvalid("Rakaman terlalu panjang. Sila ringkaskan (maks 5 minit).");
          resolve(false);
          return;
        }

        resolve(true);
      };
    });
  };

  async function startRecording(questionId: QuestionItem["id"]) {
    setAudioWarning((prev) => ({
      ...prev,
      [questionId]: "",
    }));

    try {
      if (recordingId) {
        stopRecording();
      }

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);

      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        chunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, {
          type: "audio/webm",
        });

        const isValid = await validateAudioDuration(
          blob,
          (msg) => {
            setAudioWarning((prev) => ({
              ...prev,
              [questionId]: msg,
            }));

            setError(msg);
          }
        );

        if (!isValid) {
          updateAudioFile(questionId, null as any);

          stream.getTracks().forEach((track) => track.stop());
          setRecordingId(null);
          return;
        }

        const file = new File(
          [blob],
          `recording-${questionId}.webm`,
          {
            type: "audio/webm",
          }
        );

        updateAudioFile(questionId, file);

        setAudioWarning((prev) => ({
          ...prev,
          [questionId]: "",
        }));

        setError("");

        stream.getTracks().forEach((track) => track.stop());
        setRecordingId(null);
      };

      mediaRecorder.start();
      setRecordingId(questionId);

    } catch (err) {
      console.error(err);
      setError("Gagal akses mikrofon. Sila benarkan penggunaan mikrofon.");
    }
  }

  function stopRecording() {
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
    }

    setRecordingId(null);
  }

  async function handleFileUpload(
    questionId: QuestionItem["id"],
    file?: File
  ) {
    if (!file) return;

    if (recordingId) {
      stopRecording();
    }

    const isValid = await validateAudioDuration(
      file,
      (msg) => {
        setAudioWarning((prev) => ({
          ...prev,
          [questionId]: msg,
        }));

        setError(msg);
      }
    );

    if (!isValid) {
      updateAudioFile(questionId, null);

      return;
    }

    updateAudioFile(questionId, file);

    setAudioWarning((prev) => ({
      ...prev,
      [questionId]: "",
    }));

    setError("");
  }

  function allAudioCompleted() {
    return questions.length === 5 && questions.every((question) => question.audioFile);
  }

  async function handleSubmit() {
    if (!allAudioCompleted()) {
      setError("Sila lengkapkan semua rakaman audio dahulu.");
      return;
    }

    const getAudio = (id: QuestionItem["id"]) => {
      const audio = questions.find((question) => question.id === id)?.audioFile;

      if (!audio) {
        throw new Error(`Audio missing for ${id}`);
      }

      return audio;
    };

    setSubmitting(true);
    setError("");

    try {
      const data = (await submitLatihanSpeaking(
        sessionId,
        "lisan",
        userId,
        stimulus,
        soalanRangsangan,
        soalanKbat,
        {
          bacaan: getAudio("bacaan"),
          r1: getAudio("r1"),
          r2: getAudio("r2"),
          k1: getAudio("k1"),
          k2: getAudio("k2"),
        }
      )) as SpeakingResult;

      setResult(data);

      setTimeout(() => {
        window.scrollTo({
          top: document.body.scrollHeight,
          behavior: "smooth",
        });
      }, 100);
    } catch (err) {
      console.error(err);
      setError("Gagal menghantar latihan bertutur. Sila cuba lagi.");
    } finally {
      setSubmitting(false);
    }
  }

  function handleTryAgain() {
    setQuestions((prev) =>
      prev.map((question) => ({
        ...question,
        audioFile: null,
      }))
    );

    setResult(null);
    setError("");
    setAudioWarning({});
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  // ── Derived maps (only computed when result exists) ─────────────────
  const pronunciationMap = Object.fromEntries(
    (result?.pronunciation?.per_clip || []).map(p => [p.clip_id, p])
  );

  const fluencyMap = Object.fromEntries(
    (result?.fluency?.per_clip || []).map(f => [f.clip_id, f])
  );

  const grammarMap = Object.fromEntries(
    (result?.grammar_vocabulary?.per_clip || []).map(g => [g.clip_id, g])
  );

  const ideasMap = Object.fromEntries(
    (result?.ideas?.per_question || []).map(i => [i.clip_id, i])
  );

  // ── Helpers ─────────────────────────────────────────────────────────
  const CLIP_LABELS: Record<string, string> = {
    bacaan: "Bacaan Mekanis",
    r1: "Soalan Rangsangan 1",
    r2: "Soalan Rangsangan 2",
    k1: "Soalan KBAT 1",
    k2: "Soalan KBAT 2",
  };

  const scoreColor = (score: number): string => {
    if (score < 0.40) return "#ef4444";
    if (score < 0.65) return "#f59e0b";
    return "#22c55e";
  };

  const ScoreBar = ({ score }: { score: number }) => (
    <div style={{ display: "flex", alignItems: "center", gap: "10px", margin: "6px 0" }}>
      <div style={{
        flex: 1, height: "8px", background: "#e5e7eb", borderRadius: "99px", overflow: "hidden"
      }}>
        <div style={{
          width: `${score * 100}%`, height: "100%",
          background: scoreColor(score), borderRadius: "99px",
          transition: "width 0.4s ease",
        }} />
      </div>
    </div>
  );

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
          <h1>{t("speakingPracticeTitle")}</h1>
          <p>Baca bahan rangsangan dan jawab semua soalan secara lisan.</p>
          <p>
            {t("currentLevel")}: <strong>{t(difficulty)}</strong>
          </p>
        </div>

        {loading && (
          <div className="chapter-card card-base">
            <p style={{ color: "#888", fontStyle: "italic" }}>
              {t("generatingQuestion")}
            </p>
          </div>
        )}

        {!loading && questions.length > 0 && stimulus && (
          <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
            <div className="chapter-top">BAHAN RANGSANGAN</div>
            <p style={{ whiteSpace: "pre-line", lineHeight: "1.8" }}>
              {stimulus}
            </p>
          </div>
        )}

        {!loading &&
          questions.map((question) => (
            <div
              key={question.id}
              className="chapter-card card-base"
              style={{ marginBottom: "20px" }}
            >
              <div className="chapter-top">{question.title}</div>

              {question.category !== "bacaan" && <p>{question.text}</p>}

              {question.category === "bacaan" && (
                <p>
                  Rakam bacaan anda berdasarkan bahan rangsangan di atas.
                </p>
              )}

              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>

                {/* Two-panel record OR upload */}
                <div style={{
                  display: "grid",
                  gridTemplateColumns: "1fr auto 1fr",
                  border: "0.5px solid #e5e7eb",
                  borderRadius: "12px",
                  overflow: "hidden",
                  background: "white",
                }}>

                  {/* Record side */}
                  {recordingId === question.id ? (
                    <button
                      onClick={stopRecording}
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "6px",
                        padding: "18px 12px",
                        background: "#FCEBEB",
                        border: "none",
                        cursor: "pointer",
                      }}
                    >
                      <div style={{
                        width: "36px",
                        height: "36px",
                        borderRadius: "50%",
                        background: "#F09595",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: "16px",
                      }}>
                        ⏹
                      </div>

                      <span style={{
                        fontSize: "13px",
                        fontWeight: 600,
                        color: "#991b1b"
                      }}>
                        Henti Rakaman
                      </span>

                      <span style={{
                        fontSize: "11px",
                        color: "#dc2626"
                      }}>
                        🔴 Sedang merakam...
                      </span>
                    </button>
                  ) : (
                    <button
                      onClick={() => startRecording(question.id)}
                      disabled={submitting || !!result}
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "6px",
                        padding: "18px 12px",
                        background: "white",
                        border: "none",
                        cursor: "pointer",
                        transition: "background 0.15s",
                      }}
                      onMouseEnter={(e) =>
                        (e.currentTarget.style.background = "#f0fdf4")
                      }
                      onMouseLeave={(e) =>
                        (e.currentTarget.style.background = "white")
                      }
                    >
                      <div style={{
                        width: "36px",
                        height: "36px",
                        borderRadius: "50%",
                        background: "#EAF3DE",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: "16px",
                      }}>
                        🎤
                      </div>

                      <span style={{
                        fontSize: "13px",
                        fontWeight: 600,
                        color: "#1e293b"
                      }}>
                        Rekod Audio
                      </span>

                      <span style={{
                        fontSize: "11px",
                        color: "#64748b"
                      }}>
                        Klik untuk mula merakam
                      </span>
                    </button>
                  )}

                  {/* Divider */}
                  <div style={{
                    width: "1px",
                    background: "#e5e7eb",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    position: "relative",
                  }}>
                    <span style={{
                      position: "absolute",
                      background: "#f9fafb",
                      border: "0.5px solid #e5e7eb",
                      borderRadius: "99px",
                      padding: "4px 8px",
                      fontSize: "11px",
                      color: "#94a3b8",
                      fontWeight: 500,
                      whiteSpace: "nowrap",
                    }}>
                      atau
                    </span>
                  </div>

                  {/* Upload side */}
                  <label
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: "6px",
                      padding: "18px 12px",
                      background: "white",
                      cursor: "pointer",
                      transition: "background 0.15s",
                    }}
                    onMouseEnter={(e) =>
                      (e.currentTarget.style.background = "#eff6ff")
                    }
                    onMouseLeave={(e) =>
                      (e.currentTarget.style.background = "white")
                    }
                  >
                    <div style={{
                      width: "36px",
                      height: "36px",
                      borderRadius: "50%",
                      background: "#E6F1FB",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "16px",
                    }}>
                      📁
                    </div>

                    <span style={{
                      fontSize: "13px",
                      fontWeight: 600,
                      color: "#1e293b"
                    }}>
                      Muat Naik Fail
                    </span>

                    <span style={{
                      fontSize: "11px",
                      color: "#64748b"
                    }}>
                      WAV, MP3, M4A, OGG, WebM, WebA
                    </span>

                    <input
                      type="file"
                      accept=".wav,.mp3,.m4a,.ogg,.webm,.weba"
                      hidden
                      disabled={submitting || !!result}
                      onChange={(event) =>
                        handleFileUpload(question.id, event.target.files?.[0])
                      }
                    />
                  </label>
                </div>

                {/* Playback */}
                {question.audioFile && (
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    <div style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      padding: "8px 12px",
                      background: "#f0fdf4",
                      borderRadius: "8px",
                      border: "0.5px solid #bbf7d0",
                    }}>
                      <span style={{
                        fontSize: "13px",
                        color: "#15803d",
                        fontWeight: 500
                      }}>
                        ✔ Audio siap
                      </span>
                    </div>

                    <audio
                      controls
                      style={{ width: "100%" }}
                      src={URL.createObjectURL(question.audioFile)}
                    />
                  </div>
                )}

                {audioWarning[question.id] && (
                  <p style={{ color: "#d97706", marginTop: "10px" }}>
                    {audioWarning[question.id]}
                  </p>
                )}
              </div>
            </div>
          ))}

        {error && (
          <p style={{ color: "red", fontWeight: 600, marginBottom: "12px" }}>
            {error}
          </p>
        )}

        {!result && questions.length > 0 && (
          <button
            className="button1"
            onClick={handleSubmit}
            disabled={submitting || loading}
            style={{ marginTop: "20px" }}
          >
            {submitting ? "Sedang menanda..." : "Hantar Jawapan"}
          </button>
        )}

        {result && (
          <div
            className="chapter-card card-base"
            style={{ marginTop: "25px", marginBottom: "25px" }}
          >
            <div className="chapter-top">Keputusan Latihan Bertutur</div>

            <h2>
              Skor: {result.total_score} | Band {result.overall_band}
            </h2>

            <p>
              <strong>Deskriptor:</strong> {result.overall_descriptor}
            </p>

            <hr />

            {/* ── Overall Analysis ── */}
            <div style={{ marginBottom: "32px" }}>
              <h3 style={{ marginBottom: "18px" }}>
                Analisis Keseluruhan
              </h3>

              {[
                {
                  title: "Tatabahasa & Kosa Kata",
                  score: result.grammar_vocabulary.score,
                  reason: result.grammar_vocabulary.reason,
                },
                {
                  title: "Sebutan",
                  score: result.pronunciation.score,
                  reason: result.pronunciation.reason,
                },
                {
                  title: "Kefasihan",
                  score: result.fluency.score,
                  reason: result.fluency.reason,
                },
                {
                  title: "Idea",
                  score: result.ideas.score,
                  reason: result.ideas.reason,
                },
              ].map((item, idx) => (
                <div
                  key={idx}
                  style={{
                    background: "#ffffff",
                    border: "1px solid #e5e7eb",
                    borderRadius: "14px",
                    padding: "16px",
                    marginBottom: "14px",
                  }}
                >
                  <div style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: "12px",
                    marginBottom: "8px",
                  }}>
                    <b>{item.title}</b>

                    <span style={{
                      fontWeight: 700,
                      color: scoreColor(item.score),
                    }}>
                      {(item.score * 100).toFixed(1)}%
                    </span>
                  </div>

                  <ScoreBar score={item.score} />

                  <p style={{
                    marginTop: "10px",
                    lineHeight: "1.7",
                    color: "#475569",
                  }}>
                    {item.reason}
                  </p>
                </div>
              ))}
            </div>

            {/* ── Per Clip Breakdown ── */}
            <div style={{ marginBottom: "32px" }}>
              <h3 style={{ marginBottom: "18px" }}>
                Pecahan Mengikut Klip
              </h3>

              {result.grammar_vocabulary.per_clip.map((g) => {
                const clipId = g.clip_id;

                const gram = grammarMap[clipId];
                const pron = pronunciationMap[clipId];
                const flu = fluencyMap[clipId];
                const idea = ideasMap[clipId];

                return (
                  <div
                    key={clipId}
                    style={{
                      border: "1px solid #e5e7eb",
                      borderRadius: "16px",
                      padding: "18px",
                      marginBottom: "20px",
                      background: "#ffffff",
                    }}
                  >

                    {/* Title */}
                    <div style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: "18px",
                      gap: "12px",
                    }}>
                      <div>
                        <div style={{
                          fontSize: "1rem",
                          fontWeight: 700,
                          color: "#0f172a",
                        }}>
                          {CLIP_LABELS[clipId] || clipId.toUpperCase()}
                        </div>
                      </div>
                    </div>

                    {/* Metrics */}
                    <div style={{
                      display: "grid",
                      gridTemplateColumns: "1fr",
                      gap: "14px",
                    }}>
                      {[
                        {
                          label: "Tatabahasa & Kosa Kata",
                          score: gram?.score ?? g.score,
                          reason: gram?.reason,
                        },
                        {
                          label: "Sebutan",
                          score: pron?.score ?? 0,
                          reason: pron?.reason,
                        },
                        {
                          label: "Kefasihan",
                          score: flu?.score ?? 0,
                          reason: flu?.reason,
                        },
                        ...(clipId !== "bacaan"
                          ? [
                              {
                                label: "Idea",
                                score: idea?.score ?? 0,
                                reason: idea?.reason ?? "",
                              },
                            ]
                          : []),
                      ].map((item, idx) => (
                        <div
                          key={idx}
                          style={{
                            background: "#f8fafc",
                            borderRadius: "12px",
                            padding: "14px",
                            border: "1px solid #e2e8f0",
                          }}
                        >
                          <div style={{
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            marginBottom: "8px",
                          }}>
                            <span style={{ fontWeight: 600 }}>
                              {item.label}
                            </span>

                            <span style={{
                              fontWeight: 700,
                              color: scoreColor(item.score),
                            }}>
                              {(item.score * 100).toFixed(1)}%
                            </span>
                          </div>

                          <ScoreBar score={item.score} />

                          {item.reason && (
                            <p style={{
                              marginTop: "10px",
                              color: "#475569",
                              lineHeight: "1.6",
                              fontSize: "14px",
                            }}>
                              {item.reason}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div> 
                );
              })}
            </div>

            <div
              style={{
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                gap: "12px",
                flexWrap: "wrap",
                marginTop: "18px",
              }}
            >
              <button className="button1" onClick={loadQuestions}>
                {t("newQuestion")}
              </button>

              <button className="button1" onClick={handleTryAgain}>
                {t("tryAgainButton")}
              </button>
            </div>
          </div>
        )}

        {!loading && questions.length === 0 && (
          <button className="button1" onClick={loadQuestions}>
            {t("newQuestion")}
          </button>
        )}

        <div style={{ marginBottom: "40px" }} />
      </div>
    </Layout>
  );
}