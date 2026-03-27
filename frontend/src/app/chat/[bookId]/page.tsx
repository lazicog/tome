"use client";

import { useParams } from "next/navigation";
import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

type Message = { role: "user" | "assistant"; content: string };

export default function ChatPage() {
  const params = useParams<{ bookId: string }>();
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [sources, setSources] = useState<string>("");
  const [sending, setSending] = useState(false);

  const send = async () => {
    if (!input.trim()) return;
    const userMsg: Message = { role: "user", content: input };
    const next = [...messages, userMsg];
    setMessages(next);
    setInput("");
    setSending(true);

    const res = await fetch(`${API}/books/${params.bookId}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: userMsg.content, chat_history: next.slice(0, -1) }),
    });

    if (!res.body) {
      setSending(false);
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let assistantText = "";
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const frames = buffer.split("\n\n");
      buffer = frames.pop() ?? "";

      for (const frame of frames) {
        const eventLine = frame.split("\n").find((line) => line.startsWith("event: "));
        const dataLine = frame.split("\n").find((line) => line.startsWith("data: "));
        if (!eventLine || !dataLine) continue;

        const event = eventLine.replace("event: ", "");
        const data = dataLine.replace("data: ", "");

        if (event === "token") {
          assistantText += JSON.parse(data) as string;
          setMessages((prev) => {
            const copy = [...prev];
            copy[copy.length - 1] = { role: "assistant", content: assistantText };
            return copy;
          });
        }
        if (event === "sources") {
          setSources(data);
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
            <strong>{m.role === "user" ? "You" : "Tutor"}:</strong> {m.content}
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

      {sources ? (
        <pre style={{ marginTop: "1rem", whiteSpace: "pre-wrap", background: "#111827", padding: "0.8rem", borderRadius: 8 }}>
          Sources: {sources}
        </pre>
      ) : null}
    </section>
  );
}
