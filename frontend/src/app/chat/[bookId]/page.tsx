"use client";

import { useParams } from "next/navigation";
import { useState } from "react";

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
  return "Tutor";
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
      const res = await fetch(`${API}/books/${params.bookId}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMsg.content, chat_history: next.slice(0, -1) }),
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
    <section>
      <h2>Chat with book: {params.bookId}</h2>

      <div style={{ minHeight: 280, border: "1px solid #334155", borderRadius: 8, padding: "1rem", marginBottom: "1rem" }}>
        {messages.map((m, idx) => (
          <p key={idx}>
            <strong>{m.role === "user" ? "You" : toAgentLabel(m.agentType ?? "explain")}:</strong> {m.content}
          </p>
        ))}
      </div>

      <div style={{ display: "flex", gap: 8 }}>
        <input
          aria-label="Ask a question"
          value={input}
          onChange={(e) => setInput(e.target.value)}
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
  );
}
