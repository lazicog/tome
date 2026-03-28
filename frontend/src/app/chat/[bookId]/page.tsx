"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { getSessionMessages, listSessions, type Session } from "../../../lib/api";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

type Message = { role: "user" | "assistant"; content: string };
type SourceChunk = {
  chunk_id: string;
  chapter: string;
  section: string;
  page_numbers: number[];
  score: number;
};

function toAgentLabel(agentType: string): string {
  if (agentType === "example") return "Example Agent";
  if (agentType === "context") return "Context Enricher";
  if (agentType === "quiz") return "Quiz Master";
  return "Tutor";
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso;
  }
}

export default function ChatPage() {
  const params = useParams<{ bookId: string }>();
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Array<Message & { agentType?: string }>>([]);
  const [sources, setSources] = useState<SourceChunk[]>([]);
  const [selectedPage, setSelectedPage] = useState<number | null>(null);
  const [copyStatus, setCopyStatus] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [loadingSessions, setLoadingSessions] = useState(true);

  const refreshSessions = useCallback(async () => {
    try {
      const data = await listSessions(params.bookId);
      setSessions(data);
    } catch {
      /* ignore */
    } finally {
      setLoadingSessions(false);
    }
  }, [params.bookId]);

  useEffect(() => {
    void refreshSessions();
  }, [refreshSessions]);

  const resumeSession = async (session: Session) => {
    setActiveSessionId(session.id);
    setMessages([]);
    setSources([]);
    setError("");
    try {
      const msgs = await getSessionMessages(session.id);
      setMessages(msgs.map((m) => ({ role: m.role, content: m.content })));
    } catch {
      setError("Failed to load session history.");
    }
  };

  const startNewSession = () => {
    setActiveSessionId(null);
    setMessages([]);
    setSources([]);
    setSelectedPage(null);
    setCopyStatus("");
    setError("");
  };

  const send = async () => {
    if (!input.trim()) return;
    const userMsg: Message = { role: "user", content: input };
    const next = [...messages, userMsg];
    setMessages(next);
    setInput("");
    setSending(true);
    setError("");
    setSources([]);
    setSelectedPage(null);
    setCopyStatus("");

    try {
      const body: Record<string, unknown> = {
        message: userMsg.content,
        chat_history: activeSessionId ? [] : next.slice(0, -1),
      };
      if (activeSessionId) {
        body.session_id = activeSessionId;
      }

      const res = await fetch(`${API}/books/${params.bookId}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        setError(await res.text());
        return;
      }

      if (!res.body) {
        setError("No response stream returned by server.");
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let assistantText = "";
      setMessages((prev) => [...prev, { role: "assistant", content: "", agentType: "explain" }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";

        for (const frame of frames) {
          const lines = frame.split("\n");
          const eventLine = lines.find((line) => line.startsWith("event: "));
          const dataLines = lines.filter((line) => line.startsWith("data: "));
          if (!eventLine || dataLines.length === 0) continue;

          const event = eventLine.replace("event: ", "");
          const data = dataLines.map((line) => line.replace("data: ", "")).join("\n");

          if (event === "session") {
            try {
              const sid = JSON.parse(data) as string;
              setActiveSessionId(sid);
            } catch {
              /* ignore */
            }
          }
          if (event === "token") {
            try {
              assistantText += JSON.parse(data) as string;
            } catch {
              continue;
            }
            setMessages((prev) => {
              const copy = [...prev];
              copy[copy.length - 1] = { ...copy[copy.length - 1], role: "assistant", content: assistantText };
              return copy;
            });
          }
          if (event === "agent") {
            let routed = "explain";
            try {
              routed = JSON.parse(data) as string;
            } catch {
              routed = "explain";
            }
            setMessages((prev) => {
              const copy = [...prev];
              copy[copy.length - 1] = { ...copy[copy.length - 1], role: "assistant", agentType: routed };
              return copy;
            });
          }
          if (event === "sources") {
            try {
              const parsed = JSON.parse(data) as SourceChunk[];
              setSources(parsed);
            } catch {
              setSources([]);
            }
          }
        }
      }

      void refreshSessions();
    } catch {
      setError("Chat request failed. Please try again.");
    } finally {
      setSending(false);
    }
  };

  const availablePages = Array.from(new Set(sources.flatMap((source) => source.page_numbers))).sort((a, b) => a - b);
  const visibleSources = selectedPage === null ? sources : sources.filter((source) => source.page_numbers.includes(selectedPage));
  const filterActive = selectedPage !== null;

  const copyCitation = async (source: SourceChunk) => {
    const citation = `${source.chapter} | ${source.section} | pages ${source.page_numbers.join(", ")} | score ${source.score.toFixed(4)}`;
    try {
      await navigator.clipboard.writeText(citation);
      setCopyStatus("Citation copied.");
    } catch {
      setCopyStatus("Clipboard unavailable in this browser.");
    }
  };

  return (
    <div style={{ display: "flex", gap: 16 }}>
      {/* Sessions sidebar */}
      <aside
        style={{
          width: 220,
          minWidth: 220,
          borderRight: "1px solid #334155",
          paddingRight: 16,
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <strong style={{ fontSize: 14 }}>Sessions</strong>
          <button
            type="button"
            onClick={startNewSession}
            style={{
              fontSize: 12,
              padding: "4px 8px",
              borderRadius: 6,
              border: "1px solid #334155",
              background: "#1e293b",
              color: "#e2e8f0",
              cursor: "pointer",
            }}
          >
            + New
          </button>
        </div>
        {loadingSessions ? (
          <p style={{ fontSize: 13, color: "#94a3b8" }}>Loading...</p>
        ) : sessions.length === 0 ? (
          <p style={{ fontSize: 13, color: "#94a3b8" }}>No sessions yet. Start chatting!</p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {sessions.map((s) => (
              <button
                key={s.id}
                type="button"
                onClick={() => void resumeSession(s)}
                style={{
                  textAlign: "left",
                  padding: "8px 10px",
                  borderRadius: 8,
                  border: activeSessionId === s.id ? "2px solid #93c5fd" : "1px solid #334155",
                  background: activeSessionId === s.id ? "#1e293b" : "transparent",
                  color: "#e2e8f0",
                  cursor: "pointer",
                  fontSize: 13,
                }}
              >
                <div>{s.message_count} messages</div>
                <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2 }}>{formatTime(s.updated_at)}</div>
              </button>
            ))}
          </div>
        )}
      </aside>

      {/* Chat area */}
      <section style={{ flex: 1, minWidth: 0 }}>
        <h2 style={{ marginTop: 0 }}>Chat with book: {params.bookId}</h2>

        <div style={{ minHeight: 280, border: "1px solid #334155", borderRadius: 8, padding: "1rem", marginBottom: "1rem" }}>
          {messages.length === 0 ? (
            <p style={{ color: "#94a3b8" }}>
              {activeSessionId ? "Loading session..." : "Start a conversation by asking a question about the book."}
            </p>
          ) : (
            messages.map((m, idx) => (
              <p key={idx}>
                <strong>{m.role === "user" ? "You" : toAgentLabel(m.agentType ?? "explain")}:</strong> {m.content}
              </p>
            ))
          )}
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          <input
            aria-label="Ask a question"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !sending) void send();
            }}
            placeholder="Ask about any concept in this book..."
            style={{ flex: 1, padding: "0.7rem", borderRadius: 8 }}
          />
          <button onClick={send} disabled={sending} style={{ padding: "0.7rem 1rem", borderRadius: 8 }}>
            {sending ? "Thinking..." : "Send"}
          </button>
        </div>
        {error ? <p style={{ color: "#fca5a5" }}>{error}</p> : null}

        {sources.length > 0 ? (
          <div style={{ marginTop: "1rem", border: "1px solid #334155", borderRadius: 8, padding: "0.8rem" }}>
            <strong>Sources</strong>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8, alignItems: "center" }}>
              <button
                type="button"
                aria-pressed={!filterActive}
                onClick={() => {
                  setSelectedPage(null);
                  setCopyStatus("");
                }}
                style={{
                  borderRadius: 8,
                  padding: "0.35rem 0.6rem",
                  border: filterActive ? "1px solid #334155" : "2px solid #94a3b8",
                  background: filterActive ? "transparent" : "#1e293b",
                }}
              >
                All pages
              </button>
              {filterActive ? (
                <span style={{ fontSize: 12, color: "#94a3b8" }}>Filtered by page {selectedPage}</span>
              ) : null}
              {availablePages.map((page) => (
                <button
                  key={page}
                  type="button"
                  aria-pressed={selectedPage === page}
                  onClick={() => {
                    setSelectedPage(page);
                    setCopyStatus("");
                  }}
                  style={{
                    borderRadius: 8,
                    padding: "0.35rem 0.6rem",
                    border: selectedPage === page ? "2px solid #94a3b8" : "1px solid #334155",
                    background: selectedPage === page ? "#1e293b" : "transparent",
                  }}
                >
                  Page {page}
                </button>
              ))}
            </div>
            {copyStatus ? (
              <p style={{ marginTop: 8, fontSize: 13 }} role="status" aria-live="polite">
                {copyStatus}
              </p>
            ) : null}
            {filterActive && visibleSources.length === 0 ? (
              <p style={{ marginTop: 8, fontSize: 13, color: "#94a3b8" }} role="status">
                No sources cite page {selectedPage}. Pick another page or choose All pages.
              </p>
            ) : null}
            <div style={{ display: "grid", gap: 8, marginTop: 8 }}>
              {visibleSources.map((source) => (
                <div key={source.chunk_id} style={{ background: "#111827", borderRadius: 8, padding: "0.7rem" }}>
                  <div style={{ fontSize: 13, opacity: 0.9 }}>
                    {source.chapter} - {source.section}
                  </div>
                  <div style={{ fontSize: 13, marginTop: 4 }}>
                    Pages: {source.page_numbers.join(", ")} | Score: {source.score.toFixed(4)}
                  </div>
                  <button
                    type="button"
                    aria-label={`Copy citation: ${source.chapter}, ${source.section}`}
                    onClick={() => void copyCitation(source)}
                    style={{ marginTop: 6, borderRadius: 8, padding: "0.3rem 0.5rem", border: "1px solid #334155" }}
                  >
                    Copy citation
                  </button>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </section>
    </div>
  );
}
