"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { BookOpen, Upload, RefreshCw, Clock, CheckCircle, AlertCircle, Loader2, Trash2, Library } from "lucide-react";

import { listBooks, uploadBook, reingestBook, deleteBook, type Book } from "../lib/api";
import { cn } from "../lib/utils";

function StatusBadge({ status }: { status: Book["status"] }) {
  const map: Record<Book["status"], { label: string; cls: string; icon: React.ReactNode }> = {
    queued: { label: "Queued", cls: "bg-warning/15 text-warning", icon: <Clock className="w-3 h-3" /> },
    processing: { label: "Processing", cls: "bg-accent/15 text-accent", icon: <Loader2 className="w-3 h-3 animate-spin" /> },
    ready: { label: "Ready", cls: "bg-success/15 text-success", icon: <CheckCircle className="w-3 h-3" /> },
    failed: { label: "Failed", cls: "bg-error/15 text-error", icon: <AlertCircle className="w-3 h-3" /> },
  };
  const s = map[status];
  return (
    <span className={cn("inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium", s.cls)}>
      {s.icon} {s.label}
    </span>
  );
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return "";
  }
}

function Toast({ message, onDone }: { message: string; onDone: () => void }) {
  const [exiting, setExiting] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setExiting(true), 2500);
    const t2 = setTimeout(onDone, 2800);
    return () => { clearTimeout(t); clearTimeout(t2); };
  }, [onDone]);

  return (
    <div className={cn(
      "fixed bottom-6 right-6 z-50 px-4 py-2.5 rounded-lg bg-bg-card border border-border shadow-lg text-sm text-text",
      exiting ? "toast-exit" : "toast-enter"
    )}>
      {message}
    </div>
  );
}

export default function HomePage() {
  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [toast, setToast] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    setError("");
    try {
      const data = await listBooks();
      setBooks(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load books");
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    const hasInFlight = books.some((b) => b.status === "queued" || b.status === "processing");
    if (!hasInFlight) return;
    const timer = setInterval(() => void refresh(true), 4000);
    return () => clearInterval(timer);
  }, [books, refresh]);

  const handleUpload = async (file: File) => {
    if (file.type !== "application/pdf") {
      setError("Only PDF files are supported.");
      return;
    }
    setUploading(true);
    setError("");
    try {
      await uploadBook(file);
      setToast("Book uploaded! Processing will start shortly.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const onFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) void handleUpload(file);
    if (e.target) e.target.value = "";
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) void handleUpload(file);
  };

  const handleReingest = async (bookId: string) => {
    try {
      await reingestBook(bookId);
      setToast("Re-ingesting with improved pipeline...");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Re-ingest failed");
    }
  };

  const handleDelete = async (bookId: string, title: string) => {
    if (!confirm(`Delete "${title}"? This removes the book, its embeddings, and chat history.`)) return;
    try {
      await deleteBook(bookId);
      setToast("Book deleted.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  };

  return (
    <div className="space-y-8">
      {toast && <Toast message={toast} onDone={() => setToast("")} />}

      <div className="text-center space-y-2 pt-4">
        <h1 className="text-3xl font-bold text-text-heading">Your Library</h1>
        <p className="text-text-muted">Upload a technical PDF and learn with AI-powered tutoring, examples, and quizzes.</p>
      </div>

      {/* Upload zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
        className={cn(
          "border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all",
          dragOver ? "border-accent bg-accent/5" : "border-border hover:border-text-muted hover:bg-bg-card/50",
          uploading && "pointer-events-none opacity-60"
        )}
      >
        <input ref={fileInputRef} type="file" accept="application/pdf" onChange={onFileInput} className="hidden" />
        <Upload className="w-8 h-8 mx-auto mb-3 text-text-muted" />
        {uploading ? (
          <p className="text-text-muted flex items-center justify-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" /> Uploading...
          </p>
        ) : (
          <>
            <p className="text-text-heading font-medium">Drop a PDF here or click to browse</p>
            <p className="text-sm text-text-muted mt-1">Max 100MB</p>
          </>
        )}
      </div>

      {error && <p className="text-error text-sm text-center">{error}</p>}

      {loading ? (
        <div className="text-center py-12">
          <Loader2 className="w-6 h-6 animate-spin mx-auto text-text-muted" />
          <p className="text-text-muted mt-2 text-sm">Loading library...</p>
        </div>
      ) : books.length === 0 ? (
        <div className="text-center py-16">
          <Library className="w-12 h-12 mx-auto text-text-muted/30 mb-4" />
          <p className="text-text-heading font-medium mb-1">Your library is empty</p>
          <p className="text-text-muted text-sm">Upload your first PDF above to get started.</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {books.map((book) => (
            <article
              key={book.id}
              className="group bg-bg-card border border-border rounded-xl p-5 flex flex-col justify-between hover:border-text-muted transition-colors"
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-3">
                  <BookOpen className="w-5 h-5 text-accent shrink-0 mt-0.5" />
                  <StatusBadge status={book.status} />
                </div>
                <h3 className="text-text-heading font-semibold leading-snug line-clamp-2 mb-1">{book.title}</h3>
                <div className="flex items-center gap-2 text-xs text-text-muted">
                  <span>{book.chunks} chunks</span>
                  {book.created_at && (
                    <>
                      <span className="text-border">·</span>
                      <span>{formatDate(book.created_at)}</span>
                    </>
                  )}
                </div>
              </div>
              <div className="mt-4 flex items-center gap-2">
                {book.status === "ready" ? (
                  <>
                    <Link
                      href={`/book/${book.id}`}
                      className="flex-1 text-center px-3 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent-hover transition-colors"
                    >
                      Open
                    </Link>
                    <button
                      onClick={() => void handleReingest(book.id)}
                      title="Re-ingest with improved pipeline"
                      className="p-2 rounded-lg border border-border hover:bg-bg-hover transition-colors text-text-muted hover:text-text"
                    >
                      <RefreshCw className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => void handleDelete(book.id, book.title)}
                      title="Delete book"
                      className="p-2 rounded-lg border border-border hover:bg-error/10 hover:border-error/40 transition-colors text-text-muted hover:text-error"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </>
                ) : book.status === "failed" ? (
                  <button
                    onClick={() => void handleDelete(book.id, book.title)}
                    className="text-xs text-error hover:underline"
                  >
                    Delete failed upload
                  </button>
                ) : (
                  <span className="text-xs text-text-muted">Available when ready</span>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
