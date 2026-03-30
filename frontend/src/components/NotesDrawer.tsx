"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { X, Plus, Search, Pencil, Trash2, Check, ChevronDown, Download } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  listNotes,
  createNote,
  updateNote,
  deleteNote,
  type Note,
} from "@/lib/api";

type NoteType = "all" | "manual" | "ai_summary" | "highlight" | "agent_insight";

const TYPE_LABELS: Record<string, string> = {
  manual: "Manual",
  ai_summary: "AI Summary",
  highlight: "Highlight",
  agent_insight: "Insight",
};

const TYPE_COLORS: Record<string, string> = {
  manual: "#6366F1",
  ai_summary: "#22C55E",
  highlight: "#F59E0B",
  agent_insight: "#8B5CF6",
};

function NoteBadge({ type }: { type: string }) {
  return (
    <span
      className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium"
      style={{
        background: `${TYPE_COLORS[type] ?? "#6366F1"}18`,
        color: TYPE_COLORS[type] ?? "#6366F1",
      }}
    >
      {TYPE_LABELS[type] ?? type}
    </span>
  );
}

/** Minimal prose styles for notes — lighter than chat prose */
const noteProseClass = [
  "[&_p]:my-0.5 [&_p]:leading-relaxed",
  "[&_ul]:my-1 [&_ul]:pl-4 [&_ol]:my-1 [&_ol]:pl-4",
  "[&_li]:my-0",
  "[&_strong]:font-semibold [&_strong]:text-[#F0F0F0]",
  "[&_em]:italic",
  "[&_code]:bg-indigo-500/10 [&_code]:text-indigo-300 [&_code]:px-1 [&_code]:py-0.5 [&_code]:rounded [&_code]:text-[0.82em] [&_code]:font-mono",
  "[&_pre]:bg-[#0A0A0A] [&_pre]:border [&_pre]:border-[#242424] [&_pre]:rounded [&_pre]:p-2 [&_pre]:overflow-x-auto [&_pre]:my-1",
  "[&_pre_code]:bg-transparent [&_pre_code]:text-[#E0E0E0] [&_pre_code]:p-0",
  "[&_blockquote]:border-l-2 [&_blockquote]:border-indigo-500 [&_blockquote]:pl-3 [&_blockquote]:text-[#737373] [&_blockquote]:italic",
  "[&_h1]:font-semibold [&_h1]:text-[#F0F0F0] [&_h1]:text-sm [&_h1]:my-1",
  "[&_h2]:font-semibold [&_h2]:text-[#F0F0F0] [&_h2]:text-xs [&_h2]:my-1",
  "[&_h3]:font-medium [&_h3]:text-[#F0F0F0] [&_h3]:text-xs [&_h3]:my-0.5",
  "[&_a]:text-indigo-400 [&_a]:underline",
  "[&_hr]:border-[#242424] [&_hr]:my-2",
].join(" ");

interface Props {
  bookId: string;
  currentPage: number;
  open: boolean;
  onClose: () => void;
  bookTitle?: string;
  refreshToken?: number;
}

export default function NotesDrawer({ bookId, currentPage, open, onClose, bookTitle, refreshToken }: Props) {
  const [notes, setNotes] = useState<Note[]>([]);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<NoteType>("all");
  const [showFilterMenu, setShowFilterMenu] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newContent, setNewContent] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editContent, setEditContent] = useState("");
  const [viewingNote, setViewingNote] = useState<Note | null>(null);
  const viewModalRef = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    const params: { type?: string; search?: string } = {};
    if (filter !== "all") params.type = filter;
    if (search.trim()) params.search = search.trim();
    try {
      setNotes(await listNotes(bookId, params));
    } catch { /* silently fail */ }
  }, [bookId, filter, search]);

  useEffect(() => {
    if (open) load();
  }, [open, load, refreshToken]);

  async function handleCreate() {
    if (!newContent.trim()) return;
    await createNote(bookId, {
      title: newTitle.trim() || `Note — page ${currentPage}`,
      content: newContent.trim(),
      page_number: currentPage,
      type: "manual",
    });
    setCreating(false);
    setNewTitle("");
    setNewContent("");
    load();
  }

  async function handleSaveEdit(id: string) {
    await updateNote(id, { title: editTitle, content: editContent });
    setEditingId(null);
    load();
  }

  async function handleDelete(id: string) {
    await deleteNote(id);
    setViewingNote(null);
    load();
  }

  function startEdit(note: Note) {
    setViewingNote(null);
    setEditingId(note.id);
    setEditTitle(note.title);
    setEditContent(note.content);
  }

  function exportNotes() {
    // All currently visible notes exported as a single .md file
    const allNotes = notes;
    const title = bookTitle ?? "Book";
    const date = new Date().toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });

    const lines: string[] = [
      `# Notes — ${title}`,
      `*Exported: ${date}*`,
      "",
    ];

    for (const note of allNotes) {
      lines.push("---", "");
      lines.push(`## ${note.title}`);
      const meta: string[] = [`**Type:** ${TYPE_LABELS[note.type] ?? note.type}`];
      if (note.page_number) meta.push(`**Page:** ${note.page_number}`);
      if (note.chapter) meta.push(`**Chapter:** ${note.chapter}`);
      lines.push(meta.join(" · "));
      lines.push("");
      lines.push(note.content);
      lines.push("");
    }

    const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `notes-${title.toLowerCase().replace(/\s+/g, "-").slice(0, 40)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setViewingNote(null);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  if (!open) return null;

  const filterLabels: Record<NoteType, string> = {
    all: "All types",
    manual: "Manual",
    ai_summary: "AI Summary",
    highlight: "Highlight",
    agent_insight: "Insight",
  };

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-40 bg-black/30" onClick={onClose} />

      {/* Drawer */}
      <aside
        className="drawer-open fixed top-0 right-0 z-50 h-full w-[400px] flex flex-col border-l"
        style={{ background: "#111111", borderColor: "#242424" }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-4 h-12 border-b flex-shrink-0"
          style={{ borderColor: "#242424" }}
        >
          <span className="text-sm font-semibold" style={{ color: "#F0F0F0" }}>Notes</span>
          <div className="flex items-center gap-1">
            {notes.length > 0 && (
              <button
                onClick={exportNotes}
                className="p-1.5 rounded hover:bg-[#1C1C1C] transition-colors"
                title="Export as Markdown"
              >
                <Download size={14} style={{ color: "#737373" }} />
              </button>
            )}
            <button
              onClick={() => { setCreating(true); setNewTitle(""); setNewContent(""); }}
              className="p-1.5 rounded hover:bg-[#1C1C1C] transition-colors"
              title="New note"
            >
              <Plus size={15} style={{ color: "#F0F0F0" }} />
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded hover:bg-[#1C1C1C] transition-colors"
              title="Close"
            >
              <X size={15} style={{ color: "#737373" }} />
            </button>
          </div>
        </div>

        {/* Toolbar */}
        <div className="px-3 py-2 flex gap-2 flex-shrink-0 border-b" style={{ borderColor: "#1C1C1C" }}>
          <div className="flex-1 relative">
            <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: "#737373" }} />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search notes…"
              className="w-full pl-7 pr-3 h-7 rounded-md text-xs border outline-none focus:border-indigo-500/60 transition-colors"
              style={{ background: "#1C1C1C", borderColor: "#303030", color: "#F0F0F0" }}
            />
          </div>
          <div className="relative">
            <button
              onClick={() => setShowFilterMenu((v) => !v)}
              className="flex items-center gap-1 h-7 px-2.5 rounded-md text-xs border transition-colors"
              style={{ background: "#1C1C1C", borderColor: "#303030", color: "#737373" }}
            >
              {filterLabels[filter]}
              <ChevronDown size={11} />
            </button>
            {showFilterMenu && (
              <div
                className="absolute right-0 top-8 z-10 rounded-lg border py-1 min-w-[140px] shadow-xl"
                style={{ background: "#1C1C1C", borderColor: "#303030" }}
              >
                {(Object.keys(filterLabels) as NoteType[]).map((k) => (
                  <button
                    key={k}
                    onClick={() => { setFilter(k); setShowFilterMenu(false); }}
                    className="w-full text-left px-3 py-1.5 text-xs hover:bg-[#242424] transition-colors"
                    style={{ color: filter === k ? "#F0F0F0" : "#737373" }}
                  >
                    {filterLabels[k]}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* New note form */}
        {creating && (
          <div className="px-3 py-3 border-b flex-shrink-0" style={{ borderColor: "#242424" }}>
            <input
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder={`Note — page ${currentPage}`}
              className="w-full mb-2 px-3 h-7 rounded-md text-xs border outline-none focus:border-indigo-500/60 transition-colors"
              style={{ background: "#1C1C1C", borderColor: "#303030", color: "#F0F0F0" }}
            />
            <textarea
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              placeholder="Write your note… (Markdown supported)"
              rows={4}
              className="w-full px-3 py-2 rounded-md text-xs border outline-none focus:border-indigo-500/60 transition-colors resize-none mb-2 font-mono"
              style={{ background: "#1C1C1C", borderColor: "#303030", color: "#F0F0F0" }}
              autoFocus
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setCreating(false)}
                className="px-3 h-7 rounded-md text-xs border transition-colors hover:bg-[#1C1C1C]"
                style={{ borderColor: "#303030", color: "#737373" }}
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                className="px-3 h-7 rounded-md text-xs font-medium transition-colors"
                style={{ background: "#6366F1", color: "#F0F0F0" }}
              >
                Save note
              </button>
            </div>
          </div>
        )}

        {/* Notes list */}
        <div className="flex-1 overflow-y-auto">
          {notes.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full gap-2 px-4">
              <p className="text-xs text-center" style={{ color: "#737373" }}>
                {search ? "No notes match your search." : "No notes yet. Create one or ask a question to auto-save insights."}
              </p>
            </div>
          ) : (
            <div className="divide-y" style={{ borderColor: "#1C1C1C" }}>
              {notes.map((note) => (
                <div key={note.id} className="px-4 py-3 group">
                  {editingId === note.id ? (
                    <div>
                      <input
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        className="w-full mb-2 px-2 h-7 rounded-md text-xs border outline-none focus:border-indigo-500/60"
                        style={{ background: "#1C1C1C", borderColor: "#303030", color: "#F0F0F0" }}
                      />
                      <textarea
                        value={editContent}
                        onChange={(e) => setEditContent(e.target.value)}
                        rows={4}
                        className="w-full px-2 py-1.5 rounded-md text-xs border outline-none focus:border-indigo-500/60 resize-none mb-2 font-mono"
                        style={{ background: "#1C1C1C", borderColor: "#303030", color: "#F0F0F0" }}
                        autoFocus
                      />
                      <div className="flex justify-end gap-2">
                        <button
                          onClick={() => setEditingId(null)}
                          className="px-2 h-6 rounded text-xs border"
                          style={{ borderColor: "#303030", color: "#737373" }}
                        >
                          Cancel
                        </button>
                        <button
                          onClick={() => handleSaveEdit(note.id)}
                          className="p-1 rounded text-green-400"
                          title="Save"
                        >
                          <Check size={13} />
                        </button>
                      </div>
                    </div>
                  ) : (
                    /* View mode — click to open full-view modal */
                    <div className="cursor-pointer" onClick={() => setViewingNote(note)}>
                      <div className="flex items-start justify-between gap-2 mb-1">
                        <p className="text-xs font-medium leading-snug" style={{ color: "#F0F0F0" }}>
                          {note.title}
                        </p>
                        <div
                          className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <button onClick={() => startEdit(note)} className="p-1 rounded hover:bg-[#242424] transition-colors">
                            <Pencil size={11} style={{ color: "#737373" }} />
                          </button>
                          <button onClick={() => handleDelete(note.id)} className="p-1 rounded hover:bg-[#242424] transition-colors">
                            <Trash2 size={11} className="text-red-500/70" />
                          </button>
                        </div>
                      </div>
                      {/* Markdown preview — clipped to 3 lines */}
                      <div
                        className={`text-xs mb-2 line-clamp-3 ${noteProseClass}`}
                        style={{ color: "#737373" }}
                      >
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{note.content}</ReactMarkdown>
                      </div>
                      <div className="flex items-center gap-2">
                        <NoteBadge type={note.type} />
                        {note.page_number && (
                          <span className="text-xs" style={{ color: "#404040" }}>p. {note.page_number}</span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </aside>

      {/* Full-view note modal */}
      {viewingNote && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50" onClick={() => setViewingNote(null)} />
          <div
            ref={viewModalRef}
            className="relative w-full max-w-lg rounded-xl border shadow-2xl flex flex-col"
            style={{ background: "#161616", borderColor: "#303030", maxHeight: "72vh" }}
          >
            {/* Modal header */}
            <div className="flex items-center justify-between px-5 py-3 border-b flex-shrink-0" style={{ borderColor: "#242424" }}>
              <div className="flex items-center gap-2">
                <NoteBadge type={viewingNote.type} />
                {viewingNote.page_number && (
                  <span className="text-xs" style={{ color: "#737373" }}>p. {viewingNote.page_number}</span>
                )}
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => {
                    const lines = [
                      `# ${viewingNote.title}`,
                      `**Type:** ${TYPE_LABELS[viewingNote.type] ?? viewingNote.type}${viewingNote.page_number ? ` · **Page:** ${viewingNote.page_number}` : ""}`,
                      "",
                      viewingNote.content,
                    ];
                    const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement("a");
                    a.href = url;
                    a.download = `${viewingNote.title.toLowerCase().replace(/\s+/g, "-").slice(0, 50)}.md`;
                    a.click();
                    URL.revokeObjectURL(url);
                  }}
                  className="p-1.5 rounded hover:bg-[#242424] transition-colors"
                  title="Download as Markdown"
                >
                  <Download size={13} style={{ color: "#737373" }} />
                </button>
                <button onClick={() => startEdit(viewingNote)} className="p-1.5 rounded hover:bg-[#242424] transition-colors" title="Edit">
                  <Pencil size={13} style={{ color: "#737373" }} />
                </button>
                <button onClick={() => handleDelete(viewingNote.id)} className="p-1.5 rounded hover:bg-[#242424] transition-colors" title="Delete">
                  <Trash2 size={13} className="text-red-500/70" />
                </button>
                <button onClick={() => setViewingNote(null)} className="p-1.5 rounded hover:bg-[#242424] transition-colors ml-1" title="Close">
                  <X size={14} style={{ color: "#737373" }} />
                </button>
              </div>
            </div>

            {/* Modal body — full markdown render */}
            <div className="overflow-y-auto px-5 py-4">
              <h2 className="text-sm font-semibold mb-4" style={{ color: "#F0F0F0" }}>
                {viewingNote.title}
              </h2>
              <div className={`text-sm ${noteProseClass}`} style={{ color: "#C0C0C0" }}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{viewingNote.content}</ReactMarkdown>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
