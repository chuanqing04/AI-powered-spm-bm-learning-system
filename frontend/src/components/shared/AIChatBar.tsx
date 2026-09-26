import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { askAI } from "../../services/api";
import ReactMarkdown from "react-markdown";

type Message = {
  role: "user" | "ai";
  text: string;
  actions?: ChatAction[];
};

type ChatAction = {
  label: string;
  path: string;
};

function userWantsAction(input: string): boolean {
  const text = input.toLowerCase().trim();

  const actionWords = [
    "practice",
    "practise",
    "exercise",
    "latihan",
    "start",
    "open",
    "go to",
    "navigate",
    "try",
    "do",
    "buka",
    "pergi",
    "mula",
    "buat",
    "cuba",
    "nak cuba",
    "saya nak",
    "i want",
    "i want to",
    "let me",
    "bring me",
  ];

  const definitionWords = [
    "what is",
    "what are",
    "what does",
    "apa itu",
    "apakah",
    "explain",
    "terangkan",
    "maksud",
    "meaning",
    "define",
    "definition",
  ];

  const isAskingDefinition = definitionWords.some((word) =>
    text.includes(word)
  );

  if (isAskingDefinition) {
    return false;
  }

  return actionWords.some((word) => text.includes(word));
}

function addUniqueAction(
  actions: ChatAction[],
  label: string,
  path: string
) {
  const exists = actions.some((action) => action.path === path);

  if (!exists) {
    actions.push({ label, path });
  }
}

function getAgentActions(input: string): ChatAction[] {
  const text = input.toLowerCase().trim();

  if (!userWantsAction(text)) {
    return [];
  }

  const actions: ChatAction[] = [];

  if (
    text.includes("dashboard") ||
    text.includes("papan pemuka") ||
    text.includes("progress") ||
    text.includes("prestasi")
  ) {
    addUniqueAction(actions, "Open Dashboard", "/dashboard");
  }

  if (
    text.includes("karangan panjang") ||
    text.includes("essay panjang") ||
    text.includes("long essay")
  ) {
    addUniqueAction(
      actions,
      "Open Karangan Panjang Latihan",
      "/karangan-panjang-latihan"
    );
  }

  if (
    text.includes("karangan pendek") ||
    text.includes("short essay")
  ) {
    addUniqueAction(
      actions,
      "Open Karangan Pendek Latihan",
      "/karangan-pendek-latihan"
    );
  }

  if (
    text.includes("karangan") ||
    text.includes("essay") ||
    text.includes("esei")
  ) {
    addUniqueAction(
      actions,
      "Open Karangan Panjang Latihan",
      "/karangan-panjang-latihan"
    );

    addUniqueAction(
      actions,
      "Open Karangan Pendek Latihan",
      "/karangan-pendek-latihan"
    );
  }

  if (
    text.includes("speaking") ||
    text.includes("bertutur") ||
    text.includes("lisan")
  ) {
    addUniqueAction(
      actions,
      "Open Ujian Bertutur Latihan",
      "/ujian-bertutur-latihan"
    );
  }

  if (
    text.includes("listening") ||
    text.includes("mendengar")
  ) {
    addUniqueAction(
      actions,
      "Open Ujian Mendengar Latihan",
      "/ujian-mendengar-latihan"
    );
  }

  if (
    text.includes("bina ayat") ||
    text.includes("sentence")
  ) {
    addUniqueAction(
      actions,
      "Open Bina Ayat Latihan",
      "/bina-ayat-latihan"
    );
  }

  if (
    text.includes("golongan kata") ||
    text.includes("kata nama") ||
    text.includes("kata kerja") ||
    text.includes("kata adjektif")
  ) {
    addUniqueAction(
      actions,
      "Open Golongan Kata Latihan",
      "/golongan-kata-latihan"
    );
  }

  if (
    text.includes("jenis ayat") ||
    text.includes("ayat penyata") ||
    text.includes("ayat tanya") ||
    text.includes("ayat perintah") ||
    text.includes("ayat seruan")
  ) {
    addUniqueAction(
      actions,
      "Open Jenis Ayat Latihan",
      "/jenis-ayat-latihan"
    );
  }

  if (
    text.includes("kesalahan bahasa") ||
    text.includes("grammar error") ||
    text.includes("grammar mistake")
  ) {
    addUniqueAction(
      actions,
      "Open Kesalahan Bahasa Latihan",
      "/kesalahan-bahasa-latihan"
    );
  }

  if (
    text.includes("tatabahasa") ||
    text.includes("grammar")
  ) {
    addUniqueAction(
      actions,
      "Open Golongan Kata Latihan",
      "/golongan-kata-latihan"
    );

    addUniqueAction(
      actions,
      "Open Jenis Ayat Latihan",
      "/jenis-ayat-latihan"
    );

    addUniqueAction(
      actions,
      "Open Kesalahan Bahasa Latihan",
      "/kesalahan-bahasa-latihan"
    );
  }

  if (
    text.includes("pemahaman") ||
    text.includes("comprehension")
  ) {
    addUniqueAction(
      actions,
      "Open Pemahaman Latihan",
      "/pemahaman-latihan"
    );
  }

  if (
    text.includes("rumusan") ||
    text.includes("summary") ||
    text.includes("summarise") ||
    text.includes("summarize")
  ) {
    addUniqueAction(
      actions,
      "Open Rumusan Latihan",
      "/rumusan-latihan"
    );
  }

  if (
    text.includes("home") ||
    text.includes("laman utama") ||
    text.includes("utama")
  ) {
    addUniqueAction(actions, "Open Home", "/");
  }

  return actions.slice(0, 3);
}

export default function AIChatBar() {
  const navigate = useNavigate();

  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  function handleAgentNavigate(path: string) {
    navigate(path);
    setIsOpen(false);
  }

  const handleSend = async () => {
    const trimmedMessage = message.trim();

    if (!trimmedMessage) return;

    const userMessage: Message = {
      role: "user",
      text: trimmedMessage,
    };

    setMessages((prev) => [...prev, userMessage]);

    setLoading(true);
    setIsOpen(true);
    setMessage("");

    try {
      const aiReply = await askAI(trimmedMessage);

      const aiMessage: Message = {
        role: "ai",
        text: aiReply,
        actions: getAgentActions(trimmedMessage),
      };

      setMessages((prev) => [...prev, aiMessage]);
    } catch (err) {
      console.error(err);

      setMessages((prev) => [
        ...prev,
        {
          role: "ai",
          text: "❌ Error sending message",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <div className="ai-chatbar">
        <input
          type="text"
          placeholder="Ask AI about Tatabahasa, Karangan..."
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
        />

        <button type="button" onClick={handleSend}>
          Send
        </button>
      </div>

      <div className={`ai-chat-panel ${isOpen ? "open" : ""}`}>
        <div className="ai-chat-header">
          <span>AI Assistant</span>

          <button
            type="button"
            className="ai-chat-close"
            onClick={() => setIsOpen(false)}
            aria-label="Close AI assistant"
          >
            ✖
          </button>
        </div>

        <div className="ai-chat-messages">
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`ai-chat-message ${
                msg.role === "user" ? "user" : "ai"
              }`}
            >
              <div className="ai-chat-markdown">
                <ReactMarkdown
                  components={{
                    p: ({ children }) => <p>{children}</p>,
                    strong: ({ children }) => <strong>{children}</strong>,
                    ul: ({ children }) => <ul>{children}</ul>,
                    ol: ({ children }) => <ol>{children}</ol>,
                    li: ({ children }) => <li>{children}</li>,
                  }}
                >
                  {msg.text}
                </ReactMarkdown>
              </div>

              {msg.role === "ai" && msg.actions && msg.actions.length > 0 && (
                <div className="ai-agent-actions">
                  {msg.actions.map((action) => (
                    <button
                      key={action.path}
                      type="button"
                      className="ai-agent-action-btn"
                      onClick={() => handleAgentNavigate(action.path)}
                    >
                      {action.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}

          {loading && <p className="ai-typing">AI is typing...</p>}

          <div ref={bottomRef} />
        </div>
      </div>
    </>
  );
}