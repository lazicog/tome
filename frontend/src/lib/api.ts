export type Book = {
  id: string;
  title: string;
  file_name: string;
  status: "queued" | "processing" | "ready" | "failed";
  chunks: number;
  created_at: string;
};

export type Session = {
  id: string;
  book_id: string;
  created_at: string;
  updated_at: string;
  message_count: number;
};

export type SessionMessage = {
  role: "user" | "assistant";
  content: string;
};

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export async function listBooks(): Promise<Book[]> {
  const res = await fetch(`${API}/books`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(await res.text());
  }
  const data = (await res.json()) as { items: Book[] };
  return data.items;
}

export async function uploadBook(file: File): Promise<Book> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${API}/books`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return (await res.json()) as Book;
}

export async function listSessions(bookId: string): Promise<Session[]> {
  const res = await fetch(`${API}/sessions/book/${bookId}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return (await res.json()) as Session[];
}

export async function getSessionMessages(sessionId: string): Promise<SessionMessage[]> {
  const res = await fetch(`${API}/sessions/${sessionId}/messages`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(await res.text());
  }
  const data = (await res.json()) as { session_id: string; messages: SessionMessage[] };
  return data.messages;
}
