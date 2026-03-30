"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { listBooks, uploadBook, reingestBook, deleteBook, type Book } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Upload, Loader2, Trash2, RefreshCw, BookOpen } from "lucide-react";

/* ── Status dot ── */
function StatusDot({ status }: { status: Book["status"] }) {
  const colors: Record<string, string> = {
    ready: "bg-green-500",
    processing: "bg-yellow-500 animate-pulse",
    queued: "bg-zinc-500 animate-pulse",
    failed: "bg-red-500",
  };
  const labels: Record<string, string> = {
    ready: "Ready",
    processing: "Processing…",
    queued: "Queued",
    failed: "Failed",
  };
  return (
    <span className="flex items-center gap-1.5">
      <span className={`inline-block w-1.5 h-1.5 rounded-full ${colors[status] ?? "bg-zinc-500"}`} />
      <span className="text-xs text-[#737373]">{labels[status] ?? status}</span>
    </span>
  );
}

/* ── Book card ── */
function BookCard({
  book,
  onOpen,
  onDelete,
  onReingest,
}: {
  book: Book;
  onOpen: () => void;
  onDelete: () => void;
  onReingest: () => void;
}) {
  const [hovered, setHovered] = useState(false);
  const date = new Date(book.created_at).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return (
    <div
      className="relative rounded-lg border p-4 cursor-pointer transition-colors duration-150"
      style={{
        background: "#151515",
        borderColor: hovered ? "#303030" : "#242424",
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={onOpen}
    >
      {/* Hover action icons */}
      <div
        className="absolute top-3 right-3 flex items-center gap-1 transition-opacity duration-100"
        style={{ opacity: hovered ? 1 : 0 }}
        onClick={(e) => e.stopPropagation()}
      >
        <button
          title="Re-ingest"
          onClick={onReingest}
          className="p-1 rounded text-[#737373] hover:text-[#F0F0F0] hover:bg-[#242424] transition-colors"
        >
          <RefreshCw size={13} />
        </button>
        <button
          title="Delete"
          onClick={onDelete}
          className="p-1 rounded text-[#737373] hover:text-red-400 hover:bg-[#242424] transition-colors"
        >
          <Trash2 size={13} />
        </button>
      </div>

      {/* Book icon */}
      <div className="mb-3">
        <div
          className="w-8 h-8 rounded-md flex items-center justify-center"
          style={{ background: "rgba(99,102,241,0.12)" }}
        >
          <BookOpen size={15} className="text-indigo-400" />
        </div>
      </div>

      {/* Title */}
      <p className="text-sm font-medium leading-snug mb-2 pr-10" style={{ color: "#F0F0F0" }}>
        {book.title}
      </p>

      {/* Meta row */}
      <div className="flex items-center justify-between">
        <StatusDot status={book.status} />
        <span className="text-xs" style={{ color: "#737373" }}>
          {book.chunks ? `${book.chunks} chunks · ` : ""}{date}
        </span>
      </div>
    </div>
  );
}

/* ── Toast ── */
function Toast({ message, onDone }: { message: string; onDone: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDone, 3000);
    return () => clearTimeout(t);
  }, [onDone]);
  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 animate-toast-in">
      <div
        className="px-4 py-2.5 rounded-lg text-sm shadow-xl border"
        style={{ background: "#1C1C1C", borderColor: "#303030", color: "#F0F0F0" }}
      >
        {message}
      </div>
    </div>
  );
}

/* ── Confirm dialog ── */
function ConfirmDialog({
  title,
  description,
  onConfirm,
  onCancel,
}: {
  title: string;
  description: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60" onClick={onCancel} />
      <div
        className="relative rounded-xl border p-6 w-full max-w-sm shadow-2xl"
        style={{ background: "#151515", borderColor: "#303030" }}
      >
        <h3 className="text-sm font-semibold mb-1" style={{ color: "#F0F0F0" }}>
          {title}
        </h3>
        <p className="text-sm mb-5" style={{ color: "#737373" }}>
          {description}
        </p>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={onCancel}>
            Cancel
          </Button>
          <Button variant="destructive" size="sm" onClick={onConfirm}>
            Delete
          </Button>
        </div>
      </div>
    </div>
  );
}

/* ── Main ── */
export default function HomePage() {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);

  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<Book | null>(null);
  const [draggingOver, setDraggingOver] = useState(false);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<"newest" | "oldest" | "az" | "za">("newest");

  const showToast = (msg: string) => setToast(msg);

  const displayedBooks = books
    .filter((b) => b.title.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => {
      if (sort === "newest") return +new Date(b.created_at) - +new Date(a.created_at);
      if (sort === "oldest") return +new Date(a.created_at) - +new Date(b.created_at);
      if (sort === "az") return a.title.localeCompare(b.title);
      return b.title.localeCompare(a.title);
    });

  const load = useCallback(async () => {
    try {
      setBooks(await listBooks());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  /* Auto-refresh while books are processing */
  useEffect(() => {
    const pending = books.some((b) => b.status === "processing" || b.status === "queued");
    if (!pending) return;
    const id = setInterval(async () => { setBooks(await listBooks()); }, 4000);
    return () => clearInterval(id);
  }, [books]);

  /* Body-level drag-and-drop */
  useEffect(() => {
    const onDragOver = (e: DragEvent) => { e.preventDefault(); setDraggingOver(true); };
    const onDragLeave = (e: DragEvent) => {
      if ((e.target as Element).tagName === "BODY") setDraggingOver(false);
    };
    const onDrop = (e: DragEvent) => {
      e.preventDefault();
      setDraggingOver(false);
      const file = e.dataTransfer?.files[0];
      if (file) handleFile(file);
    };
    document.addEventListener("dragover", onDragOver);
    document.addEventListener("dragleave", onDragLeave);
    document.addEventListener("drop", onDrop);
    return () => {
      document.removeEventListener("dragover", onDragOver);
      document.removeEventListener("dragleave", onDragLeave);
      document.removeEventListener("drop", onDrop);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleFile(file: File) {
    if (!file.name.toLowerCase().endsWith(".pdf")) { showToast("Only PDF files are supported."); return; }
    setUploading(true);
    try {
      await uploadBook(file);
      showToast("Upload started — processing in background.");
      setBooks(await listBooks());
    } catch {
      showToast("Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  async function handleReingest(book: Book) {
    try {
      await reingestBook(book.id);
      showToast(`Re-ingesting "${book.title}"…`);
      setBooks(await listBooks());
    } catch {
      showToast("Re-ingest failed.");
    }
  }

  async function handleDelete(book: Book) {
    setConfirmDelete(null);
    try {
      await deleteBook(book.id);
      showToast(`"${book.title}" deleted.`);
      setBooks((prev) => prev.filter((b) => b.id !== book.id));
    } catch {
      showToast("Delete failed.");
    }
  }

  return (
    <>
      {/* Drag overlay */}
      {draggingOver && (
        <div className="fixed inset-0 z-50 flex items-center justify-center pointer-events-none">
          <div className="absolute inset-4 rounded-2xl border-2 border-dashed border-indigo-500/60 bg-indigo-500/5" />
          <span className="relative text-sm font-medium text-indigo-400">Drop PDF to upload</span>
        </div>
      )}

      {/* Top bar */}
      <header
        className="sticky top-0 z-40 border-b"
        style={{ background: "rgba(14,14,14,0.85)", backdropFilter: "blur(10px)", borderColor: "#242424" }}
      >
        <div className="max-w-5xl mx-auto px-6 h-12 flex items-center justify-between">
          <span className="text-sm font-semibold tracking-tight" style={{ color: "#F0F0F0" }}>
            Tome
          </span>
          <Button
            size="sm"
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            className="gap-1.5 h-7 text-xs"
          >
            {uploading ? <Loader2 size={12} className="animate-spin" /> : <Upload size={12} />}
            Upload PDF
          </Button>
        </div>
      </header>

      <input
        ref={fileRef}
        type="file"
        accept=".pdf"
        className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); e.target.value = ""; }}
      />

      {/* Main content */}
      <main className="max-w-5xl mx-auto px-6 py-8">
        {loading ? (
          <div className="flex items-center justify-center h-48">
            <Loader2 size={20} className="animate-spin text-[#737373]" />
          </div>
        ) : books.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 gap-3 text-center">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center"
              style={{ background: "rgba(99,102,241,0.1)" }}
            >
              <BookOpen size={18} className="text-indigo-400" />
            </div>
            <div>
              <p className="text-sm font-medium" style={{ color: "#F0F0F0" }}>No books yet</p>
              <p className="text-xs mt-0.5" style={{ color: "#737373" }}>Upload a PDF to get started</p>
            </div>
            <Button size="sm" onClick={() => fileRef.current?.click()} className="gap-1.5 mt-1 h-7 text-xs">
              <Upload size={12} />
              Upload PDF
            </Button>
          </div>
        ) : (
          <>
            {/* Header + toolbar */}
            <div className="mb-5">
              <div className="flex items-baseline justify-between mb-3">
                <h1 className="text-base font-semibold" style={{ color: "#F0F0F0" }}>Your library</h1>
                <p className="text-xs" style={{ color: "#737373" }}>
                  {books.length} {books.length === 1 ? "book" : "books"}
                </p>
              </div>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <svg className="absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#737373" strokeWidth="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
                  <input
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search by title…"
                    className="w-full pl-7 pr-3 h-8 rounded-lg text-xs border outline-none transition-colors"
                    style={{ background: "#151515", borderColor: "#303030", color: "#F0F0F0" }}
                    onFocus={(e) => (e.currentTarget.style.borderColor = "rgba(99,102,241,0.5)")}
                    onBlur={(e) => (e.currentTarget.style.borderColor = "#303030")}
                  />
                </div>
                <select
                  value={sort}
                  onChange={(e) => setSort(e.target.value as typeof sort)}
                  className="h-8 px-2.5 rounded-lg text-xs border outline-none cursor-pointer"
                  style={{ background: "#151515", borderColor: "#303030", color: "#737373" }}
                >
                  <option value="newest">Newest</option>
                  <option value="oldest">Oldest</option>
                  <option value="az">A → Z</option>
                  <option value="za">Z → A</option>
                </select>
              </div>
            </div>

            {displayedBooks.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-40 gap-2">
                <p className="text-sm" style={{ color: "#737373" }}>No books match &ldquo;{search}&rdquo;</p>
                <button onClick={() => setSearch("")} className="text-xs underline" style={{ color: "#6366F1" }}>
                  Clear search
                </button>
              </div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {displayedBooks.map((book) => (
                  <BookCard
                    key={book.id}
                    book={book}
                    onOpen={() => router.push(`/book/${book.id}`)}
                    onReingest={() => handleReingest(book)}
                    onDelete={() => setConfirmDelete(book)}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </main>

      {toast && <Toast message={toast} onDone={() => setToast(null)} />}

      {confirmDelete && (
        <ConfirmDialog
          title="Delete book?"
          description={`"${confirmDelete.title}" and all its notes and sessions will be permanently removed.`}
          onConfirm={() => handleDelete(confirmDelete)}
          onCancel={() => setConfirmDelete(null)}
        />
      )}
    </>
  );
}
