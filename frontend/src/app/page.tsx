"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { listBooks, uploadBook, type Book } from "../lib/api";

export default function HomePage() {
  const [books, setBooks] = useState<Book[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await listBooks();
      setBooks(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load books");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const onUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      await uploadBook(file);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    }
  };

  return (
    <section>
      <h1 style={{ marginTop: 0 }}>Tome - Phase 1</h1>
      <p>Upload a technical PDF and chat with it.</p>

      <label style={{ display: "inline-block", padding: "0.8rem 1rem", background: "#1e293b", borderRadius: 8, cursor: "pointer" }}>
        Upload PDF
        <input type="file" accept="application/pdf" onChange={onUpload} style={{ display: "none" }} />
      </label>

      {error ? <p style={{ color: "#fca5a5" }}>{error}</p> : null}
      {loading ? <p>Loading books...</p> : null}

      <div style={{ marginTop: "1.5rem", display: "grid", gap: "0.8rem" }}>
        {books.map((book) => (
          <article key={book.id} style={{ border: "1px solid #334155", borderRadius: 10, padding: "0.9rem" }}>
            <h3 style={{ margin: "0 0 0.2rem" }}>{book.title}</h3>
            <p style={{ margin: "0 0 0.4rem", opacity: 0.8 }}>
              status: {book.status} | chunks: {book.chunks}
            </p>
            <Link href={`/chat/${book.id}`} style={{ color: "#93c5fd" }}>
              Open chat
            </Link>
          </article>
        ))}
      </div>
    </section>
  );
}
