---
name: open-source-packaging
description: >-
  Package HelpMeLearn for open-source distribution with Docker Compose, README,
  CI/CD, and developer tooling. Use when creating Docker configuration, writing
  documentation, setting up GitHub Actions, configuring pre-commit hooks, or
  preparing the project for public release.
---

# Open Source Packaging

## Docker Compose (One-Command Setup)

Target: `docker compose up` starts everything.

```yaml
# docker-compose.yml
services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data        # SQLite + ChromaDB persistence
      - ./uploads:/app/uploads  # Uploaded PDFs
    env_file:
      - .env
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      backend:
        condition: service_healthy
```

### Backend Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Frontend Dockerfile

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
CMD ["node", "server.js"]
```

## .env.example

Document every variable with comments and sensible defaults:

```bash
# === LLM Configuration ===
# Supported providers: openai, anthropic, ollama
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
LLM_FALLBACK_MODEL=claude-sonnet-4-20250514
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=4096

# === API Keys (add the ones for your chosen provider) ===
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# === Local Models (Ollama) ===
OLLAMA_BASE_URL=http://localhost:11434

# === Embeddings ===
# Use "local" for sentence-transformers (no API key needed)
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# === App Settings ===
MAX_UPLOAD_SIZE_MB=100
LOG_LEVEL=info
```

## README Structure

```markdown
# HelpMeLearn

> AI-powered learning companion for technical books.

[Screenshot / Demo GIF]

## Features
- Upload technical PDFs and chat with their content
- AI-generated explanations, code examples, and analogies
- Interactive quizzes with spaced repetition
- Structured study paths with progress tracking
- Multi-provider LLM support (OpenAI, Anthropic, Ollama)

## Quick Start

### Docker (recommended)
    git clone https://github.com/yourname/helpmelearn
    cd helpmelearn
    cp .env.example .env
    # Edit .env with your API key
    docker compose up

### Manual Setup
[Python venv + npm instructions]

## Configuration
[Table of .env variables]

## Architecture
[Architecture diagram]

## Contributing
[Fork, branch, PR workflow]

## License
MIT
```

## Makefile for Developer Convenience

```makefile
.PHONY: dev install test lint format

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

dev:
	docker compose up --build

test:
	cd backend && pytest
	cd frontend && npm test

lint:
	cd backend && ruff check .
	cd frontend && npm run lint

format:
	cd backend && ruff format .
	cd frontend && npm run format
```

## GitHub Actions CI

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r backend/requirements.txt
      - run: cd backend && ruff check .
      - run: cd backend && pytest

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - run: cd frontend && npm ci
      - run: cd frontend && npm run lint
      - run: cd frontend && npm run build
```

## Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-eslint
    rev: v9.0.0
    hooks:
      - id: eslint
        files: frontend/.*\.[jt]sx?$
```

## License

Use MIT for maximum adoption. Create a `LICENSE` file at the repo root.
