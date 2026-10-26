import os
import json
import csv
import time
from pathlib import Path
from typing import List, Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from services.api.src.database import Base
from services.api.src.models.user import User
from services.api.src.models.workspace import Workspace
from services.api.src.models.document import Document
from services.api.src.models.chunk import DocumentChunk
from services.api.src.services.document_service import DocumentService
from services.api.src.services.ingestion_worker import process_document
from services.api.src.rag.embeddings import get_embedding_provider
from services.api.src.rag.retrieval.dense import dense_search
from services.api.src.rag.retrieval.keyword import keyword_search
from services.api.src.rag.retrieval.hybrid import hybrid_search
from services.api.src.rag.retrieval.reranker import CrossEncoderReranker
from services.api.src.rag.generation import get_llm_provider
from services.api.src.rag.generation.citations import CitationValidator

from evaluation.metrics import (
    calculate_recall_at_k,
    calculate_mrr,
    calculate_ndcg_at_k,
    calculate_citation_metrics,
    calculate_answer_correctness,
)

EVAL_DB_FILE = "./eval_benchmark.db"
EVAL_DB_URL = f"sqlite:///{EVAL_DB_FILE}"

CORPUS_DIR = Path("evaluation/datasets/corpus")
DATASET_PATH = Path("evaluation/datasets/benchmark_qa.jsonl")
RESULTS_DIR = Path("evaluation/results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def percentile(data: List[float], p: float) -> float:
    if not data:
        return 0.0
    sorted_d = sorted(data)
    k = (len(sorted_d) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_d) - 1)
    d = k - f
    return sorted_d[f] + d * (sorted_d[c] - sorted_d[f])


def run_benchmarks():
    print("=" * 70, flush=True)
    print("RESEARCHPILOT QUANTITATIVE BENCHMARK RUNNER", flush=True)
    print("=" * 70, flush=True)

    # Disable background async worker during deterministic benchmark ingestion
    DocumentService.enqueue_ingestion = lambda doc_id: None

    if os.path.exists(EVAL_DB_FILE):
        try:
            os.remove(EVAL_DB_FILE)
        except Exception:
            pass

    eval_engine = create_engine(EVAL_DB_URL, connect_args={"check_same_thread": False})
    EvalSession = sessionmaker(autocommit=False, autoflush=False, bind=eval_engine)

    Base.metadata.create_all(bind=eval_engine)
    db = EvalSession()

    # Create fresh evaluation tenant
    eval_email = f"evaluator_{int(time.time())}@lab.org"
    user = User(email=eval_email, hashed_password="eval_hashed_pwd")
    db.add(user)
    db.commit()
    db.refresh(user)

    ws = Workspace(name="Evaluation Corpus Workspace", owner_id=user.id)
    db.add(ws)
    db.commit()
    db.refresh(ws)

    # 1. Ingest Corpus Documents
    print("\n[Phase 1] Ingesting evaluation corpus documents...", flush=True)
    doc_map: Dict[str, Document] = {}
    ingest_times: Dict[str, float] = {}

    for doc_file in sorted(CORPUS_DIR.glob("*.txt")):
        with open(doc_file, "rb") as f:
            content = f.read()

        t0 = time.perf_counter()
        doc, _ = DocumentService.upload_document(
            db=db,
            workspace_id=ws.id,
            filename=doc_file.name,
            content=content,
            mime_type="text/plain",
        )
        process_document(doc.id, db=db)
        db.refresh(doc)
        ingest_duration = (time.perf_counter() - t0) * 1000
        ingest_times[doc_file.name] = ingest_duration
        doc_map[doc_file.name] = doc
        print(f" -> Ingested {doc_file.name} ({doc.page_count} pages) in {ingest_duration:.1f}ms", flush=True)

    # 2. Load Evaluation Questions
    print("\n[Phase 2] Loading labeled evaluation dataset...", flush=True)
    questions = []
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                questions.append(json.loads(line))
    print(f" -> Loaded {len(questions)} labeled evaluation cases.", flush=True)

    # 3. Evaluate 3 Configurations:
    # A) Dense Retrieval Only
    # B) Hybrid Retrieval (Dense + Keyword FTS with RRF k=60)
    # C) Hybrid + Cross-Encoder Reranking
    configs = [
        {"name": "Dense Retrieval", "mode": "dense"},
        {"name": "Hybrid Retrieval (RRF)", "mode": "hybrid"},
        {"name": "Hybrid + Reranking", "mode": "hybrid_rerank"},
    ]

    embedder = get_embedding_provider()
    llm = get_llm_provider()
    reranker = CrossEncoderReranker()

    benchmark_summary: Dict[str, Any] = {}
    all_runs_records = []

    for cfg in configs:
        cfg_name = cfg["name"]
        mode = cfg["mode"]
        print(f"\n[Evaluating Configuration: {cfg_name}]", flush=True)

        recalls_at_1 = []
        recalls_at_3 = []
        recalls_at_5 = []
        mrrs = []
        ndcgs = []
        citation_validities = []
        citation_supports = []
        answer_correctnesses = []
        abstention_accuracies = []
        retrieval_latencies = []
        total_latencies = []
        input_tokens_list = []
        output_tokens_list = []

        category_stats: Dict[str, Dict[str, List[float]]] = {}

        for q in questions:
            qid = q["id"]
            cat = q["category"]
            query_text = q["question"]
            gold_kw = q["gold_keywords"]
            should_abstain = q["should_abstain"]

            target_doc_ids = [doc_map[fn].id for fn in q["document_filenames"] if fn in doc_map]

            if cat not in category_stats:
                category_stats[cat] = {"recall5": [], "correctness": []}

            t_start = time.perf_counter()

            # Retrieval
            t_ret_0 = time.perf_counter()
            if mode == "dense":
                q_vec = embedder.embed_query(query_text)
                candidates = dense_search(
                    db=db,
                    workspace_id=ws.id,
                    query_vector=q_vec,
                    document_ids=target_doc_ids,
                    top_k=5,
                )
            elif mode == "hybrid":
                candidates = hybrid_search(
                    db=db,
                    workspace_id=ws.id,
                    query_text=query_text,
                    embedder=embedder,
                    document_ids=target_doc_ids,
                    top_k=5,
                )
            else:  # hybrid_rerank
                initial_candidates = hybrid_search(
                    db=db,
                    workspace_id=ws.id,
                    query_text=query_text,
                    embedder=embedder,
                    document_ids=target_doc_ids,
                    candidate_pool_size=10,
                    top_k=10,
                )
                candidates = reranker.rerank(query_text, initial_candidates, top_k=5)

            ret_duration_ms = (time.perf_counter() - t_ret_0) * 1000
            retrieval_latencies.append(ret_duration_ms)

            retrieved_texts = [getattr(c, "content", "") for c in candidates]

            # Retrieval Metrics
            r1 = calculate_recall_at_k(retrieved_texts, gold_kw, k=1)
            r3 = calculate_recall_at_k(retrieved_texts, gold_kw, k=3)
            r5 = calculate_recall_at_k(retrieved_texts, gold_kw, k=5)
            mrr = calculate_mrr(retrieved_texts, gold_kw)
            ndcg = calculate_ndcg_at_k(retrieved_texts, gold_kw, k=5)

            if not should_abstain:
                recalls_at_1.append(r1)
                recalls_at_3.append(r3)
                recalls_at_5.append(r5)
                mrrs.append(mrr)
                ndcgs.append(ndcg)
                category_stats[cat]["recall5"].append(r5)

            # Generation & Answer Scoring
            answer_res = llm.generate(question=query_text, context_chunks=candidates)
            total_duration_ms = (time.perf_counter() - t_start) * 1000
            total_latencies.append(total_duration_ms)

            cit_metrics = calculate_citation_metrics(answer_res.citations)
            citation_validities.append(cit_metrics["citation_validity"])
            citation_supports.append(cit_metrics["citation_support"])

            is_abstained = answer_res.insufficient_evidence or CitationValidator.is_abstention(answer_res.answer)
            abstain_acc = 1.0 if (is_abstained == should_abstain) else 0.0
            abstention_accuracies.append(abstain_acc)

            correctness = calculate_answer_correctness(
                answer_text=answer_res.answer,
                gold_keywords=gold_kw,
                should_abstain=should_abstain,
                is_abstained=is_abstained,
            )
            answer_correctnesses.append(correctness)
            category_stats[cat]["correctness"].append(correctness)

            in_tokens = answer_res.input_tokens
            out_tokens = answer_res.output_tokens
            input_tokens_list.append(in_tokens)
            output_tokens_list.append(out_tokens)

            # Record single case
            all_runs_records.append({
                "config": cfg_name,
                "question_id": qid,
                "category": cat,
                "recall@5": r5 if not should_abstain else "N/A",
                "mrr": round(mrr, 3) if not should_abstain else "N/A",
                "citation_validity": round(cit_metrics["citation_validity"], 2),
                "citation_support": round(cit_metrics["citation_support"], 2),
                "answer_correctness": round(correctness, 2),
                "retrieval_latency_ms": round(ret_duration_ms, 2),
                "total_latency_ms": round(total_duration_ms, 2),
            })

        # Calculate Averages & Percentiles
        avg_r1 = sum(recalls_at_1) / len(recalls_at_1) if recalls_at_1 else 0.0
        avg_r3 = sum(recalls_at_3) / len(recalls_at_3) if recalls_at_3 else 0.0
        avg_r5 = sum(recalls_at_5) / len(recalls_at_5) if recalls_at_5 else 0.0
        avg_mrr = sum(mrrs) / len(mrrs) if mrrs else 0.0
        avg_ndcg = sum(ndcgs) / len(ndcgs) if ndcgs else 0.0

        avg_cit_val = sum(citation_validities) / len(citation_validities) if citation_validities else 0.0
        avg_cit_sup = sum(citation_supports) / len(citation_supports) if citation_supports else 0.0
        avg_correctness = sum(answer_correctnesses) / len(answer_correctnesses) if answer_correctnesses else 0.0
        avg_abstention_acc = sum(abstention_accuracies) / len(abstention_accuracies) if abstention_accuracies else 0.0

        p50_total = percentile(total_latencies, 50)
        p95_total = percentile(total_latencies, 95)
        p50_ret = percentile(retrieval_latencies, 50)
        p95_ret = percentile(retrieval_latencies, 95)

        avg_in_tok = sum(input_tokens_list) / len(input_tokens_list) if input_tokens_list else 0
        avg_out_tok = sum(output_tokens_list) / len(output_tokens_list) if output_tokens_list else 0

        avg_query_cost_usd = (avg_in_tok * 0.15 + avg_out_tok * 0.60) / 1_000_000

        cat_breakdown = {}
        for cat, vals in category_stats.items():
            cat_breakdown[cat] = {
                "avg_recall5": round(sum(vals["recall5"]) / len(vals["recall5"]) if vals["recall5"] else 1.0, 4),
                "avg_correctness": round(sum(vals["correctness"]) / len(vals["correctness"]) if vals["correctness"] else 0.0, 4),
            }

        benchmark_summary[cfg_name] = {
            "recall@1": round(avg_r1, 4),
            "recall@3": round(avg_r3, 4),
            "recall@5": round(avg_r5, 4),
            "mrr": round(avg_mrr, 4),
            "ndcg@5": round(avg_ndcg, 4),
            "citation_validity": round(avg_cit_val, 4),
            "citation_support": round(avg_cit_sup, 4),
            "answer_correctness": round(avg_correctness, 4),
            "abstention_accuracy": round(avg_abstention_acc, 4),
            "p50_latency_ms": round(p50_total, 2),
            "p95_latency_ms": round(p95_total, 2),
            "retrieval_p50_ms": round(p50_ret, 2),
            "retrieval_p95_ms": round(p95_ret, 2),
            "avg_input_tokens": round(avg_in_tok, 1),
            "avg_output_tokens": round(avg_out_tok, 1),
            "est_cost_per_query_usd": f"${avg_query_cost_usd:.6f}",
            "categories": cat_breakdown,
        }

        print(f" -> Recall@5: {avg_r5 * 100:.1f}% | MRR: {avg_mrr:.3f} | Citation Validity: {avg_cit_val * 100:.1f}%", flush=True)
        print(f" -> Answer Correctness: {avg_correctness * 100:.1f}% | Abstention Accuracy: {avg_abstention_acc * 100:.1f}%", flush=True)
        print(f" -> p50 Latency: {p50_total:.1f}ms | p95 Latency: {p95_total:.1f}ms", flush=True)

    # 4. Save Artifacts
    json_path = RESULTS_DIR / "benchmark_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(benchmark_summary, f, indent=2)
    print(f"\n[Saved JSON Report to {json_path}]", flush=True)

    csv_path = RESULTS_DIR / "benchmark_runs.csv"
    if all_runs_records:
        keys = all_runs_records[0].keys()
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(all_runs_records)
        print(f"[Saved Detailed Query Runs CSV to {csv_path}]", flush=True)

    # Clean up DB
    db.close()
    eval_engine.dispose()
    if os.path.exists(EVAL_DB_FILE):
        try:
            os.remove(EVAL_DB_FILE)
        except Exception:
            pass

    return benchmark_summary


if __name__ == "__main__":
    run_benchmarks()
