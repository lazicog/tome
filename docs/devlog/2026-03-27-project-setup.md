# 2026-03-27: Project Setup and Agent Infrastructure

## What was done

- Created the HelpMeLearn workspace and established the project vision: an open-source AI-powered learning companion for technical PDFs
- Designed the full system architecture (FastAPI + Next.js + LangGraph + ChromaDB) with a phased implementation plan
- Created 6 Cursor rules to enforce code conventions:
  - `project-overview.mdc` -- always-on project context (tech stack, structure, principles)
  - `python-backend.mdc` -- Python/FastAPI standards (typing, async, Pydantic, structlog)
  - `agent-development.mdc` -- LangGraph agent conventions (state, prompts, citations)
  - `rag-pipeline.mdc` -- RAG standards (chunking, metadata, hybrid retrieval)
  - `frontend-nextjs.mdc` -- Next.js/React patterns (App Router, shadcn/ui, SSE streaming)
  - `api-design.mdc` -- REST API conventions (Pydantic responses, SSE, pagination)
- Created 4 Cursor skills for domain expertise:
  - `langgraph-agents` -- StateGraph patterns, router/RAG node templates, streaming
  - `pdf-rag-pipeline` -- PyMuPDF extraction, smart chunking, ChromaDB, hybrid retrieval
  - `langchain-llm-providers` -- Multi-provider LLM factory, fallbacks, token tracking
  - `open-source-packaging` -- Docker Compose, README, CI/CD, pre-commit
- Set up the documentation system (ADRs, devlog, changelog) with an always-on Cursor rule to keep it maintained

## Key decisions made

- See [ADR-0001](../adr/0001-langchain-over-litellm.md): Chose LangChain chat models over LiteLLM (security breach)
- See [ADR-0002](../adr/0002-langgraph-for-orchestration.md): Chose LangGraph over CrewAI/AutoGen for agent orchestration
- Tech stack: Python (FastAPI) backend + Next.js frontend for open-source credibility
- ChromaDB + SQLite for zero-infrastructure local-first deployment

## Issues / Gotchas

- PowerShell `mkdir` doesn't accept multiple paths like bash's `mkdir -p`; need `New-Item -ItemType Directory -Force -Path` with comma-separated paths
- PowerShell `ls -la` doesn't work; use `Get-ChildItem -Force` instead

## Next steps

- Initialize git repository and make first commit with all rules, skills, and docs
- Begin Phase 1: project scaffolding (FastAPI backend, Next.js frontend, Docker setup)
- Build the PDF processing pipeline (upload, extract, chunk, embed, store)
- Wire up the basic Tutor agent with RAG retrieval and streaming chat
