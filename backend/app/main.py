import structlog
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.books import router as books_router
from app.api.routes.chat import router as chat_router
from app.api.routes.debug import router as debug_router
from app.api.routes.health import router as health_router
from app.api.routes.sessions import router as sessions_router
from app.config import settings

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    log.info(
        "startup.config",
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
        openai_key_set=bool(settings.openai_api_key),
        anthropic_key_set=bool(settings.anthropic_api_key),
        embedding_model=settings.embedding_model,
        top_k=settings.top_k_chunks,
        prefetch_mult=settings.retrieval_prefetch_multiplier,
        score_threshold=settings.retrieval_score_threshold,
        phase2_routing=settings.phase2_routing_enabled,
        sqlite_storage=settings.use_sqlite_storage,
    )
    try:
        from app.rag.embeddings import _load_model
        _load_model()
        log.info("startup.embedding_model_ready")
    except Exception as exc:
        log.error("startup.embedding_model_failed", error=str(exc))
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(books_router, prefix=settings.api_prefix)
app.include_router(chat_router, prefix=settings.api_prefix)
app.include_router(sessions_router, prefix=settings.api_prefix)
app.include_router(debug_router, prefix=settings.api_prefix)
