"""生成原始JSON对应的Markdown，不用LLM判定坏例原因。"""
from pathlib import Path
from .metrics import distributions

METHODS = ("dense", "bm25", "hybrid")
KEYS = ("HitRate@1", "HitRate@3", "HitRate@5", "Recall@1", "Recall@3", "Recall@5", "MRR@3", "MRR@5")

def metric_table(outputs):
    lines = ["| Method | answerable / no-answer | "+" | ".join(KEYS)+" |",
             "|---|---|"+"---|"*len(KEYS)]
    for name in METHODS:
        summary = outputs[name]["overall"]
        row = []
        for key in KEYS:
            value = summary["metrics"][key]
            if key.startswith("HitRate"):
                row.append(f'{int(summary["hit_counts"][key])}/{summary["answerable_count"]} ({value:.2%})')
            else: row.append(f"{value:.4f}")
        lines.append(f'| {name} | {summary["answerable_count"]} / {summary["no_answer_count"]} | '+" | ".join(row)+" |")
    return "\n".join(lines)

def dev_report(outputs):
    return "# V0.2 Dev Sanity Run\n\n仅用于实现检查；不根据单题加入规则。测试集尚未运行。\n\n"+metric_table(outputs)+"\n\n"+ "\n".join(
        f'- {name}: latency mean {outputs[name]["latency_ms"]["mean"]:.3f} ms; inconsistent query rankings '
        f'{sum(not q["ranking_consistent"] for q in outputs[name]["queries"])}.'
        for name in METHODS)+"\n"

def test_report(outputs, comparison, provenance, stats, run_dir):
    output_path = Path(run_dir).relative_to(Path(__file__).resolve().parents[3]).as_posix()
    config_hash = comparison["config_sha256"]
    lines = [
        "# V0.2 Dense / BM25 / Hybrid Retrieval Report",
        "",
        "## Experiment setup",
        "",
        f'- Dataset checkpoint: `{provenance["dataset_checkpoint"]}`; version: `v0.2-dataset-1`.',
        f'- Dataset manifest SHA256: `{provenance["dataset_manifest_sha256"]}`.',
        f'- CONFIG SHA256: `{config_hash}`; parameters and implementation were locked after dev and before test.',
        f'- Python {provenance["python"]}; Ollama {provenance["ollama_version"]}; packages: `{provenance["packages"]}`.',
        f'- Embedding: `{provenance["embedding_model"]["name"]}`; digest: `{provenance["embedding_model"]["digest"]}`.',
        f'- Reused original RAGAdapter / Retriever / Ollama normalization / FAISS. Independent IndexFlatIP: '
        f'{stats["ntotal"]} vectors, dimension {stats["vector_dimension"]}, metadata {stats["metadata_count"]}.',
        "- Dev: 36 queries; test: 24 queries (20 answerable +4 no-answer). Each category test n=4.",
        f'- Raw JSON, index, provenance, integrity snapshots, warm-up and timings: `{output_path}/` (ignored).',
        "",
        "## Deterministic BM25 tokenizer / formula",
        "",
        "- Tokenizer: nfkc-ascii-id-cjk12-v1. NFKC +casefold; ASCII alphanumeric words/integers retained; "
        "hyphenated identifiers (ORBIT-3, RB-204, Aurora-X) kept whole. CJK contiguous runs emit each character "
        "and every adjacent bigram. Punctuation separates runs. No dictionary, network or query-specific rule.",
        "- For 项目负责人: 项、目、负、责、人、项目、目负、负责、责人.",
        "- IDF(t)=ln(1+(N-df(t)+0.5)/(df(t)+0.5)).",
        "- BM25(d,Q)=Σ IDF(t) · tf(t,d) · (k1+1) / "
        "[tf(t,d)+k1·(1-b+b·|d|/avgdl)], summed once per distinct query term.",
        "- Fixed k1=1.5, b=0.75. Document length counts both unigram and bigram tokens. "
        "No stopword filter/query-frequency multiplier. Zero-overlap scores are retained (0), "
        "ties use chunk_id ascending; they are not positive evidence.",
        "",
        "## Hybrid / RRF",
        "",
        "- Dense Top20 +BM25 Top20; equal weights; RRF(d)=Σ 1/(60+rank_i(d)); ranks start at 1.",
        "- Missing from a list contributes zero. Final ties use chunk_id ascending. No score addition or threshold.",
        "- Dense scores: normalized inner product (cosine). BM25 scores: lexical relevance. RRF scores: rank fusion. "
        "These three numeric scales are incomparable.",
        "",
        "## Overall test metrics",
        "",
        metric_table(outputs),
        "",
        "Recall is macro-averaged over answerable queries, not micro-averaged over evidence chunks. "
        "MRR@K uses the first relevant result within K; no-answer queries are excluded from all three metrics.",
        "",
        "## Category comparison",
        "",
        "| Category | Method | n (answerable / no-answer) | Hit@1 | Hit@3 | Hit@5 | Recall@1 | Recall@3 | Recall@5 | MRR@3 | MRR@5 |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for category in sorted(outputs["dense"]["categories"]):
        for name in METHODS:
            s = outputs[name]["categories"][category]
            if not s["metrics"]:
                lines.append(f'| {category} | {name} | 0 / {s["no_answer_count"]} | — | — | — | — | — | — | — | — |')
                continue
            entries = [f'{int(s["hit_counts"][f"HitRate@{k}"])}/{s["answerable_count"]}' for k in (1,3,5)]
            entries += [f'{s["metrics"][key]:.4f}' for key in ("Recall@1","Recall@3","Recall@5","MRR@3","MRR@5")]
            lines.append(f'| {category} | {name} | {s["answerable_count"]} / {s["no_answer_count"]} | '+" | ".join(entries)+" |")
    lines += ["", "## Retrieval latency", "",
              "| Method | samples | mean ms | median ms | p95 ms |",
              "|---|---|---|---|---|"]
    for name in METHODS:
        s = outputs[name]["latency_ms"]
        lines.append(f'| {name} | {s["n"]} | {s["mean"]:.3f} | {s["median"]:.3f} | {s["p95"]:.3f} |')
    lines += ["", "- Each backend warmed up once before test; every test query repeated 3 times in frozen order. "
              "72 timed searches per method. Warm-ups and index build excluded.",
              "- Dense/Hybrid include a real query embedding on every call; no embedding cache. BM25 is CPU-only. "
              "Methods run sequentially in fixed Dense → BM25 → Hybrid order per query/repetition.",
              "- E2E wall time includes tokenization/search/result conversion; component timings preserved in latency_raw.json. "
              "p95 uses linear interpolation; these correlated repetitions are not 72 independent questions.",
              "- Local small controlled synthetic benchmark, not a production throughput/SLA benchmark.", "",
              "## No-answer scores (not a rejection threshold)", "",
              "| Method / score scale | queries | Top1 mean | median | min | max |",
              "|---|---|---|---|---|---|"]
    for name in METHODS:
        s = outputs[name]["no_answer_scores"]["top1"]
        lines.append(f'| {name} / {outputs[name]["score_kind"]} | {s["n"]} | {s["mean"]:.6f} | '
                     f'{s["median"]:.6f} | {s["min"]:.6f} | {s["max"]:.6f} |')
    lines += ["", "Top-K may still be returned when no fact answers the query. Raw Top5 scores preserved; "
              "no threshold, generation or abstention decision is evaluated here.", "", "## Bad cases", "",
              "Automated candidates use complete evidence coverage at K=3 as 'correct'. Group D means "
              "Hybrid Recall@3 is below the better single method; it does not imply every metric is worse. "
              "Group F records annotated negatives in Top3 or missing relevant Top1 for ambiguity/hard-negative questions. "
              "It is not an LLM judgement.", ""]
    for kind, candidates in comparison["bad_case_groups"].items():
        lines += [f"### {kind}", "", f"{len(candidates)} test candidates.", ""]
        if not candidates:
            lines += ["No observed case of this type; no invented example.", ""]
        for candidate in candidates[:2]:
            lines += [f'**{candidate["id"]}: {candidate["query"]}**', "",
                      f'Expected: `{candidate["expected_chunk_ids"]}`.',
                      f'Recall@3: `{candidate["recall_at_3"]}`.', ""]
            for name in METHODS:
                lines += [f"{name} Top5:", ""]
                for r in candidate["top5"][name]:
                    lines.append(f'{r["rank"]}. `{r["chunk_id"]}` — {r["score"]:.6f}: {r["text"]}')
                lines.append("")
            lines += ["Engineering analysis (hypothesis, not causal proof): inspect exact entity/role/numeric "
                      "terms and missing evidence in the ranks above. BM25 weights lexical overlap; Dense "
                      "depends on embedding geometry; RRF rewards agreement in rank and can demote a relevant "
                      "item when only one method ranks it highly. No query-specific fix was applied.", ""]
    lines += ["## Default pipeline recommendation", ""]
    dense, lexical, hybrid = [outputs[name]["overall"]["metrics"] for name in METHODS]
    if hybrid["Recall@3"] > max(dense["Recall@3"], lexical["Recall@3"]):
        lines.append("Hybrid merits a later, separately approved candidate evaluation because Recall@3 is higher "
                     "in this test. This alone is insufficient to replace the default pipeline; compare rank quality, "
                     "latency and generalization on a larger independently authored corpus.")
    else:
        lines.append("Keep the existing default pipeline. Hybrid does not exceed the better single method's "
                     "Recall@3 in this small test, so the measured evidence does not justify automatic replacement. "
                     "Retain it as an experimental comparator; no Tool/default Retriever was changed.")
    lines += ["", "## Limitations / integrity", "",
              "- Small controlled synthetic benchmark: test=24, category=4, answerable=20. A single category hit "
              "changes its HitRate by 25 percentage points; report counts, not broad superiority claims.",
              "- 40 documents →40 chunks does not measure long-document chunking, OCR or cross-page retrieval. "
              "Handwritten templates, explicit negative clues and regular role identifiers introduce shortcuts. "
              "Test family holdout does not remove all design/style leakage.",
              "- Dev is an implementation sanity run, not extensive hyperparameter search. No test-derived "
              "tokenizer/parameter changes, no stronger model, no reranker, no default integration.",
              "- First repetition determines metrics; all repeat ranks/scores/timings are retained. "
              f'Rank-inconsistent queries: '+", ".join(f'{name}={sum(not q["ranking_consistent"] for q in outputs[name]["queries"])}' for name in METHODS)+".",
              "- Runner verified V0.1 25 hashes, V0.2 45 dataset hashes, tag, protected source/evidence/index "
              "fingerprints and clean nanobot both before and after. Final regression checks are reported separately.",
              "", "## Repeat this experiment", "",
              "Run from the repository with its nanobot venv. Use a new run directory; previous results cannot be overwritten.",
              "", "```powershell",
              "$python = '../nanobot/.venv/Scripts/python.exe'",
              "$run = 'artifacts/v0.2/retrieval/' + (Get-Date -Format 'yyyyMMddTHHmmss')",
              "& $python scripts/v0_2/run_retrieval.py --stage dev --run-dir $run",
              "# Review dev implementation behavior. CONFIG may be reused only if identical.",
              "& $python scripts/v0_2/run_retrieval.py --stage lock --run-dir $run",
              "& $python scripts/v0_2/run_retrieval.py --stage test --run-dir $run",
              "```", "",
              "The runner writes an immutable CONFIG/source-hash lock before test and refuses changes/overwrites. "
              "It never calls Qwen or AgentRunner. Preserve the first official run even if later runs differ.",
              ""]
    return "\n".join(lines)
