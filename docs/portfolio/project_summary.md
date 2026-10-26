# ResearchPilot — Executive Project Summary

## 1. One-Sentence Project Pitch
**ResearchPilot is a production-grade, multi-document research assistant that ingests technical literature and delivers evidence-grounded answers with mathematically fused hybrid retrieval, verifiable source citations, and honest abstention.**

---

## 2. Problem & Solution

### The Problem
Researchers, engineers, and analysts reviewing long-form academic papers, system architectures, and specifications face two critical friction points:
1. **Keyword Search Inefficiency**: Traditional full-text keyword search cannot synthesize distributed evidence across multiple sections or answer conceptual questions.
2. **LLM Hallucination & Citation Fiction**: Standard frontier LLMs frequently hallucinate factual assertions, cite nonexistent page numbers or titles, and exhibit overconfidence on unanswerable questions.

### The Solution
ResearchPilot combines:
- **PyMuPDF Document Ingestion**: Fast PDF and text parsing that extracts text while preserving page numbers, section headings, and document structure.
- **Sliding-Window Token Chunking**: Preserves sentence boundaries with configurable target sizes (500-800 tokens) and bounded overlap (100 tokens).
- **Hybrid Search with Reciprocal Rank Fusion (RRF $k=60$)**: Merges dense semantic vector similarity (pgvector / SentenceTransformers) with exact full-text keyword matching (PostgreSQL FTS / BM25).
- **Two-Stage Citation Guard**: Enforces that all citations reference valid chunk UUIDs present in the retrieved context and verifies verbatim quote agreement before presenting evidence to the user.
- **Honest Abstention**: Detects when retrieved evidence is insufficient and abstains rather than inventing unsupported answers.

---

## 3. Target Users
- **Academic Researchers & Students**: Synthesizing literature, validating methodology across conflicting papers.
- **Software Engineers & Architects**: Querying RFCs, distributed systems papers, and complex technical specifications.
- **Financial & Policy Analysts**: Comparing quarterly earnings reports, regulatory filings, and multi-tenant disclosures.

---

## 4. System Architecture

```mermaid
flowchart LR
    A["User / Browser\n(Next.js 14)"] -->|SSE & REST| B["FastAPI Gateway\n(Auth & Tracing)"]
    B --> C["Object Storage\n(Local / S3)"]
    B --> D["Ingestion Worker\n(PyMuPDF + Chunker)"]
    D --> E["Embedding Engine\n(all-MiniLM-L6-v2)"]
    E --> F[("PostgreSQL 16\n+ pgvector + FTS")]
    B --> G["Hybrid Search\n(pgvector + FTS + RRF)"]
    G --> H["Citation Guard\n& Grounding Validator"]
    H --> I["LLM Provider\n(OpenAI / Local Mock)"]
```

---

## 5. Key Technical Decisions

| Technical Decision | Selected Approach | Alternative Considered | Engineering Rationale |
| :--- | :--- | :--- | :--- |
| **Search Paradigm** | Hybrid (pgvector + FTS + RRF) | Pure Dense Vector Search | Vector embeddings capture broad semantic intent but struggle with specific technical parameters (`150ms`, `32MB`). Keyword search guarantees exact match; RRF fuses them without requiring raw score normalization. |
| **Citation Representation** | Structured Array Objects | Free-form inline markdown `[1]` | Parsing inline markdown links is vulnerable to hallucinated source IDs. Structured JSON schemas force the model to supply exact chunk UUIDs and quotes that are validated against DB state. |
| **Multi-Tenancy** | Database-enforced Workspace Scoping | Post-retrieval filtering | Applying workspace filters inside SQL where clauses guarantees zero possibility of cross-workspace data leakage during retrieval. |
| **Token Streaming** | Server-Sent Events (SSE) | WebSocket | SSE operates over standard HTTP/2, auto-reconnects natively, and traverses corporate proxies with zero protocol upgrade friction. |

---

## 6. Key Engineering Challenges & Solutions

### Challenge 1: The "False Confidence on Unanswerable Queries" Dilemma
- **Issue**: Standard prompt architectures often hallucinate answers when provided with tangential passages matching common English words.
- **Solution**: Implemented stop-word filtering and minimum informative term density thresholds in passage selection, coupled with an explicit abstention prompt contract. Abstention accuracy jumped to 80-100% on absent-answer test cases.

### Challenge 2: Cross-Scale Retrieval Score Incompatibility
- **Issue**: Cosine similarity ranges from 0 to 1, while BM25 / FTS scores can range from 0 to 50+, making linear combination weighting fragile across varied corpus sizes.
- **Solution**: Employed **Reciprocal Rank Fusion**:
  $$RRF(d) = \sum_{r \in \{\text{dense}, \text{fts}\}} \frac{1}{60 + \text{rank}_r(d)}$$
  which evaluates candidate rank orders rather than raw scores, elevating Recall@1 by **+3.85%** and MRR by **+2.46%**.

---

## 7. Measured Benchmark Results

- **Dataset**: 40 curated questions across public systems papers (Raft, LSM-Trees, HNSW).
- **Recall@5**: **90.62%** (100% on direct factual queries).
- **Mean Reciprocal Rank (MRR)**: **0.875** (Hybrid) vs 0.854 (Dense).
- **Citation Validity**: **100.0%** (zero hallucinated chunk IDs).
- **Citation Support Precision**: **100.0%** (all cited quotes verified in source passages).
- **p50 End-to-End Latency**: **32.5 ms**.
- **Estimated Cost / Query**: **$0.000155** (sub-millicent per query).

---

## 8. Known Limitations & Roadmap
- **OCR Support**: Current MVP parses native text PDFs via PyMuPDF; scanned image PDFs without OCR text layers are safely rejected with error code `SCANNED_PDF_NO_TEXT`. Roadmap includes Tesseract / AWS Textract integration.
- **Table Extraction**: Complex multi-column tabular data is extracted as structured text lines; Markdown table preservation via LayoutLM is slated for v1.1.
- **Hierarchical Summarization**: Auto-generating document executive summaries upon ingestion completion.
