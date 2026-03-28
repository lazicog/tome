"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import dynamic from "next/dynamic";
import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ArrowLeft,
  MessageSquare,
  BookOpen,
  Send,
  Plus,
  Loader2,
  FileText,
  X,
} from "lucide-react";

import {
  getBook,
  getBookPdfUrl,
  getApiBase,
  getSessionMessages,
  listSessions,
  type Book,
  type Session,
} from "../../../lib/api";
import { cn } from "../../../lib/utils";

const PdfViewer = dynamic(() => import("../../../components/PdfViewer"), {
  ssr: false,
  loading: () => (
    <div className="flex flex-col items-center justify-center h-full text-text-muted">
      <Loader2 className="w-6 h-6 animate-spin mb-2" />
      <span className="text-sm">Loading PDF viewer...</span>
    </div>
  ),
});

type Message = { role: "user" | "assistant"; content: string; agentType?: string };
type SourceChunk = {
  chunk_id: string;
  chapter: string;
  section: string;
  page_numbers: number[];
  score: number;
};

function agentLabel(t: string): string {
  if (t === "example") return "Example Agent";
  if (t === "context") return "Context Enricher";
  if (t === "quiz") return "Quiz Master";
  return "Tutor";
}

export default function BookPage() {
  const params = useParams<{ bookId: string }>();
  const bookId = params.bookId;

  const [book, setBook] = useState<Book | null>(null);
  const [goToPage, setGoToPage] = useState<number | undefined>(undefined);

  const [chatOpen, setChatOpen] = useState(true);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [sources, setSources] = useState<SourceChunk[]>([]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    void getBook(bookId).then(setBook);
  }, [bookId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const refreshSessions = useCallback(async () => {
    try {
      const data = await listSessions(bookId);
      setSessions(data);
    } catch { /* ignore */ }
  }, [bookId]);

  useEffect(() => { void refreshSessions(); }, [refreshSessions]);

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
    setError("");
  };

  const send = async () => {
    if (!input.trim() || sending) return;
    const userMsg: Message = { role: "user", content: input };
    const next = [...messages, userMsg];
    setMessages(next);
    setInput("");
    setSending(true);
    setError("");
    setSources([]);

    try {
      const body: Record<string, unknown> = {
        message: userMsg.content,
        chat_history: activeSessionId ? [] : next.slice(0, -1),
      };
      if (activeSessionId) body.session_id = activeSessionId;

      const res = await fetch(`${getApiBase()}/books/${bookId}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) { setError(await res.text()); return; }
      if (!res.body) { setError("No stream returned."); return; }

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
          const eventLine = lines.find((l) => l.startsWith("event: "));
          const dataLines = lines.filter((l) => l.startsWith("data: "));
          if (!eventLine || !dataLines.length) continue;
          const event = eventLine.replace("event: ", "");
          const data = dataLines.map((l) => l.replace("data: ", "")).join("\n");

          if (event === "session") {
            try { setActiveSessionId(JSON.parse(data)); } catch { /* */ }
          }
          if (event === "token") {
            try { assistantText += JSON.parse(data) as string; } catch { continue; }
            setMessages((prev) => {
              const copy = [...prev];
              copy[copy.length - 1] = { ...copy[copy.length - 1], content: assistantText };
              return copy;
            });
          }
          if (event === "agent") {
            let routed = "explain";
            try { routed = JSON.parse(data) as string; } catch { /* */ }
            setMessages((prev) => {
              const copy = [...prev];
              copy[copy.length - 1] = { ...copy[copy.length - 1], agentType: routed };
              return copy;
            });
          }
          if (event === "sources") {
            try { setSources(JSON.parse(data) as SourceChunk[]); } catch { setSources([]); }
          }
        }
      }
      void refreshSessions();
    } catch {
      setError("Chat request failed.");
    } finally {
      setSending(false);
    }
  };

  const pdfUrl = getBookPdfUrl(bookId);

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem-3rem)]">
      {/* Top bar */}
      <div className="flex items-center justify-between px-2 py-2 border-b border-border shrink-0">
        <div className="flex items-center gap-3">
          <Link href="/" className="p-1.5 rounded-lg hover:bg-bg-hover transition-colors text-text-muted hover:text-text">
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <h1 className="text-sm font-semibold text-text-heading truncate max-w-[300px]">
            {book?.title ?? "Loading..."}
          </h1>
        </div>
        <button
          onClick={() => setChatOpen(!chatOpen)}
          className={cn(
            "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
            chatOpen ? "bg-accent text-white" : "border border-border text-text-muted hover:text-text hover:bg-bg-hover"
          )}
        >
          <MessageSquare className="w-4 h-4" />
          {chatOpen ? "Hide Chat" : "Show Chat"}
        </button>
      </div>

      {/* Main split pane */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* PDF Viewer */}
        <div className={cn("min-h-0", chatOpen ? "w-1/2" : "w-full")}>
          <PdfViewer url={pdfUrl} goToPage={goToPage} />
        </div>

        {/* Chat panel */}
        {chatOpen && (
          <div className="w-1/2 flex flex-col border-l border-border min-h-0">
            {/* Session bar */}
            <div className="flex items-center gap-2 px-3 py-2 border-b border-border bg-bg-card/50 shrink-0 overflow-x-auto">
              <button
                onClick={startNewSession}
                className="shrink-0 flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium border border-border hover:bg-bg-hover transition-colors text-text-muted hover:text-text"
              >
                <Plus className="w-3 h-3" /> New
              </button>
              {sessions.map((s) => (
                <button
                  key={s.id}
                  onClick={() => void resumeSession(s)}
                  className={cn(
                    "shrink-0 px-2.5 py-1 rounded-lg text-xs transition-colors",
                    activeSessionId === s.id
                      ? "bg-accent/15 text-accent border border-accent/40 font-medium"
                      : "border border-border text-text-muted hover:text-text hover:bg-bg-hover"
                  )}
                >
                  {s.message_count} msgs
                </button>
              ))}
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-auto px-3 py-3 space-y-3">
              {messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-text-muted">
                  <BookOpen className="w-8 h-8 mb-3 opacity-40" />
                  <p className="text-sm">Ask a question about this book.</p>
                </div>
              ) : (
                messages.map((m, i) => (
                  <div key={i} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
                    <div
                      className={cn(
                        "max-w-[85%] rounded-xl px-3.5 py-2.5 text-sm leading-relaxed",
                        m.role === "user"
                          ? "bg-accent text-white rounded-br-sm"
                          : "bg-bg-card border border-border rounded-bl-sm"
                      )}
                    >
                      {m.role === "assistant" && m.agentType && (
                        <div className="text-[11px] font-medium text-accent mb-1">{agentLabel(m.agentType ?? "explain")}</div>
                      )}
                      {m.role === "assistant" ? (
                        <div className="prose prose-sm prose-invert max-w-none [&_p]:my-1 [&_ul]:my-1 [&_ol]:my-1 [&_li]:my-0.5">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content || "..."}</ReactMarkdown>
                        </div>
                      ) : (
                        <span>{m.content}</span>
                      )}
                    </div>
                  </div>
                ))
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Source chips */}
            {sources.length > 0 && (
              <div className="px-3 py-2 border-t border-border bg-bg-card/30 shrink-0">
                <div className="text-[11px] font-medium text-text-muted mb-1.5">Sources</div>
                <div className="flex flex-wrap gap-1.5">
                  {sources.map((s) => (
                    <button
                      key={s.chunk_id}
                      onClick={() => {
                        const p = s.page_numbers[0];
                        if (p) setGoToPage(p);
                      }}
                      className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-bg-input border border-border text-xs text-text-muted hover:text-accent hover:border-accent/40 transition-colors"
                      title={`${s.chapter} - ${s.section} (score: ${s.score.toFixed(3)})`}
                    >
                      <FileText className="w-3 h-3" />
                      p.{s.page_numbers.join(",")}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {error && (
              <div className="px-3 py-2 shrink-0 flex items-center gap-2">
                <span className="text-error text-xs flex-1">{error}</span>
                <button onClick={() => setError("")} className="text-text-muted hover:text-text">
                  <X className="w-3 h-3" />
                </button>
              </div>
            )}

            {/* Input */}
            <div className="px-3 py-2.5 border-t border-border shrink-0">
              <div className="flex gap-2">
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter" && !sending) void send(); }}
                  placeholder="Ask about this book..."
                  className="flex-1 bg-bg-input border border-border rounded-lg px-3 py-2 text-sm text-text placeholder:text-text-muted focus:outline-none focus:border-accent transition-colors"
                />
                <button
                  onClick={() => void send()}
                  disabled={sending || !input.trim()}
                  className="px-3 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent-hover disabled:opacity-40 transition-colors flex items-center gap-1.5"
                >
                  {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
