import hashlib

from sentence_transformers import SentenceTransformer

from app.config import settings


_MODEL: SentenceTransformer | None = None


def _load_model() -> SentenceTransformer:
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer(settings.embedding_model)
    return _MODEL


def _fallback_embedding(text: str, dims: int = 384) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values = [((digest[i % len(digest)] / 255.0) * 2.0) - 1.0 for i in range(dims)]
    return values


def embed_texts(texts: list[str]) -> list[list[float]]:
    try:
        model = _load_model()
        vectors = model.encode(texts, batch_size=64, normalize_embeddings=True)
        return [v.tolist() for v in vectors]
    except Exception:
        return [_fallback_embedding(t) for t in texts]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]
