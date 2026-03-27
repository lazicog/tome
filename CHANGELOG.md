# Changelog

All notable changes to HelpMeLearn will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Project architecture and phased implementation plan
- 6 Cursor rules for automated code convention enforcement (project overview, Python backend, agent development, RAG pipeline, frontend Next.js, API design)
- 4 Cursor skills for domain expertise (LangGraph agents, PDF RAG pipeline, LangChain LLM providers, open-source packaging)
- Documentation system with Architecture Decision Records, development log, and changelog
- Multi-provider LLM support design via LangChain chat models (OpenAI, Anthropic, Ollama)
- Phase 1 backend scaffold with FastAPI routes for health, books upload/list/get, and chat streaming
- PDF ingestion pipeline: PyMuPDF extraction, semantic chunking with overlap, sentence-transformers embeddings, ChromaDB storage
- Hybrid retrieval baseline combining vector search and BM25 scoring
- Tutor agent streaming answers with source chunk citations over SSE
- Phase 1 frontend scaffold (Next.js) with library/upload view and per-book chat page
- Docker Compose setup and root `.env.example` + project README quick start
