"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { memo, useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ArrowLeft,
  Send,
  Plus,
  Loader2,
  FileText,
  X,
  Sparkles,
  StickyNote,
  Bookmark,
  ChevronDown,
  ChevronRight,
} from "lucide-react";

import dynamic from "next/dynamic";
const PdfViewer = dynamic(() => import("@/components/PdfViewer"), { ssr: false });
import NotesDrawer from "@/components/NotesDrawer";
import {
  getBook,
  getBookPdfUrl,
  getApiBase,
  getSessionMessages,
  listSessions,
  createNote,
  suggestNoteTitle,
  type Book,
  type Session,
} from "@/lib/api";
import { cn } from "@/lib/utils";

type Message = { role: "user" | "assistant"; content: string };
type WebSource = { url: string; snippet: string };
type SourceChunk = {
  chunk_id: string;
  chapter: string;
  section: string;
  page_numbers: number[];
  score: number;
  relevance?: string;
  quote?: string;
  is_ahead_of_position?: boolean;
};

/** Derive a short title from note content — strips markdown, uses first sentence */
function deriveTitle(content: string): string {
  const firstLine = content
    .split("\n")
    .map((l) => l.replace(/^#{1,6}\s+/, "").replace(/[*_`]/g, "").trim())
    .find((l) => l.length > 0) ?? "";
  const sentence = firstLine.split(/[.!?]/)[0].trim();
  const candidate = sentence || firstLine;
  return candidate.length > 60 ? candidate.slice(0, 57) + "…" : candidate;
}

/* Fix 2: session label helper */
function formatSessionLabel(s: Session): string {
  const date = new Date(s.created_at).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
  return `${date} · ${s.message_count} msgs`;
}

const TypingIndicator = memo(function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 py-1">
      <span className="typing-dot w-1.5 h-1.5 rounded-full bg-indigo-400" />
      <span className="typing-dot w-1.5 h-1.5 rounded-full bg-indigo-400" />
      <span className="typing-dot w-1.5 h-1.5 rounded-full bg-indigo-400" />
    </div>
  );
});

const SUGGESTIONS = [
  "Explain the main concepts",
  "Show me a code example",
  "Give me background context",
  "Quiz me on this chapter",
  "Summarize the key points",
];

/* ── Save Note Dialog ── */
function SaveNoteDialog({
  loading,
  title,
  content,
  onTitleChange,
  onConfirm,
  onCancel,
}: {
  loading: boolean;
  title: string;
  content: string;
  onTitleChange: (v: string) => void;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const preview = content.length > 200 ? content.slice(0, 197) + "…" : content;

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onCancel(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onCancel]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onCancel} />
      <div
        className="relative rounded-xl border w-full max-w-md shadow-2xl p-5 flex flex-col gap-4"
        style={{ background: "#151515", borderColor: "#303030" }}
      >
        {/* Header */}
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold" style={{ color: "#F0F0F0" }}>Save as note</span>
          <button onClick={onCancel} className="p-1 rounded text-[#737373] hover:text-[#F0F0F0] transition-colors">
            <X size={14} />
          </button>
        </div>

        {/* Title field */}
        <div className="flex flex-col gap-1.5">
          <label className="text-xs" style={{ color: "#737373" }}>Title</label>
          {loading ? (
            <div
              className="h-8 rounded-lg border flex items-center px-3 gap-2"
              style={{ background: "#1C1C1C", borderColor: "#303030" }}
            >
              <Loader2 size={12} className="animate-spin text-indigo-400" />
              <span className="text-xs" style={{ color: "#737373" }}>Generating title…</span>
            </div>
          ) : (
            <input
              autoFocus
              value={title}
              onChange={(e) => onTitleChange(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); onConfirm(); } }}
              className="h-8 rounded-lg border px-3 text-sm outline-none transition-colors"
              style={{ background: "#1C1C1C", borderColor: "#303030", color: "#F0F0F0" }}
              onFocus={(e) => (e.currentTarget.style.borderColor = "rgba(99,102,241,0.5)")}
              onBlur={(e) => (e.currentTarget.style.borderColor = "#303030")}
            />
          )}
        </div>

        {/* Content preview */}
        <div
          className="rounded-lg border p-3 text-xs leading-relaxed"
          style={{ background: "#0E0E0E", borderColor: "#242424", color: "#737373", maxHeight: "120px", overflowY: "auto" }}
        >
          {preview}
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="px-3 h-7 rounded-md text-xs transition-colors"
            style={{ color: "#737373" }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "#F0F0F0")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "#737373")}
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={loading || !title.trim()}
            className="px-3 h-7 rounded-md text-xs font-medium transition-colors disabled:opacity-40"
            style={{ background: "#6366F1", color: "#F0F0F0" }}
            onMouseEnter={(e) => { if (!loading) e.currentTarget.style.background = "#4F46E5"; }}
            onMouseLeave={(e) => (e.currentTarget.style.background = "#6366F1")}
          >
            Save note
          </button>
        </div>
      </div>
    </div>
  );
}

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  isLast: boolean;
  thinkingLabel: string;
  waitingForFirst: boolean;
  sending: boolean;
  onSaveAsNote: (content: string) => void;
}

const MessageBubble = memo(function MessageBubble({
  role,
  content,
  isLast,
  thinkingLabel,
  waitingForFirst,
  sending,
  onSaveAsNote,
}: MessageBubbleProps) {
  return (
    <div className={cn("flex", role === "user" ? "justify-end" : "justify-start")}>
      <div
        className={cn("max-w-[88%] rounded-2xl px-3.5 py-2.5 text-sm min-w-0")}
        style={
          role === "user"
            ? { background: "#6366F1", color: "#F0F0F0", overflowWrap: "anywhere", wordBreak: "break-word" }
            : { background: "#151515", border: "1px solid #242424", color: "#F0F0F0", overflowWrap: "anywhere", wordBreak: "break-word" }
        }
      >
        {role === "assistant" ? (
          <>
            {content ? (
              <div className="prose-chat max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
              </div>
            ) : isLast && waitingForFirst ? (
              <div className="flex flex-col gap-1">
                <TypingIndicator />
                {thinkingLabel && (
                  <span className="text-[10px]" style={{ color: "#737373" }}>{thinkingLabel}</span>
                )}
              </div>
            ) : (
              <span style={{ color: "#737373" }}>…</span>
            )}
            {content && !sending && (
              <button
                onClick={() => onSaveAsNote(content)}
                className="mt-2 flex items-center gap-1 text-[10px] transition-colors"
                style={{ color: "#404040" }}
                onMouseEnter={(e) => (e.currentTarget.style.color = "#6366F1")}
                onMouseLeave={(e) => (e.currentTarget.style.color = "#404040")}
              >
                <Bookmark size={11} /> Save as note
              </button>
            )}
          </>
        ) : (
          <span>{content}</span>
        )}
      </div>
    </div>
  );
});

export default function BookPage() {
  const params = useParams<{ bookId: string }>();
  const bookId = params.bookId;

  const [book, setBook] = useState<Book | null>(null);
  const [goToPage, setGoToPage] = useState<number | undefined>(undefined);
  const [currentPage, setCurrentPage] = useState(1);

  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [sources, setSources] = useState<SourceChunk[]>([]);
  const [sourcesExpanded, setSourcesExpanded] = useState(false); // Fix 4
  const [sending, setSending] = useState(false);
  const [waitingForFirst, setWaitingForFirst] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");

  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [sessionsExpanded, setSessionsExpanded] = useState(false);

  const [notesOpen, setNotesOpen] = useState(false);
  const [notesRefresh, setNotesRefresh] = useState(0);

  const [searchWholeBook, setSearchWholeBook] = useState(false);

  const [thinkingLabel, setThinkingLabel] = useState("");
  const [webSources, setWebSources] = useState<WebSource[]>([]);

  // Save-as-note dialog
  const [pendingNoteContent, setPendingNoteContent] = useState<string | null>(null);
  const [suggestedTitle, setSuggestedTitle] = useState("");
  const [fetchingTitle, setFetchingTitle] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null); // Fix 5
  const shouldAutoScroll = useRef(true); // Fix 5
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { void getBook(bookId).then(setBook); }, [bookId]);

  /* Fix 5: smart scroll — instant during streaming, only if near bottom */
  useEffect(() => {
    if (!shouldAutoScroll.current) return;
    messagesEndRef.current?.scrollIntoView({ behavior: "instant" });
  }, [messages]);

  /* Fix 5: when user sends a message, force-scroll and re-enable auto-scroll */
  const scrollToBottom = () => {
    shouldAutoScroll.current = true;
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  /* Fix 5: track whether user has scrolled up */
  const handleMessagesScroll = () => {
    const el = messagesContainerRef.current;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    shouldAutoScroll.current = nearBottom;
  };

  const refreshSessions = useCallback(async () => {
    try { setSessions(await listSessions(bookId)); } catch { /* */ }
  }, [bookId]);

  useEffect(() => { void refreshSessions(); }, [refreshSessions]);

  /* Press "/" anywhere to focus chat input */
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      if (e.key === "/") {
        e.preventDefault();
        textareaRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  useEffect(() => {
    if (!textareaRef.current) return;
    textareaRef.current.style.height = "auto";
    textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + "px";
  }, [input]);

  /* Fix 4: collapse sources when a new message arrives */
  useEffect(() => { setSourcesExpanded(false); }, [sources]);

  const resumeSession = async (session: Session) => {
    setActiveSessionId(session.id);
    setMessages([]);
    setSources([]);
    setError("");
    setSessionsExpanded(false);
    try {
      const msgs = await getSessionMessages(session.id);
      setMessages(msgs.map((m) => ({ role: m.role, content: m.content })));
    } catch { setError("Failed to load session."); }
  };

  const startNewSession = () => {
    setActiveSessionId(null);
    setMessages([]);
    setSources([]);
    setError("");
    setSessionsExpanded(false);
  };

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(""), 3000);
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
    setThinkingLabel("");
    setWebSources([]);
    scrollToBottom(); // Fix 5: force scroll on new user message

    try {
      const body: Record<string, unknown> = {
        message: userMsg.content,
        chat_history: activeSessionId ? [] : next.slice(0, -1),
      };
      if (activeSessionId) body.session_id = activeSessionId;
      if (!searchWholeBook) body.current_page = currentPage;

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
      setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

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
            setThinkingLabel("");
            try { assistantText += JSON.parse(data) as string; } catch { continue; }
            setMessages((prev) => {
              const copy = [...prev];
              copy[copy.length - 1] = { ...copy[copy.length - 1], content: assistantText };
              return copy;
            });
          }
          if (event === "thinking") {
            try { setThinkingLabel(JSON.parse(data) as string); } catch { /* */ }
          }
          if (event === "sources") {
            try { setSources(JSON.parse(data) as SourceChunk[]); } catch { setSources([]); }
          }
          if (event === "note_saved") {
            showToast("Note saved");
            setNotesRefresh((n) => n + 1);
          }
          if (event === "web_sources") {
            try { setWebSources(JSON.parse(data) as WebSource[]); } catch { /* */ }
          }
        }
      }
      void refreshSessions();
    } catch { setError("Chat request failed."); }
    finally { setSending(false); setWaitingForFirst(false); }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !sending) {
      e.preventDefault();
      void sendMessage();
    }
  };

  const saveAsNote = useCallback(async (content: string) => {
    setPendingNoteContent(content);
    setSuggestedTitle("");
    setFetchingTitle(true);
    try {
      const title = await suggestNoteTitle(content);
      setSuggestedTitle(title);
    } catch {
      setSuggestedTitle(deriveTitle(content) || `Insight — p.${currentPage}`);
    } finally {
      setFetchingTitle(false);
    }
  }, [currentPage]);

  const confirmSaveNote = async (title: string) => {
    if (!pendingNoteContent) return;
    const content = pendingNoteContent;
    setPendingNoteContent(null);
    try {
      await createNote(bookId, {
        content,
        title: title || `Insight — p.${currentPage}`,
        type: "agent_insight",
        page_number: currentPage,
      });
      showToast("Saved as note");
      setNotesRefresh((n) => n + 1);
    } catch { showToast("Failed to save note."); }
  };

  const pdfUrl = getBookPdfUrl(bookId);

  return (
    <div className="flex flex-col h-screen" style={{ background: "#0E0E0E" }}>

      {/* ── Top bar ── */}
      <header
        className="flex items-center justify-between px-4 h-12 border-b flex-shrink-0"
        style={{ borderColor: "#242424", background: "rgba(14,14,14,0.9)" }}
      >
        <div className="flex items-center gap-3 min-w-0">
          <Link
            href="/"
            className="p-1.5 rounded-md transition-colors flex-shrink-0"
            style={{ color: "#737373" }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "#F0F0F0")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "#737373")}
          >
            <ArrowLeft size={15} />
          </Link>
          <div className="flex items-center gap-2 min-w-0 text-sm" style={{ color: "#737373" }}>
            <span>Tome</span>
            <span>/</span>
            <span className="truncate font-medium" style={{ color: "#F0F0F0" }}>
              {book?.title ?? "Loading…"}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3 flex-shrink-0">
          <span className="text-xs" style={{ color: "#737373" }}>p. {currentPage}</span>
          <button
            onClick={() => setNotesOpen(true)}
            className="flex items-center gap-1.5 px-3 h-7 rounded-md text-xs border transition-colors"
            style={{ borderColor: "#303030", color: "#F0F0F0", background: "#151515" }}
            onMouseEnter={(e) => (e.currentTarget.style.background = "#1C1C1C")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "#151515")}
          >
            <StickyNote size={13} />
            Notes
          </button>
        </div>
      </header>

      {/* ── Main: PDF + Chat ── */}
      <div className="flex flex-1 min-h-0">

        {/* PDF panel — 62% */}
        <div className="flex-shrink-0 min-h-0" style={{ width: "62%" }}>
          <PdfViewer url={pdfUrl} goToPage={goToPage} onPageChange={setCurrentPage} />
        </div>

        {/* Divider */}
        <div className="w-px flex-shrink-0" style={{ background: "#242424" }} />

        {/* Fix 6: min-w-0 prevents content from expanding the panel */}
        <div className="flex flex-col min-h-0 flex-1 min-w-0">

          {/* Sessions pill */}
          <div className="flex-shrink-0 border-b" style={{ borderColor: "#1C1C1C" }}>
            <button
              onClick={() => setSessionsExpanded((v) => !v)}
              className="w-full flex items-center justify-between px-4 h-9 text-xs transition-colors"
              style={{ color: "#737373" }}
              onMouseEnter={(e) => (e.currentTarget.style.color = "#F0F0F0")}
              onMouseLeave={(e) => (e.currentTarget.style.color = "#737373")}
            >
              {/* Fix 2: formatted session label */}
              <span>
                {activeSessionId
                  ? (() => {
                      const s = sessions.find((s) => s.id === activeSessionId);
                      return s ? formatSessionLabel(s) : "Active session";
                    })()
                  : "New conversation"}
              </span>
              <ChevronDown
                size={13}
                className={cn("transition-transform", sessionsExpanded && "rotate-180")}
              />
            </button>

            {sessionsExpanded && (
              <div className="px-3 pb-2 flex flex-wrap gap-1.5" style={{ borderTop: "1px solid #1C1C1C" }}>
                <button
                  onClick={startNewSession}
                  className="flex items-center gap-1 px-2.5 h-7 rounded-md text-xs border transition-colors"
                  style={{
                    borderColor: !activeSessionId ? "#6366F1" : "#303030",
                    color: !activeSessionId ? "#6366F1" : "#737373",
                    background: !activeSessionId ? "rgba(99,102,241,0.08)" : "transparent",
                  }}
                >
                  <Plus size={11} /> New
                </button>
                {/* Fix 2: use formatSessionLabel for each session pill */}
                {sessions.map((s) => (
                  <button
                    key={s.id}
                    onClick={() => void resumeSession(s)}
                    className="px-2.5 h-7 rounded-md text-xs border transition-colors"
                    style={{
                      borderColor: activeSessionId === s.id ? "#6366F1" : "#303030",
                      color: activeSessionId === s.id ? "#6366F1" : "#737373",
                      background: activeSessionId === s.id ? "rgba(99,102,241,0.08)" : "transparent",
                    }}
                  >
                    {formatSessionLabel(s)}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Fix 5: add containerRef + onScroll handler */}
          <div
            ref={messagesContainerRef}
            onScroll={handleMessagesScroll}
            className="flex-1 overflow-y-auto px-4 py-4 space-y-3"
          >
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full gap-4">
                <p className="text-xs text-center" style={{ color: "#737373" }}>
                  Ask a question about this book
                </p>
                <div className="grid grid-cols-1 gap-1.5 w-full max-w-[260px]">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => void sendMessage(s)}
                      className="flex items-center gap-2 px-3 py-2 rounded-lg border text-xs text-left transition-colors"
                      style={{ borderColor: "#242424", color: "#737373", background: "#151515" }}
                      onMouseEnter={(e) => { e.currentTarget.style.borderColor = "#303030"; e.currentTarget.style.color = "#F0F0F0"; }}
                      onMouseLeave={(e) => { e.currentTarget.style.borderColor = "#242424"; e.currentTarget.style.color = "#737373"; }}
                    >
                      <Sparkles size={11} className="text-indigo-400 flex-shrink-0" />
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((m, i) => {
                const last = i === messages.length - 1;
                return (
                  <MessageBubble
                    key={i}
                    role={m.role}
                    content={m.content}
                    isLast={last}
                    thinkingLabel={last ? thinkingLabel : ""}
                    waitingForFirst={last ? waitingForFirst : false}
                    sending={last ? sending : false}
                    onSaveAsNote={saveAsNote}
                  />
                );
              })
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Fix 4: Sources — collapsible vertical list */}
          {sources.length > 0 && (
            <div className="flex-shrink-0 border-t" style={{ borderColor: "#1C1C1C" }}>
              <button
                onClick={() => setSourcesExpanded((v) => !v)}
                className="w-full flex items-center gap-1.5 px-4 py-2 text-[11px] transition-colors"
                style={{ color: "#404040" }}
                onMouseEnter={(e) => (e.currentTarget.style.color = "#737373")}
                onMouseLeave={(e) => (e.currentTarget.style.color = "#404040")}
              >
                <ChevronRight
                  size={12}
                  className={cn("transition-transform flex-shrink-0", sourcesExpanded && "rotate-90")}
                />
                Sources ({sources.length})
              </button>

              {sourcesExpanded && (
                <div className="overflow-y-auto" style={{ maxHeight: "240px" }}>
                  {sources.map((s) => (
                    <button
                      key={s.chunk_id}
                      onClick={() => { const p = s.page_numbers[0]; if (p) setGoToPage(p); }}
                      className="w-full flex flex-col px-4 py-2 text-left border-t transition-colors"
                      style={{ borderColor: "#1C1C1C" }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = "#151515")}
                      onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                    >
                      <div className="flex items-center gap-2 flex-wrap">
                        <FileText size={11} style={{ color: "#737373", flexShrink: 0 }} />
                        <span className="text-xs font-medium truncate" style={{ color: "#F0F0F0", maxWidth: "160px" }}>
                          {s.chapter !== "Unknown" ? s.chapter : s.section}
                        </span>
                        <span className="text-xs" style={{ color: "#404040" }}>p.{s.page_numbers[0]}</span>
                        {s.relevance && (
                          <span
                            className="px-1 rounded text-[9px] font-medium"
                            style={
                              s.relevance === "high"
                                ? { background: "rgba(34,197,94,0.12)", color: "#22C55E" }
                                : s.relevance === "medium"
                                ? { background: "rgba(245,158,11,0.12)", color: "#F59E0B" }
                                : { background: "rgba(239,68,68,0.12)", color: "#EF4444" }
                            }
                          >
                            {s.relevance}
                          </span>
                        )}
                        {s.is_ahead_of_position && (
                          <span
                            className="px-1 rounded text-[9px] font-medium"
                            style={{ background: "rgba(249,115,22,0.12)", color: "#F97316" }}
                          >
                            ahead
                          </span>
                        )}
                      </div>
                      {s.quote && (
                        <p className="text-[11px] mt-1 truncate" style={{ color: "#737373" }}>
                          &ldquo;{s.quote}&rdquo;
                        </p>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Web sources */}
          {webSources.length > 0 && (
            <div className="flex-shrink-0 border-t" style={{ borderColor: "#1C1C1C" }}>
              <details>
                <summary
                  className="flex items-center gap-1.5 px-4 py-2 text-[11px] cursor-pointer list-none transition-colors"
                  style={{ color: "#404040" }}
                  onMouseEnter={(e) => ((e.currentTarget as HTMLElement).style.color = "#737373")}
                  onMouseLeave={(e) => ((e.currentTarget as HTMLElement).style.color = "#404040")}
                >
                  <ChevronRight size={12} className="flex-shrink-0" />
                  Web sources ({webSources.length})
                </summary>
                <div className="overflow-y-auto" style={{ maxHeight: "180px" }}>
                  {webSources.map((ws, i) => (
                    <div key={i} className="px-4 py-2 border-t" style={{ borderColor: "#1C1C1C" }}>
                      {ws.url ? (
                        <a
                          href={ws.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[11px] block truncate mb-1 hover:underline"
                          style={{ color: "#6366F1" }}
                        >
                          {ws.url}
                        </a>
                      ) : null}
                      <p className="text-[11px] leading-snug" style={{ color: "#737373" }}>
                        {ws.snippet.length > 200 ? ws.snippet.slice(0, 197) + "…" : ws.snippet}
                      </p>
                    </div>
                  ))}
                </div>
              </details>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="flex-shrink-0 px-4 py-2 flex items-center gap-2">
              <span className="text-xs flex-1" style={{ color: "#EF4444" }}>{error}</span>
              <button onClick={() => setError("")}>
                <X size={13} style={{ color: "#737373" }} />
              </button>
            </div>
          )}

          {/* Input area */}
          <div
            className="flex-shrink-0 px-4 pt-3 pb-4 border-t"
            style={{ borderColor: "#1C1C1C" }}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px]" style={{ color: "#404040" }}>
                {searchWholeBook ? "Searching whole book" : `Up to p.${currentPage}`}
              </span>
              <button
                onClick={() => setSearchWholeBook((v) => !v)}
                className="text-[10px] px-2 py-0.5 rounded-md border transition-colors"
                style={
                  searchWholeBook
                    ? { borderColor: "rgba(99,102,241,0.4)", color: "#6366F1", background: "rgba(99,102,241,0.08)" }
                    : { borderColor: "#303030", color: "#737373" }
                }
              >
                {searchWholeBook ? "Restrict to my page" : "Search whole book"}
              </button>
            </div>

            <div
              className="flex gap-2 items-end rounded-xl border px-3 py-2"
              style={{ borderColor: "#303030", background: "#151515" }}
            >
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask anything about this book…"
                rows={1}
                className="flex-1 bg-transparent text-sm resize-none overflow-hidden outline-none leading-relaxed min-w-0"
                style={{ color: "#F0F0F0", maxHeight: "120px" }}
              />
              <button
                onClick={() => void sendMessage()}
                disabled={sending || !input.trim()}
                className="flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center transition-colors disabled:opacity-30"
                style={{ background: "#6366F1" }}
              >
                {sending
                  ? <Loader2 size={13} className="animate-spin text-white" />
                  : <Send size={13} className="text-white" />}
              </button>
            </div>
            <p className="text-[10px] mt-1.5 px-1" style={{ color: "#404040" }}>
              Enter to send · Shift+Enter for new line
            </p>
          </div>
        </div>
      </div>

      <NotesDrawer
        bookId={bookId}
        currentPage={currentPage}
        open={notesOpen}
        onClose={() => setNotesOpen(false)}
        refreshToken={notesRefresh}
        bookTitle={book?.title}
      />

      {toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 animate-toast-in">
          <div
            className="px-4 py-2.5 rounded-lg text-sm shadow-xl border"
            style={{ background: "#1C1C1C", borderColor: "#303030", color: "#F0F0F0" }}
          >
            {toast}
          </div>
        </div>
      )}

      {pendingNoteContent !== null && (
        <SaveNoteDialog
          loading={fetchingTitle}
          title={suggestedTitle}
          content={pendingNoteContent}
          onTitleChange={setSuggestedTitle}
          onConfirm={() => void confirmSaveNote(suggestedTitle)}
          onCancel={() => setPendingNoteContent(null)}
        />
      )}
    </div>
  );
}
