---
name: pdf-rag-pipeline
description: >-
  Build PDF processing and RAG retrieval pipelines using PyMuPDF, sentence-transformers,
  and ChromaDB. Use when implementing PDF text extraction, document chunking, embedding
  generation, vector storage, hybrid retrieval, or reranking for the HelpMeLearn system.
---

# PDF RAG Pipeline

## PDF Text Extraction with PyMuPDF

Extract text preserving structure, handling code blocks and tables.

```python
import fitz  # PyMuPDF

async def extract_pdf(file_path: str) -> list[PageContent]:
    doc = fitz.open(file_path)
    pages = []
    for page_num, page in enumerate(doc, start=1):
        blocks = page.get_text("dict")["blocks"]
        content = []
        for block in blocks:
            if block["type"] == 0:  # text block
                for line in block["lines"]:
                    text = "".join(span["text"] for span in line["spans"])
                    font_size = line["spans"][0]["size"] if line["spans"] else 12
                    is_heading = font_size > 14
                    content.append(TextBlock(text=text, is_heading=is_heading, font_size=font_size))
            elif block["type"] == 1:  # image block
                content.append(ImageBlock(bbox=block["bbox"]))
        pages.append(PageContent(page_num=page_num, blocks=content))
    doc.close()
    return pages
```

### TOC Extraction

Use the built-in TOC for chapter/section structure:

```python
toc = doc.get_toc()  # [[level, title, page_num], ...]
# level 1 = chapter, level 2 = section, level 3 = subsection
```

## Smart Chunking Strategy

Split by document structure, not arbitrary token counts.

```python
def chunk_document(pages: list[PageContent], toc: list) -> list[Chunk]:
    sections = split_by_toc(pages, toc)
    chunks = []
    for section in sections:
        text = section.full_text
        if len(text) <= MAX_CHUNK_TOKENS:
            chunks.append(make_chunk(text, section.metadata))
            continue
        # Split large sections at paragraph boundaries
        paragraphs = text.split("\n\n")
        current = ""
        for para in paragraphs:
            if is_code_block(para):
                # Code blocks stay atomic
                if current:
                    chunks.append(make_chunk(current, section.metadata))
                    current = ""
                chunks.append(make_chunk(para, section.metadata, content_type="code"))
            elif token_count(current + para) > MAX_CHUNK_TOKENS:
                chunks.append(make_chunk(current, section.metadata))
                current = para
            else:
                current += "\n\n" + para if current else para
        if current:
            chunks.append(make_chunk(current, section.metadata))
    return add_overlaps(chunks, overlap_tokens=128)
```

### Key Rules
- **Code blocks**: detect ``` fences, keep as single chunks tagged `content_type="code"`
- **Tables**: detect pipe-delimited or grid patterns, keep intact
- **Overlap**: 128 tokens between adjacent chunks for context continuity
- **Metadata**: every chunk gets `book_id`, `chapter`, `section`, `page_numbers`, `chunk_index`

## Embedding Generation

```python
from sentence_transformers import SentenceTransformer

class EmbeddingEngine:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(
            texts,
            batch_size=64,
            show_progress_bar=True,
            normalize_embeddings=True,
        )
        return embeddings.tolist()

    def embed_query(self, query: str) -> list[float]:
        return self.model.encode(query, normalize_embeddings=True).tolist()
```

## ChromaDB Storage

```python
import chromadb

client = chromadb.PersistentClient(path="./data/chroma")

def store_chunks(book_id: str, chunks: list[Chunk], embeddings: list[list[float]]):
    collection = client.get_or_create_collection(
        name=f"book_{book_id}",
        metadata={"hnsw:space": "cosine"},
    )
    collection.add(
        ids=[c.id for c in chunks],
        documents=[c.content for c in chunks],
        embeddings=embeddings,
        metadatas=[c.metadata_dict() for c in chunks],
    )
```

## Hybrid Retrieval with Reranking

Combine vector similarity with BM25, then rerank.

```python
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

class HybridRetriever:
    def __init__(self):
        self.cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    async def search(self, query: str, book_id: str, k: int = 5) -> list[ChunkResult]:
        collection = client.get_collection(f"book_{book_id}")

        # Vector search
        query_embedding = embedding_engine.embed_query(query)
        vector_results = collection.query(
            query_embeddings=[query_embedding],
            n_results=k * 3,
        )

        # BM25 keyword search over same collection
        all_docs = collection.get()
        bm25 = BM25Okapi([doc.split() for doc in all_docs["documents"]])
        bm25_scores = bm25.get_scores(query.split())
        bm25_top = sorted(
            enumerate(bm25_scores), key=lambda x: x[1], reverse=True
        )[:k * 3]

        # Merge candidates, deduplicate
        candidates = merge_results(vector_results, bm25_top, all_docs)

        # Rerank with cross-encoder
        pairs = [(query, c.content) for c in candidates]
        scores = self.cross_encoder.predict(pairs)
        ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)

        return [
            ChunkResult(content=c.content, score=float(s), metadata=c.metadata)
            for c, s in ranked[:k]
        ]
```

## Testing Retrieval Quality

Sanity-check retrieval before building agents on top:
1. Pick 10 questions you can answer from the book manually
2. Run retrieval, check if the correct chunks appear in top-5
3. Target: correct chunk in top-5 for at least 8/10 queries
4. If below target: adjust chunk size, overlap, or add BM25 weight tuning
