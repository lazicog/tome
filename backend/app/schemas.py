from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ProcessingStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class BookResponse(BaseModel):
    id: str
    title: str
    file_name: str
    status: ProcessingStatus
    chunks: int = 0
    created_at: datetime


class BookListResponse(BaseModel):
    items: list[BookResponse]
    total: int
    page: int = 1
    limit: int = 100


class ChatMessage(BaseModel):
    role: str = Field(default="user")
    content: str


class ChatRequest(BaseModel):
    message: str
    chat_history: list[ChatMessage] = Field(default_factory=list)
    session_id: str | None = None
    current_page: int | None = None


class SourceChunk(BaseModel):
    chunk_id: str
    chapter: str
    section: str
    page_numbers: list[int]
    score: float
    relevance: str = "medium"
    quote: str = ""
    is_ahead_of_position: bool = False


class SessionResponse(BaseModel):
    id: str
    book_id: str
    created_at: str
    updated_at: str
    message_count: int = 0


class SessionMessagesResponse(BaseModel):
    session_id: str
    messages: list[ChatMessage]


class NoteCreate(BaseModel):
    page_number: int | None = None
    chapter: str | None = None
    title: str = ""
    content: str
    type: str = "manual"
    source_message_id: int | None = None
    tags: str = ""


class NoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    tags: str | None = None


class NoteResponse(BaseModel):
    id: str
    book_id: str
    page_number: int | None = None
    chapter: str | None = None
    title: str
    content: str
    type: str
    source_message_id: int | None = None
    tags: str
    created_at: str
    updated_at: str


class SuggestTitleRequest(BaseModel):
    content: str


class SuggestTitleResponse(BaseModel):
    title: str


class ErrorResponse(BaseModel):
    detail: str
