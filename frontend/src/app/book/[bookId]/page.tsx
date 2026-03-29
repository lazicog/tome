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
  StickyNote,
  Trash2,
  Search,
  Bookmark,
  Edit3,
  Save,
} from "lucide-react";

import PdfViewer from "../../../components/PdfViewer";
import {
  getBook,
  getBookPdfUrl,
  getApiBase,
  getSessionMessages,
  listSessions,
  listNotes,
  createNote,
  updateNote,
  deleteNote,
  type Book,
  type Session,
  type Note,
} from "../../../lib/api";
import { cn } from "../../../lib/utils";

type Message = { role: "user" | "assistant"; content: string; agentType?: string };
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

function agentLabel(t: string): string {
  if (t === "example") return "Example Agent";
  if (t === "context") return "Context Enricher";
  if (t === "quiz") return "Quiz Master";
  if (t === "summarize") return "Summarizer";
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
  { label: "Summarize the key points", icon: "summarize" },
];

const NOTE_TYPE_LABELS: Record<string, string> = {
  manual: "Manual",
  ai_summary: "AI Summary",
  highlight: "Highlight",
  agent_insight: "Saved Insight",
};

const NOTE_TYPE_COLORS: Record<string, string> = {
  manual: "bg-blue-500/15 text-blue-400",
  ai_summary: "bg-purple-500/15 text-purple-400",
  highlight: "bg-yellow-500/15 text-yellow-400",
  agent_insight: "bg-green-500/15 text-green-400",
};

export default function BookPage() {
  const params = useParams<{ bookId: string }>();
  const bookId = params.bookId;

  const [book, setBook] = useState<Book | null>(null);
  const [goToPage, setGoToPage] = useState<number | undefined>(undefined);
  const [currentPage, setCurrentPage] = useState(1);

  const [rightPanel, setRightPanel] = useState<"chat" | "notes">("chat");
  const [panelOpen, setPanelOpen] = useState(true);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [sources, setSources] = useState<SourceChunk[]>([]);
  const [sending, setSending] = useState(false);
  const [waitingForFirst, setWaitingForFirst] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");

  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Notes state
  const [notes, setNotes] = useState<Note[]>([]);
  const [noteSearch, setNoteSearch] = useState("");
  const [noteFilter, setNoteFilter] = useState<string>("");
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editContent, setEditContent] = useState("");
  const [showNewNote, setShowNewNote] = useState(false);
  const [newNoteTitle, setNewNoteTitle] = useState("");
  const [newNoteContent, setNewNoteContent] = useState("");

  const [searchWholeBook, setSearchWholeBook] = useState(false);

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

  const refreshNotes = useCallback(async () => {
    try {
      const data = await listNotes(bookId, {
        type: noteFilter || undefined,
        search: noteSearch || undefined,
      });
      setNotes(data);
    } catch { /* ignore */ }
  }, [bookId, noteFilter, noteSearch]);

  useEffect(() => { void refreshSessions(); }, [refreshSessions]);
  useEffect(() => { void refreshNotes(); }, [refreshNotes]);

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
          if (event === "note_saved") {
            showToast("Study notes saved automatically!");
            void refreshNotes();
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

  const saveAsNote = async (content: string) => {
    try {
      await createNote(bookId, {
        content,
        title: `Insight: ${content.slice(0, 60)}...`,
        type: "agent_insight",
        page_number: currentPage,
      });
      showToast("Saved as note!");
      void refreshNotes();
    } catch {
      showToast("Failed to save note.");
    }
  };

  const handleCreateNote = async () => {
    if (!newNoteContent.trim()) return;
    try {
      await createNote(bookId, {
        content: newNoteContent,
        title: newNoteTitle || `Note on page ${currentPage}`,
        type: "manual",
        page_number: currentPage,
      });
      setNewNoteTitle("");
      setNewNoteContent("");
      setShowNewNote(false);
      void refreshNotes();
      showToast("Note created!");
    } catch {
      showToast("Failed to create note.");
    }
  };

  const handleUpdateNote = async (noteId: string) => {
    try {
      await updateNote(noteId, { title: editTitle, content: editContent });
      setEditingNoteId(null);
      void refreshNotes();
      showToast("Note updated!");
    } catch {
      showToast("Failed to update note.");
    }
  };

  const handleDeleteNote = async (noteId: string) => {
    try {
      await deleteNote(noteId);
      void refreshNotes();
      showToast("Note deleted.");
    } catch {
      showToast("Failed to delete note.");
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
        <div className="flex items-center gap-2">
          <button
            onClick={() => { setRightPanel("chat"); setPanelOpen(true); }}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
              panelOpen && rightPanel === "chat"
                ? "bg-accent text-white"
                : "border border-border text-text-muted hover:text-text hover:bg-bg-hover"
            )}
          >
            <MessageSquare className="w-4 h-4" />
            Chat
          </button>
          <button
            onClick={() => { setRightPanel("notes"); setPanelOpen(true); }}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
              panelOpen && rightPanel === "notes"
                ? "bg-accent text-white"
                : "border border-border text-text-muted hover:text-text hover:bg-bg-hover"
            )}
          >
            <StickyNote className="w-4 h-4" />
            Notes
            {notes.length > 0 && (
              <span className="ml-1 px-1.5 py-0.5 rounded-full text-[10px] bg-accent/20 text-accent">{notes.length}</span>
            )}
          </button>
          {panelOpen && (
            <button
              onClick={() => setPanelOpen(false)}
              className="p-1.5 rounded-lg border border-border text-text-muted hover:text-text hover:bg-bg-hover transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Main split pane */}
      <div ref={containerRef} className="flex flex-1 min-h-0 overflow-hidden">
        {/* PDF Viewer */}
        <div style={{ width: panelOpen ? `${pdfWidth}%` : "100%" }} className="min-h-0 shrink-0">
          <PdfViewer url={pdfUrl} goToPage={goToPage} onPageChange={setCurrentPage} />
        </div>

        {/* Drag handle */}
        {panelOpen && (
          <div
            onMouseDown={onDragStart}
            className="resize-handle w-1.5 shrink-0 bg-border hover:bg-accent transition-colors flex items-center justify-center"
          >
            <GripVertical className="w-3 h-3 text-text-muted pointer-events-none" />
          </div>
        )}

        {/* Right panel */}
        {panelOpen && rightPanel === "chat" && (
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
                        <>
                          {m.content ? (
                            <div className="prose-chat text-sm max-w-none">
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                            </div>
                          ) : waitingForFirst ? (
                            <TypingIndicator />
                          ) : (
                            <span className="text-text-muted">...</span>
                          )}
                          {m.content && !sending && (
                            <button
                              onClick={() => void saveAsNote(m.content)}
                              className="mt-2 flex items-center gap-1 text-[10px] text-text-muted hover:text-accent transition-colors"
                            >
                              <Bookmark className="w-3 h-3" /> Save as note
                            </button>
                          )}
                        </>
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
                      className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-bg-input border border-border text-xs text-text-muted hover:text-accent hover:border-accent/40 transition-colors group relative"
                      title={s.quote || `Score: ${s.score.toFixed(3)}`}
                    >
                      <FileText className="w-3 h-3" />
                      <span className="max-w-[120px] truncate">{s.chapter !== "Unknown" ? s.chapter : s.section}</span>
                      <span className="text-text-muted/60">p.{s.page_numbers.join(",")}</span>
                      {s.relevance && (
                        <span className={cn(
                          "ml-0.5 px-1 rounded text-[9px] font-medium",
                          s.relevance === "high" ? "bg-green-500/15 text-green-400"
                            : s.relevance === "medium" ? "bg-yellow-500/15 text-yellow-400"
                            : "bg-red-500/15 text-red-400"
                        )}>
                          {s.relevance}
                        </span>
                      )}
                      {s.is_ahead_of_position && (
                        <span className="ml-0.5 px-1 rounded text-[9px] font-medium bg-orange-500/15 text-orange-400">
                          ahead
                        </span>
                      )}
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
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[10px] text-text-muted/70">
                  {searchWholeBook ? "Searching whole book" : `Searching up to page ${currentPage}`}
                </span>
                <button
                  onClick={() => setSearchWholeBook((v) => !v)}
                  className={cn(
                    "text-[10px] px-2 py-0.5 rounded border transition-colors",
                    searchWholeBook
                      ? "border-accent/40 text-accent bg-accent/10 hover:bg-accent/20"
                      : "border-border text-text-muted hover:text-text hover:bg-bg-hover"
                  )}
                >
                  {searchWholeBook ? "Restrict to my page" : "Search whole book"}
                </button>
              </div>
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

        {/* Notes panel */}
        {panelOpen && rightPanel === "notes" && (
          <div className="flex-1 flex flex-col min-h-0 min-w-0">
            {/* Notes toolbar */}
            <div className="flex items-center gap-2 px-3 py-2 border-b border-border bg-bg-card/50 shrink-0">
              <button
                onClick={() => { setShowNewNote(true); setNewNoteTitle(""); setNewNoteContent(""); }}
                className="shrink-0 flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium border border-border hover:bg-bg-hover transition-colors text-text-muted hover:text-text"
              >
                <Plus className="w-3 h-3" /> New Note
              </button>
              <div className="flex-1 relative">
                <Search className="w-3 h-3 absolute left-2 top-1/2 -translate-y-1/2 text-text-muted" />
                <input
                  type="text"
                  value={noteSearch}
                  onChange={(e) => setNoteSearch(e.target.value)}
                  placeholder="Search notes..."
                  className="w-full bg-bg-input border border-border rounded-lg pl-7 pr-2 py-1 text-xs text-text placeholder:text-text-muted focus:outline-none focus:border-accent transition-colors"
                />
              </div>
              <select
                value={noteFilter}
                onChange={(e) => setNoteFilter(e.target.value)}
                className="bg-bg-input border border-border rounded-lg px-2 py-1 text-xs text-text-muted focus:outline-none focus:border-accent"
              >
                <option value="">All types</option>
                <option value="manual">Manual</option>
                <option value="ai_summary">AI Summary</option>
                <option value="highlight">Highlight</option>
                <option value="agent_insight">Saved Insight</option>
              </select>
            </div>

            {/* New note form */}
            {showNewNote && (
              <div className="px-3 py-3 border-b border-border bg-bg-card/30 space-y-2">
                <input
                  type="text"
                  value={newNoteTitle}
                  onChange={(e) => setNewNoteTitle(e.target.value)}
                  placeholder={`Note title (page ${currentPage})`}
                  className="w-full bg-bg-input border border-border rounded-lg px-3 py-1.5 text-sm text-text placeholder:text-text-muted focus:outline-none focus:border-accent"
                />
                <textarea
                  value={newNoteContent}
                  onChange={(e) => setNewNoteContent(e.target.value)}
                  placeholder="Write your note..."
                  rows={4}
                  className="w-full bg-bg-input border border-border rounded-lg px-3 py-2 text-sm text-text placeholder:text-text-muted focus:outline-none focus:border-accent resize-none"
                />
                <div className="flex gap-2">
                  <button
                    onClick={() => void handleCreateNote()}
                    disabled={!newNoteContent.trim()}
                    className="px-3 py-1.5 rounded-lg bg-accent text-white text-xs font-medium hover:bg-accent-hover disabled:opacity-40 transition-colors flex items-center gap-1"
                  >
                    <Save className="w-3 h-3" /> Save
                  </button>
                  <button
                    onClick={() => setShowNewNote(false)}
                    className="px-3 py-1.5 rounded-lg border border-border text-xs text-text-muted hover:text-text hover:bg-bg-hover transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {/* Notes list */}
            <div className="flex-1 overflow-auto px-3 py-3 space-y-2">
              {notes.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full">
                  <StickyNote className="w-10 h-10 mb-4 text-text-muted opacity-30" />
                  <p className="text-sm text-text-muted mb-2">No notes yet</p>
                  <p className="text-xs text-text-muted/60">
                    Create manual notes, save AI responses, or ask the AI to summarize
                  </p>
                </div>
              ) : (
                notes.map((note) => (
                  <div key={note.id} className="rounded-lg border border-border bg-bg-card/50 p-3">
                    {editingNoteId === note.id ? (
                      <div className="space-y-2">
                        <input
                          type="text"
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          className="w-full bg-bg-input border border-border rounded px-2 py-1 text-sm text-text focus:outline-none focus:border-accent"
                        />
                        <textarea
                          value={editContent}
                          onChange={(e) => setEditContent(e.target.value)}
                          rows={4}
                          className="w-full bg-bg-input border border-border rounded px-2 py-1.5 text-sm text-text focus:outline-none focus:border-accent resize-none"
                        />
                        <div className="flex gap-2">
                          <button
                            onClick={() => void handleUpdateNote(note.id)}
                            className="px-2 py-1 rounded bg-accent text-white text-xs hover:bg-accent-hover transition-colors"
                          >
                            Save
                          </button>
                          <button
                            onClick={() => setEditingNoteId(null)}
                            className="px-2 py-1 rounded border border-border text-xs text-text-muted hover:bg-bg-hover transition-colors"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="flex items-start justify-between gap-2 mb-1.5">
                          <div className="flex items-center gap-2 flex-1 min-w-0">
                            <span className={cn("px-1.5 py-0.5 rounded text-[10px] font-medium shrink-0", NOTE_TYPE_COLORS[note.type] || "bg-bg-hover text-text-muted")}>
                              {NOTE_TYPE_LABELS[note.type] || note.type}
                            </span>
                            <span className="text-sm font-medium text-text truncate">{note.title || "Untitled"}</span>
                          </div>
                          <div className="flex items-center gap-1 shrink-0">
                            <button
                              onClick={() => {
                                setEditingNoteId(note.id);
                                setEditTitle(note.title);
                                setEditContent(note.content);
                              }}
                              className="p-1 rounded hover:bg-bg-hover text-text-muted hover:text-text transition-colors"
                            >
                              <Edit3 className="w-3 h-3" />
                            </button>
                            <button
                              onClick={() => void handleDeleteNote(note.id)}
                              className="p-1 rounded hover:bg-bg-hover text-text-muted hover:text-error transition-colors"
                            >
                              <Trash2 className="w-3 h-3" />
                            </button>
                          </div>
                        </div>
                        <div className="prose-chat text-xs max-w-none text-text-muted line-clamp-4">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>{note.content}</ReactMarkdown>
                        </div>
                        <div className="flex items-center gap-3 mt-2 text-[10px] text-text-muted/60">
                          {note.page_number && (
                            <button
                              onClick={() => setGoToPage(note.page_number!)}
                              className="hover:text-accent transition-colors flex items-center gap-0.5"
                            >
                              <FileText className="w-2.5 h-2.5" /> p.{note.page_number}
                            </button>
                          )}
                          {note.chapter && <span>{note.chapter}</span>}
                          <span>{new Date(note.created_at).toLocaleDateString()}</span>
                        </div>
                      </>
                    )}
                  </div>
                ))
              )}
            </div>

            {/* Quick highlight button */}
            <div className="px-3 py-2.5 border-t border-border shrink-0">
              <button
                onClick={() => {
                  setShowNewNote(true);
                  setNewNoteTitle(`Highlight - Page ${currentPage}`);
                  setNewNoteContent("");
                }}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg border border-border text-xs text-text-muted hover:text-text hover:bg-bg-hover transition-colors"
              >
                <Bookmark className="w-3.5 h-3.5" />
                Add highlight for page {currentPage}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-bg-card border border-border rounded-xl px-4 py-2.5 text-sm text-text shadow-lg animate-toast-in">
          {toast}
        </div>
      )}
    </div>
  );
}
