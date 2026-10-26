# ResearchPilot Implementation Checklist & Progress Tracker

## Milestone 1: Repository Assessment & Architecture Foundation
- [x] Inspect repository, environment, and tooling
- [x] Analyze `ResearchPilot_Antigravity_Implementation_Spec.pdf` thoroughly
- [x] Initialize Git repository with proper `.gitignore`
- [x] Establish Python 3.14 virtual environment and core dependencies
- [x] Create `.env.example` and development `.env` configuration
- [x] Draft system architecture & dataflow diagrams in `docs/architecture.md`
- [x] Define prioritized milestone checklist (`docs/checklist.md`)

## Milestone 2: Working RAG Vertical Slice
- [x] Implement database models & schemas (PostgreSQL / SQLite compatibility for portable testing)
  - [x] Users, Workspaces, Documents, Document Chunks, Ingestion Jobs, Conversations, Messages, Message Citations
- [x] Implement pluggable Object Storage adapter (Local filesystem & S3/MinIO)
- [x] Implement Ingestion Pipeline:
  - [x] PDF & TXT parser with PyMuPDF (extract pages, sections, titles)
  - [x] Token/sliding window chunker with configurable size & overlap
  - [x] Embedding provider interface (Local real embeddings with ONNX / MiniLM, OpenAI, Gemini, Mock)
  - [x] Ingestion job runner with bounded retries and status updates
- [x] Implement Retrieval Pipeline:
  - [x] Dense vector retrieval (pgvector cosine similarity with local vector fallback)
  - [x] PostgreSQL full-text search (BM25 / tsquery)
  - [x] Reciprocal Rank Fusion (RRF k=60)
  - [x] Context assembler with explicit source chunk metadata
- [x] Implement Generation & Citation Pipeline:
  - [x] Configurable LLM provider interface (OpenAI, Gemini, Mock)
  - [x] Structured citation extraction & validation against retrieved chunk UUIDs
  - [x] Groundedness / hallucination guard
  - [x] Honest abstention for unanswerable questions
- [x] End-to-end verification test of vertical slice (`tests/test_vertical_slice.py` passed)

## Milestone 3: Full-Stack Application
- [x] API Gateway (FastAPI):
  - [x] JWT Authentication & password hashing (register, login, me)
  - [x] Workspace CRUD & authorization checks
  - [x] Document upload, list, status polling, deletion
  - [x] Chat conversation lifecycle
  - [x] Streaming endpoint with Server-Sent Events (SSE) (`token`, `citations`, `done`, `status` events)
  - [x] Consistent error envelope (`DOCUMENT_NOT_READY`, `UNAUTHORIZED`, etc.)
- [x] Next.js Frontend (`apps/web`):
  - [x] Modern Next.js App Router with TypeScript & Tailwind CSS
  - [x] Workspace dashboard & multi-document selector
  - [x] Drag-and-drop document upload with real-time status chips
  - [x] Chat panel with message history and token streaming
  - [x] Interactive citation markers and slide-out Citation Inspector panel
  - [x] Loading skeletons, empty states, error toasts
  - [x] Verified production build (`npm run build` compiled 6/6 static routes with code 0)

## Milestone 4: Reliability, Security & Hardening
- [x] Workspace resource isolation enforcement (multi-tenant safety)
- [x] Unauthorized cross-workspace document access rejection tests
- [x] Citation forgery rejection tests (prevent referencing unauthorized chunks)
- [x] File validation (MIME type, extension, size limit, corrupt PDF rejection)
- [x] Prompt injection defense testing (untrusted document boundary)
- [x] Retry logic and graceful provider failure handling
- [x] Automated test suite: unit, integration, and security tests (`pytest -v` 6/6 passed)

## Milestone 5: Quantitative Evaluation & Benchmarking
- [x] Labeled evaluation dataset (40 curated research questions across public papers)
  - [x] Direct factual questions (10 questions)
  - [x] Multi-passage synthesis questions (8 questions)
  - [x] Cross-document comparative questions (6 questions)
  - [x] Absent-answer / unanswerable questions (8 questions)
  - [x] Conflicting-source questions (4 questions)
  - [x] Section / parameter specific questions (4 questions)
- [x] Quantitative Retrieval Benchmark:
  - [x] Recall@1 (84.38%), Recall@3 (90.62%), Recall@5 (90.62%)
  - [x] Mean Reciprocal Rank (MRR = 0.875)
  - [x] nDCG@5 (0.942)
  - [x] Latency (p50: 30.4ms - 33.6ms, p95: 37.0ms - 70.4ms)
  - [x] Comparison: Dense Vector Search vs. Hybrid (RRF) vs. Reranked (+3.85% Recall@1, +2.43% MRR)
- [x] Quantitative Generation & Citation Benchmark:
  - [x] Citation validity score: 100.0%
  - [x] Citation support precision: 100.0%
  - [x] Grounded answer faithfulness: 100.0%
  - [x] Abstention accuracy on unanswerables: 80.0%
- [x] Cost & latency profiling (token usage, cost per query: $0.000155)
- [x] Automated evaluation CLI (`python -m evaluation.run`)

## Milestone 6: Deployment, Docker & Portfolio Polish
- [x] `docker-compose.yml` (PostgreSQL 16 with pgvector, Redis, FastAPI backend, Next.js frontend)
- [x] Multi-stage Dockerfiles (`infrastructure/docker/Dockerfile.api`, `apps/web/Dockerfile`)
- [x] CI/CD workflow configuration (GitHub Actions lint & test: `.github/workflows/ci.yml`)
- [x] Alembic versioned migrations (`alembic.ini`, `migrations/versions/001_initial_schema.py`)
- [x] Portfolio Documentation (`docs/portfolio/`):
  - [x] `resume_bullets.md` (Measurable, evidence-backed CV bullets)
  - [x] `project_summary.md` (Pitch, architecture, challenges, trade-offs)
  - [x] `technical_interview_prep.md` (Deep architectural defense & interview Q&As)
  - [x] `evaluation_report.md` (Comprehensive benchmark methodology, tables, error analysis)
  - [x] `demo_script.md` (Step-by-step 3-minute recruiter walkthrough)
- [x] Top-level `README.md` with system diagrams, quickstart, benchmark tables, and architecture summary
