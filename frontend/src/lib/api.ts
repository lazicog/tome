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

export type Note = {
  id: string;
  book_id: string;
  page_number: number | null;
  chapter: string | null;
  title: string;
  content: string;
  type: "manual" | "ai_summary" | "highlight" | "agent_insight";
  source_message_id: number | null;
  tags: string;
  created_at: string;
  updated_at: string;
};

export type ChatMode = "learn" | "research";

export type Model = {
  id: string;
  label: string;
  provider: string;
  is_default: boolean;
};

export async function listModels(): Promise<{ models: Model[]; default: string }> {
  const res = await fetch(`${API}/models`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return (await res.json()) as { models: Model[]; default: string };
}

export type NoteCreate = {
  content: string;
  title?: string;
  page_number?: number | null;
  chapter?: string | null;
  type?: string;
  source_message_id?: number | null;
  tags?: string;
};

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export function getApiBase() {
  return API;
}

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

export async function getBook(bookId: string): Promise<Book> {
  const res = await fetch(`${API}/books/${bookId}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return (await res.json()) as Book;
}

export async function reingestBook(bookId: string): Promise<Book> {
  const res = await fetch(`${API}/books/${bookId}/reingest`, { method: "POST" });
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return (await res.json()) as Book;
}

export async function deleteBook(bookId: string): Promise<void> {
  const res = await fetch(`${API}/books/${bookId}`, { method: "DELETE" });
  if (!res.ok) {
    throw new Error(await res.text());
  }
}

export function getBookPdfUrl(bookId: string): string {
  return `${API}/books/${bookId}/pdf`;
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

// Notes API

export async function listNotes(
  bookId: string,
  params?: { page?: number; type?: string; search?: string },
): Promise<Note[]> {
  const url = new URL(`${API}/books/${bookId}/notes`);
  if (params?.page != null) url.searchParams.set("page", String(params.page));
  if (params?.type) url.searchParams.set("type", params.type);
  if (params?.search) url.searchParams.set("search", params.search);

  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return (await res.json()) as Note[];
}

export async function createNote(bookId: string, data: NoteCreate): Promise<Note> {
  const res = await fetch(`${API}/books/${bookId}/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return (await res.json()) as Note;
}

export async function updateNote(
  noteId: string,
  data: { title?: string; content?: string; tags?: string },
): Promise<Note> {
  const res = await fetch(`${API}/notes/${noteId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return (await res.json()) as Note;
}

export async function deleteNote(noteId: string): Promise<void> {
  const res = await fetch(`${API}/notes/${noteId}`, { method: "DELETE" });
  if (!res.ok) {
    throw new Error(await res.text());
  }
}

export async function suggestNoteTitle(content: string): Promise<string> {
  const res = await fetch(`${API}/notes/suggest-title`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  if (!res.ok) {
    throw new Error(await res.text());
  }
  const data = (await res.json()) as { title: string };
  return data.title;
}
