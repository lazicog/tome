"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
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
  Sparkles,
  GripVertical,
} from "lucide-react";

import PdfViewer from "../../../components/PdfViewer";
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

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-1 py-1">
      <span className="typing-dot w-1.5 h-1.5 rounded-full bg-accent" />
      <span className="typing-dot w-1.5 h-1.5 rounded-full bg-accent" />
      <span className="typing-dot w-1.5 h-1.5 rounded-full bg-accent" />
    </div>
  );
}

const SUGGESTIONS = [
  { label: "Explain the main concepts", icon: "explain" },
  { label: "Show me a code example", icon: "example" },
  { label: "Give me background context", icon: "context" },
  { label: "Quiz me on this chapter", icon: "quiz" },
];

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
  const [waitingForFirst, setWaitingForFirst] = useState(false);
  const [error, setError] = useState("");

  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Resizable pane
  const [pdfWidth, setPdfWidth] = useState(50);
  const dragging = useRef(false);
  const containerRef = useRef<HTMLDivElement>(null);

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

  // Auto-resize textarea
  useEffect(() => {
    if (!textareaRef.current) return;
    textareaRef.current.style.height = "auto";
    textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + "px";
  }, [input]);

  // Drag to resize
  const onDragStart = (e: React.MouseEvent) => {
    e.preventDefault();
    dragging.current = true;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    const onMove = (ev: MouseEvent) => {
      if (!dragging.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const pct = ((ev.clientX - rect.left) / rect.width) * 100;
      setPdfWidth(Math.max(25, Math.min(75, pct)));
    };
    const onUp = () => {
      dragging.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  };

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

  const sendMessage = async (text?: string) => {
    const msg = text ?? input;
    if (!msg.trim() || sending) return;
    const userMsg: Message = { role: "user", content: msg };
    const next = [...messages, userMsg];
    setMessages(next);
    setInput("");
    setSending(true);
    setWaitingForFirst(true);
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
      if (!res.ok) { setError(await res.text()); setWaitingForFirst(false); return; }
      if (!res.body) { setError("No stream returned."); setWaitingForFirst(false); return; }

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
            setWaitingForFirst(false);
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
      setWaitingForFirst(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !sending) {
      e.preventDefault();
      void sendMessage();
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
      <div ref={containerRef} className="flex flex-1 min-h-0 overflow-hidden">
        {/* PDF Viewer */}
        <div style={{ width: chatOpen ? `${pdfWidth}%` : "100%" }} className="min-h-0 shrink-0">
          <PdfViewer url={pdfUrl} goToPage={goToPage} />
        </div>

        {/* Drag handle */}
        {chatOpen && (
          <div
            onMouseDown={onDragStart}
            className="resize-handle w-1.5 shrink-0 bg-border hover:bg-accent transition-colors flex items-center justify-center"
          >
            <GripVertical className="w-3 h-3 text-text-muted pointer-events-none" />
          </div>
        )}

        {/* Chat panel */}
        {chatOpen && (
          <div className="flex-1 flex flex-col min-h-0 min-w-0">
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
                <div className="flex flex-col items-center justify-center h-full">
                  <BookOpen className="w-10 h-10 mb-4 text-text-muted opacity-30" />
                  <p className="text-sm text-text-muted mb-5">Ask a question about this book</p>
                  <div className="grid grid-cols-2 gap-2 max-w-xs w-full">
                    {SUGGESTIONS.map((s) => (
                      <button
                        key={s.label}
                        onClick={() => void sendMessage(s.label)}
                        className="text-left px-3 py-2.5 rounded-lg border border-border bg-bg-card/50 text-xs text-text-muted hover:text-text hover:border-text-muted transition-colors leading-snug"
                      >
                        <Sparkles className="w-3 h-3 text-accent mb-1" />
                        {s.label}
                      </button>
                    ))}
                  </div>
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
                        m.content ? (
                          <div className="prose-chat text-sm max-w-none">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                          </div>
                        ) : waitingForFirst ? (
                          <TypingIndicator />
                        ) : (
                          <span className="text-text-muted">...</span>
                        )
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
                      title={`Score: ${s.score.toFixed(3)}`}
                    >
                      <FileText className="w-3 h-3" />
                      <span className="max-w-[120px] truncate">{s.chapter !== "Unknown" ? s.chapter : s.section}</span>
                      <span className="text-text-muted/60">p.{s.page_numbers.join(",")}</span>
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
              <div className="flex gap-2 items-end">
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask about this book..."
                  rows={1}
                  className="flex-1 bg-bg-input border border-border rounded-lg px-3 py-2 text-sm text-text placeholder:text-text-muted focus:outline-none focus:border-accent transition-colors resize-none overflow-hidden leading-relaxed"
                />
                <button
                  onClick={() => void sendMessage()}
                  disabled={sending || !input.trim()}
                  className="px-3 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent-hover disabled:opacity-40 transition-colors flex items-center gap-1.5 shrink-0"
                >
                  {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                </button>
              </div>
              <p className="text-[10px] text-text-muted/50 mt-1 px-1">Enter to send · Shift+Enter for new line</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
