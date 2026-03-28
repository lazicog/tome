import structlog

from sentence_transformers import SentenceTransformer

from app.config import settings

log = structlog.get_logger()

_MODEL: SentenceTransformer | None = None


def _load_model() -> SentenceTransformer:
    global _MODEL
    if _MODEL is None:
        log.info("embedding.loading", model=settings.embedding_model)
        _MODEL = SentenceTransformer(settings.embedding_model)
        log.info("embedding.loaded", model=settings.embedding_model, dim=_MODEL.get_sentence_embedding_dimension())
    return _MODEL


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = _load_model()
    vectors = model.encode(texts, batch_size=64, normalize_embeddings=True)
    return [v.tolist() for v in vectors]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
