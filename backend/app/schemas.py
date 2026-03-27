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


class SourceChunk(BaseModel):
    chunk_id: str
    chapter: str
    section: str
    page_numbers: list[int]
    score: float


class ErrorResponse(BaseModel):
    detail: str
