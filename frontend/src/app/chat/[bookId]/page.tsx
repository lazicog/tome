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

    const res = await fetch(`${API}/books/${params.bookId}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: userMsg.content, chat_history: next.slice(0, -1) }),
    });
    if (!res.ok) {
      setError(await res.text());
      setSending(false);
      return;
    }

    if (!res.body) {
      setError("No response stream returned by server.");
      setSending(false);
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
          assistantText += JSON.parse(data) as string;
          setMessages((prev) => {
            const copy = [...prev];
            copy[copy.length - 1] = { ...copy[copy.length - 1], role: "assistant", content: assistantText };
            return copy;
          });
        }
        if (event === "agent") {
          const routed = JSON.parse(data) as string;
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

    setSending(false);
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
          <div style={{ display: "grid", gap: 8, marginTop: 8 }}>
            {sources.map((source) => (
              <div key={source.chunk_id} style={{ background: "#111827", borderRadius: 8, padding: "0.7rem" }}>
                <div style={{ fontSize: 13, opacity: 0.9 }}>
                  {source.chapter} - {source.section}
                </div>
                <div style={{ fontSize: 13, marginTop: 4 }}>
                  Pages: {source.page_numbers.join(", ")} | Score: {source.score.toFixed(4)}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
