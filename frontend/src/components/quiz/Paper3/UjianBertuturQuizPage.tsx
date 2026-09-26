import Layout from "../../shared/Layout";
import { useLanguage } from "../../../language";
import { useEffect, useState, useRef } from "react";
import { startSpeaking, submitSpeaking, retrySpeaking } from "../../../services/api";
import { useAuth } from "../../../context/AuthContext";

// ── Types ───────────────────────────────────────────────────────────────
import { API_URL } from "../../../services/config";
interface QuestionItem {
  id: string;
  text: string;
  category: "bacaan" | "rangsangan" | "kbat";
  audioFile: File | null;
  recordedBlob?: Blob | null;
}

interface WerResult {
  strict: number;
  spoken_only: number;
  completeness: number;
}

interface SpeakingResult {
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

interface SpeakingStartResponse {
  session_id: string;
  task_type: string;
  stimulus_text: string;
  soalan_rangsangan: {
    question_id: string;
    question_text: string;
  }[];
  soalan_kbat: {
    question_id: string;
    question_text: string;
  }[];
}

// ── Component ───────────────────────────────────────────────────────────
export default function UjianBertuturQuizPage() {
  const { t } = useLanguage();
  const { user } = useAuth();
  const userId = user?.user_id;
  const [sessionId, setSessionId] = useState<string>("");
  const [stimulus, setStimulus] = useState<string>("");
  const [soalanRangsangan, setSoalanRangsangan] = useState<any[]>([]);
  const [soalanKbat, setSoalanKbat] = useState<any[]>([]);
  const [questions, setQuestions] = useState<QuestionItem[]>([]);
  const [result, setResult] = useState<SpeakingResult | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [error, setError] = useState<string>("");
  const calledOnce = useRef(false); //Prevent double API call in Strict Mode

  // ── Recording refs ──────────────────────────────────────────────────
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const [recordingIndex, setRecordingIndex] = useState<number | null>(null);
  const MIN_AUDIO_SECS = 3.0;
  const MAX_AUDIO_SECS = 300.0;
  const [audioWarning, setAudioWarning] = useState<Record<number, string>>({});
  // const [expandedClip, setExpandedClip] = useState<string | null>(null);

  // Helper to validate upload + recording 
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
          onInvalid("Rakaman terlalu panjang. Sila ringkaskan (maks 2 minit).");
          resolve(false);
          return;
        }

        resolve(true);
      };
    });
  };

  // ── Start recording ────────────────────────────────────────────────
  const startRecording = async (index: number) => {
    setAudioWarning(prev => ({
      ...prev,
      [index]: ""
    }));

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        chunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });

        const isValid = await validateAudioDuration(blob, (msg) => {
          setAudioWarning(prev => ({
            ...prev,
            [index]: msg
          }));
          setError(msg);
        });

        if (!isValid) {
          setQuestions(prev => {
            const updated = [...prev];
            updated[index].recordedBlob = null;
            updated[index].audioFile = null;
            return updated;
          });

          return;
        }

        setQuestions(prev => {
          const updated = [...prev];
          updated[index].recordedBlob = blob;
          updated[index].audioFile = new File([blob], `recording-${index}.webm`, {
            type: "audio/webm",
          });
          return updated;
        });

        setAudioWarning(prev => ({
          ...prev,
          [index]: ""
        }));

        setError("");
      };
      mediaRecorder.start();
      setRecordingIndex(index);

    } catch (err) {
      console.error("Mic access error:", err);
      setError("Gagal akses mikrofon.");
    }
  };

  // ── Stop recording ─────────────────────────────────────────────────
  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setRecordingIndex(null);
  };

  // ── Start speaking session ─────────────────────────────────────────────
  const fetchQuestions = async (forceNew = false, retry = false, retrySessionId?: string) => {
    if (!userId) {
      setError("User not logged in");
      setLoading(false);
      return;
    }

    setQuestions([]);
    setResult(null);
    setError("");
    setSessionId("");
    setLoading(true);

    try {
      // ── Retry session ───────────────────────────────────────────────────
      if (retry && retrySessionId) {
        const data = await retrySpeaking(retrySessionId, "lisan", userId) as SpeakingStartResponse;

        setSessionId(data.session_id);
        setStimulus(data.stimulus_text);
        setSoalanRangsangan(data.soalan_rangsangan);
        setSoalanKbat(data.soalan_kbat);

        setQuestions([
          { id: "bacaan", text: data.stimulus_text, category: "bacaan", audioFile: null },
          { id: "r1", text: data.soalan_rangsangan[0].question_text, category: "rangsangan", audioFile: null },
          { id: "r2", text: data.soalan_rangsangan[1].question_text, category: "rangsangan", audioFile: null },
          { id: "k1", text: data.soalan_kbat[0].question_text, category: "kbat", audioFile: null },
          { id: "k2", text: data.soalan_kbat[1].question_text, category: "kbat", audioFile: null },
        ]);

        return;
      }

      // ── Resume latest ───────────────────────────────────────────────────
      if (!forceNew) {
        const res = await fetch(
          `${API_URL}/speaking/resume-latest?quiz_type=lisan&user_id=${userId}`
        );

        if (res.status === 200) {
          const data = await res.json();
          setSessionId(data.session_id);
          setStimulus(data.stimulus_text);
          setSoalanRangsangan(data.soalan_rangsangan);
          setSoalanKbat(data.soalan_kbat);

          setQuestions([
            { id: "bacaan", text: data.stimulus_text, category: "bacaan", audioFile: null },
            { id: "r1", text: data.soalan_rangsangan[0].question_text, category: "rangsangan", audioFile: null },
            { id: "r2", text: data.soalan_rangsangan[1].question_text, category: "rangsangan", audioFile: null },
            { id: "k1", text: data.soalan_kbat[0].question_text, category: "kbat", audioFile: null },
            { id: "k2", text: data.soalan_kbat[1].question_text, category: "kbat", audioFile: null },
          ]);

          return;
        }
      }

      // ── Start new session ───────────────────────────────────────────────
      const data = (await startSpeaking("lisan", userId)) as SpeakingStartResponse;
      setSessionId(data.session_id);
      setStimulus(data.stimulus_text);
      setSoalanRangsangan(data.soalan_rangsangan);
      setSoalanKbat(data.soalan_kbat);

      setQuestions([
        { id: "bacaan", text: data.stimulus_text, category: "bacaan", audioFile: null },
        { id: "r1", text: data.soalan_rangsangan[0].question_text, category: "rangsangan", audioFile: null },
        { id: "r2", text: data.soalan_rangsangan[1].question_text, category: "rangsangan", audioFile: null },
        { id: "k1", text: data.soalan_kbat[0].question_text, category: "kbat", audioFile: null },
        { id: "k2", text: data.soalan_kbat[1].question_text, category: "kbat", audioFile: null },
      ]);

    } catch (err) {
      setError("Gagal memuatkan soalan. Sila cuba semula.");
      console.error(err);

    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!userId || calledOnce.current) return;
    calledOnce.current = true;
    fetchQuestions();
  }, [userId]);

  // ── Handle file upload ────────────────────────────────────────────────
  const handleFileUpload = async (index: number, file: File) => {
    if (recordingIndex !== null) {
      stopRecording();
    }
    
    const isValid = await validateAudioDuration(file, (msg) => {
      setAudioWarning(prev => ({
        ...prev,
        [index]: msg
      }));
      setError(msg);
    });

    if (!isValid) {

      setQuestions(prev => {
        const updated = [...prev];
        updated[index].recordedBlob = null;
        updated[index].audioFile = null;
        return updated;
      });

      return;
    }
    setQuestions(prev => {
      const updated = [...prev];
      updated[index].audioFile = file;
      updated[index].recordedBlob = undefined;
      return updated;
    });

    setAudioWarning(prev => ({
      ...prev,
      [index]: ""
    }));

    setError("");
  };

  // ── Submit speaking ─────────────────────────────────────────────────
  const handleSubmit = async () => {
    if (!userId) return;

    const missing = questions.filter(q => !q.audioFile);
    if (missing.length > 0) {
      setError("Sila lengkapkan semua fail audio dahulu.");
      return;
    }
    
    setSubmitting(true);
    setError("");

    try {
      const getFile = (id: string) =>
        questions.find(q => q.id === id)?.audioFile!;

      const audioFiles = {
        bacaan: getFile("bacaan"),
        r1: getFile("r1")!,
        r2: getFile("r2")!,
        k1: getFile("k1")!,
        k2: getFile("k2")!,
      };

      const data = (await submitSpeaking(
        sessionId,
        "lisan",
        userId,
        stimulus,
        soalanRangsangan,
        soalanKbat,
        audioFiles
      )) as SpeakingResult;

      setResult(data);

    } catch (err) {
      console.error("submitSpeaking failed:", err);
      setError("Gagal menghantar jawapan. Sila cuba semula.");

    } finally {
      setSubmitting(false);
    }
  };

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


  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <Layout>
      <div className="container no-top-gap">

        {/* Back button */}
        <div>
          <button
            className="update-btn button1"
            onClick={() => {
              setQuestions([]);
              setResult(null);
              setError("");
              window.history.back();
            }}
          >
            {t("back")}
          </button>
        </div>

        {/* Header */}
        <div className="hero">
          <h1>Ujian Bertutur Quiz (Lisan)</h1>
          <p>Baca bahan dan jawab semua soalan secara lisan. Upload fail audio anda untuk setiap soalan.</p>
        </div>

        {/* Loading */}
        {loading && (
          <div className="chapter-card card-base">
            <p style={{ color: "#888", fontStyle: "italic" }}>Memuatkan soalan...</p>
          </div>
        )}

        {/* ── Quiz section ── */}
        {!loading && questions.length > 0 && (
          <>
            {/* Bahan Rangsangan */}
            <div className="chapter-card card-base" style={{ marginBottom: "25px" }}>
              <div className="chapter-top">BAHAN RANGSANGAN</div>
                <p style={{ lineHeight: "1.8", whiteSpace: "pre-line" }}>
                  {stimulus}
                </p>
            </div>

            {/* Questions */}
            {questions.map((q, index) => (
              <div key={q.id} className="chapter-card card-base" style={{ marginBottom: "20px" }}>
                <div 
                  className="chapter-top"
                  style={{ marginBottom: q.category === "bacaan" ? "30px" : "20px" }}
                >
                  {q.id === "bacaan"
                    ? "BACAAN MEKANIS"
                    : q.category === "rangsangan"
                    ? "SOALAN RANGSANGAN"
                    : "SOALAN KBAT"}
                </div>

                {q.category !== "bacaan" && <p>{q.text}</p>}

                {/* Controls wrapper */}
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
                    {recordingIndex === index ? (
                      <button
                        onClick={stopRecording}
                        style={{
                          display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
                          gap: "6px", padding: "18px 12px", background: "#FCEBEB", border: "none", cursor: "pointer",
                        }}
                      >
                        <div style={{
                          width: "36px", height: "36px", borderRadius: "50%", background: "#F09595",
                          display: "flex", alignItems: "center", justifyContent: "center", fontSize: "16px",
                        }}>⏹</div>
                        <span style={{ fontSize: "13px", fontWeight: 600, color: "#991b1b" }}>Henti Rakaman</span>
                        <span style={{ fontSize: "11px", color: "#dc2626" }}>🔴 Sedang merakam...</span>
                      </button>
                    ) : (
                      <button
                        onClick={() => startRecording(index)}
                        disabled={submitting || !!result}
                        style={{
                          display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
                          gap: "6px", padding: "18px 12px", background: "white", border: "none", cursor: "pointer",
                          transition: "background 0.15s",
                        }}
                        onMouseEnter={e => (e.currentTarget.style.background = "#f0fdf4")}
                        onMouseLeave={e => (e.currentTarget.style.background = "white")}
                      >
                        <div style={{
                          width: "36px", height: "36px", borderRadius: "50%", background: "#EAF3DE",
                          display: "flex", alignItems: "center", justifyContent: "center", fontSize: "16px",
                        }}>🎤</div>
                        <span style={{ fontSize: "13px", fontWeight: 600, color: "#1e293b" }}>Rekod Audio</span>
                        <span style={{ fontSize: "11px", color: "#64748b" }}>Klik untuk mula merakam</span>
                      </button>
                    )}

                    {/* Divider with "atau" */}
                    <div style={{
                      width: "1px", background: "#e5e7eb",
                      display: "flex", alignItems: "center", justifyContent: "center", position: "relative",
                    }}>
                      <span style={{
                        position: "absolute", background: "#f9fafb", border: "0.5px solid #e5e7eb",
                        borderRadius: "99px", padding: "4px 8px", fontSize: "11px", color: "#94a3b8", fontWeight: 500,
                        whiteSpace: "nowrap",
                      }}>atau</span>
                    </div>

                    {/* Upload side */}
                    <label
                      style={{
                        display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
                        gap: "6px", padding: "18px 12px", background: "white", cursor: "pointer",
                        transition: "background 0.15s",
                      }}
                      onMouseEnter={e => (e.currentTarget.style.background = "#eff6ff")}
                      onMouseLeave={e => (e.currentTarget.style.background = "white")}
                    >
                      <div style={{
                        width: "36px", height: "36px", borderRadius: "50%", background: "#E6F1FB",
                        display: "flex", alignItems: "center", justifyContent: "center", fontSize: "16px",
                      }}>📁</div>
                      <span style={{ fontSize: "13px", fontWeight: 600, color: "#1e293b" }}>Muat Naik Fail</span>
                      <span style={{ fontSize: "11px", color: "#64748b" }}>WAV, MP3, M4A, OGG, WebM, WebA</span>
                      <input
                        type="file"
                        accept=".wav,.mp3,.m4a,.ogg,.webm,.weba"
                        hidden
                        disabled={submitting || !!result}
                        onChange={(e) => e.target.files && handleFileUpload(index, e.target.files[0])}
                      />
                    </label>

                  </div>

                  {/* Uploaded file playback */}
                  {q.audioFile && !q.recordedBlob && (
                    <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                      <div style={{
                        display: "flex", alignItems: "center", gap: "8px",
                        padding: "8px 12px", background: "#f0fdf4", borderRadius: "8px",
                        border: "0.5px solid #bbf7d0",
                      }}>
                        <span style={{ fontSize: "13px", color: "#15803d", fontWeight: 500 }}>✔ {q.audioFile.name}</span>
                      </div>
                      <audio controls style={{ width: "100%" }} src={URL.createObjectURL(q.audioFile)} />
                    </div>
                  )}

                  {/* Recorded playback */}
                  {q.recordedBlob && (
                    <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                      <div style={{
                        display: "flex", alignItems: "center", gap: "8px",
                        padding: "8px 12px", background: "#f0fdf4", borderRadius: "8px",
                        border: "0.5px solid #bbf7d0",
                      }}>
                        <span style={{ fontSize: "13px", color: "#15803d", fontWeight: 500 }}>✔ recording-{index}.webm</span>
                      </div>
                      <audio controls style={{ width: "100%" }} src={URL.createObjectURL(q.recordedBlob)} />
                    </div>
                  )}
                </div>
                {audioWarning[index] && (
                  <p style={{ color: "#d97706", marginTop: "10px" }}>
                    {audioWarning[index]}
                  </p>
                )}
              </div>
            ))}
          </>
        )}

        {!loading && (
          <>
            {/* Error message */}
            {error && <p style={{ color: "red" }}>{error}</p>}
            
            {/* Submit button */}
            {!result && (
              <button
                className="button1"
                onClick={error && questions.length === 0 ? () => {
                  setError("");
                  calledOnce.current = false;
                  fetchQuestions(true);
                } : handleSubmit}
                disabled={submitting}
              >
                {submitting
                  ? t("markingAnswer")
                  : error && questions.length === 0
                  ? t("TryAgain")
                  : t("checkAnswer")
                }
              </button>
            )}          
          </>
        )}

        {/* ────── Result ────── */}
        {result && (
          <div className="card-base" style={{ marginTop: "24px", padding: "24px" }}>

            {/* ── Header ── */}
            <div style={{ textAlign: "center", marginBottom: "30px" }}>
              <div
                style={{
                  width: "90px",
                  height: "90px",
                  borderRadius: "50%",
                  background: "#f1f5f9",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  margin: "0 auto 16px",
                  border: "4px solid #dbeafe",
                  fontSize: "2rem",
                  fontWeight: 700,
                  color: "#2563eb",
                }}
              >
                {result.overall_band}
              </div>

              <h2 style={{ fontSize: "2rem", margin: 0 }}>
                Band {result.overall_band}
              </h2>

              <p style={{
                fontSize: "1.05rem",
                color: "#64748b",
                marginTop: "8px"
              }}>
                {result.overall_descriptor}
              </p>
            </div>

            {/* ── No Speech Warning ── */}
            {result.clips?.some(c => c.no_speech) && (
              <div style={{ marginBottom: "28px" }}>
                <h3 style={{ marginBottom: "14px" }}>Amaran Rakaman</h3>

                {result.clips.map((clip) =>
                  clip.no_speech ? (
                    <div
                      key={clip.clip_id}
                      style={{
                        background: "#FEF2F2",
                        border: "1px solid #FCA5A5",
                        padding: "14px",
                        borderRadius: "12px",
                        marginBottom: "12px",
                      }}
                    >
                      <div style={{
                        fontWeight: 700,
                        marginBottom: "6px",
                        color: "#991b1b"
                      }}>
                        {CLIP_LABELS[clip.clip_id] || clip.clip_id.toUpperCase()}
                      </div>

                      <div style={{ color: "#7f1d1d" }}>
                        {clip.no_speech_reason}
                      </div>
                    </div>
                  ) : null
                )}
              </div>
            )}

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

            {/* Buttons */}
            <div style={{ marginTop: "24px", display: "flex", gap: "12px", justifyContent: "center" }}>
              <button
                className="button1"
                onClick={() => {
                  if (!sessionId) {
                    setError("No session to retry");
                    return;
                  }

                  setResult(null);
                  setError("");
                  fetchQuestions(false, true, sessionId);
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }}
              >
                {t("TryAgain")}
              </button>

              <button
                className="button1"
                onClick={() => {
                  setResult(null);
                  setError("");
                  calledOnce.current = false;
                  fetchQuestions(true);
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }}
              >
                {t("generateMoreQuestionsButton")}
              </button>
            </div>
          </div>
        )}

        <div style={{ marginBottom: "40px" }} />
      </div>
    </Layout>
  );
}