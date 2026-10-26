# ResearchPilot — 3-Minute Technical Recruiter / Interviewer Demo Script

This demo script is designed for live portfolio walkthroughs and technical interviews to showcase full-stack engineering ability, RAG pipeline architecture, and measurable AI reliability.

---

### Step 1: Login & Workspace Isolation (0:00 - 0:30)
- **Action**: Open the web application at `http://localhost:3000`.
- **Narration**:
  > *"ResearchPilot is designed around strict workspace-level multi-tenancy. Let's log in to our personal workspace. Notice that all document ingestion, search queries, and conversations are authorized at the database query level, preventing any cross-tenant data leakage."*
- **Click**: Sign In $\rightarrow$ Enter credentials $\rightarrow$ View the Workspace Dashboard.

---

### Step 2: Ingesting Research Literature (0:30 - 1:00)
- **Action**: Click **Upload Document**, drag and drop `raft_consensus.pdf` or `raft_consensus.txt`.
- **Narration**:
  > *"When we upload a PDF or text file, the API immediately validates the magic bytes, file extension, and 25MB size limit before saving it with a randomized UUID storage key to private object storage. The backend returns HTTP 202 Accepted, and an asynchronous worker parses page metadata with PyMuPDF, chunks the text with bounded token overlap, computes dense vector embeddings, and bulk-inserts them into PostgreSQL."*
- **Visual**: Show the real-time status badge transition from `Queued` $\rightarrow$ `Processing` $\rightarrow$ `Ready`.

---

### Step 3: Factual Question & Streaming Grounded Response (1:00 - 1:40)
- **Action**: Type: *"What is the range of randomized election timeouts in Raft?"* $\rightarrow$ Submit.
- **Narration**:
  > *"Notice the real-time token streaming over Server-Sent Events. The backend executed hybrid retrieval—querying dense vector embeddings alongside PostgreSQL full-text search and fusing candidate rankings using Reciprocal Rank Fusion (RRF $k=60$). The model synthesized an answer strictly grounded in the retrieved context: 150ms to 300ms."*
- **Visual**: Note the inline clickable citation pill `[1]` and latency metrics badge (e.g., `32ms`).

---

### Step 4: Inspecting Citation Grounding (1:40 - 2:10)
- **Action**: Click on the citation pill `[1]`.
- **Narration**:
  > *"Clicking the citation opens our slide-out Citation Inspector. ResearchPilot models citations as structured database entities rather than trusting free-form model text. The system automatically verifies two distinct dimensions: first, Citation Validity—confirming the passage belongs to an authorized document in context; second, Citation Support Precision—verifying that the quoted excerpt exists verbatim in the source document."*
- **Visual**: Highlight the green checkmark badges for *Valid Context Passage* and *Verbatim Quote Support*.

---

### Step 5: Honest Abstention on Unanswerable Query (2:10 - 2:35)
- **Action**: Type: *"What was Google's stock price on the day the Raft paper was published?"* $\rightarrow$ Submit.
- **Narration**:
  > *"A critical requirement for enterprise research assistants is avoiding overconfident hallucinations. When a query cannot be answered from the corpus, our grounded prompt boundaries and lexical filter recognize the lack of evidence and trigger honest abstention: 'I do not have sufficient evidence from the provided documents to answer this question.'"*
- **Visual**: Note the immediate abstention message without fabricated facts or fake citations.

---

### Step 6: Quantitative Benchmarks & Architecture Walkthrough (2:35 - 3:00)
- **Action**: Display `docs/portfolio/evaluation_report.md` and system architecture diagrams.
- **Narration**:
  > *"Rather than relying on subjective claims, we built a quantitative benchmarking toolkit. Across a 40-question labeled evaluation suite, hybrid search improved Recall@1 from 81.25% to 84.38% (+3.85%) and MRR from 0.854 to 0.875 with 100% citation validity and a 32ms p50 latency. The entire system is packaged with Docker Compose and automated GitHub Actions CI."*
- **Closing**: Open the floor for technical questions on chunking trade-offs, pgvector indexing, or RRF math.
