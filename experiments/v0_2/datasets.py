"""V0.2 离线数据契约校验。只读取 corpus；不调用 Embedding、Retriever 或 Agent。"""
from collections import Counter
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import unicodedata

RETRIEVAL_CATEGORIES = {
    "exact_keyword", "semantic_paraphrase", "entity_ambiguity",
    "hard_negative", "multi_evidence", "no_answer",
}
ROUTING_CATEGORIES = {
    "general_no_tool", "private_single_fact", "private_multi_evidence",
    "private_no_answer", "ambiguous_boundary",
}
TOOL = "search_knowledge_base"


def normalize_query(value: str) -> str:
    # 保留数字：不能把 RX-41R2 / RX-41R3 归一化为同一实体。
    value = unicodedata.normalize("NFKC", value).casefold()
    return "".join(c for c in value if not c.isspace()
                   and unicodedata.category(c)[0] not in {"P", "Z"})


def load_bundle(root: Path) -> dict:
    base = Path(root) / "eval/v0.2"
    names = {"corpus": "corpus_manifest.json", "retrieval": "retrieval_golden.json",
             "routing": "agent_routing_golden.json", "split": "split_manifest.json",
             "config": "dataset_config.json", "freeze": "freeze_manifest.json"}
    return {key: json.loads((base / name).read_text(encoding="utf-8"))
            for key, name in names.items()}


def verify_lock(root: Path, manifest: dict) -> list[str]:
    """校验运行前锁定的数据；禁止越过仓库范围读取哈希目标。"""
    errors = []
    entries = manifest.get("files")
    if not isinstance(entries, dict) or not entries:
        return ["freeze.files must be a nonempty mapping"]
    root = Path(root).resolve()
    for name, digest in entries.items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or not str(name).startswith("eval/v0.2/"):
            errors.append(f"unsafe frozen path: {name}")
        elif not path.is_file():
            errors.append(f"missing frozen file: {name}")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            errors.append(f"frozen hash mismatch: {name}")
    return errors


def validate_bundle(bundle: dict, root: Path | None = None) -> dict:
    """错误阻止运行；近似重复只提示，保留全部问题，不自动删除。"""
    errors, warnings = [], []
    chunks = bundle["corpus"].get("chunks", [])
    documents = bundle["corpus"].get("documents", [])
    chunk_ids = [c.get("chunk_id") for c in chunks]
    if any(not isinstance(i, str) or not i for i in chunk_ids):
        errors.append("corpus chunk_id must be nonempty string")
    if len({i for i in chunk_ids if isinstance(i, str)}) != len(chunk_ids):
        errors.append("duplicate corpus chunk_id")
    known = {i for i in chunk_ids if isinstance(i, str)}
    sources = [d.get("source") for d in documents]
    if len(set(sources)) != len(sources):
        errors.append("duplicate corpus document source")
    for c in chunks:
        if c.get("source") not in sources or not isinstance(c.get("text"), str) or not c["text"].strip():
            errors.append("chunk must have a known source and nonempty text")
    versions = [bundle[k].get("version") for k in ["corpus", "retrieval", "routing", "split", "freeze"]]
    if any(v != bundle["config"].get("dataset_version") for v in versions):
        errors.append("dataset version mismatch")
    families = bundle["split"].get("family_splits", {})
    all_records, seen_ids, seen_queries, stats = [], set(), {}, {}
    for suite, legal in [("retrieval", RETRIEVAL_CATEGORIES), ("routing", ROUTING_CATEGORIES)]:
        items = bundle[suite].get("items", [])
        if not items:
            errors.append(f"{suite}: empty dataset")
        category_split = {c: {"dev": 0, "test": 0} for c in sorted(legal)}
        for item in items:
            ident, query, category = item.get("id"), item.get("query"), item.get("category")
            prefix = f"{suite}/{ident}"
            if not isinstance(ident, str) or not ident.strip():
                errors.append(f"{prefix}: id must be nonempty string")
            elif ident in seen_ids:
                errors.append(f"{prefix}: duplicate ID across datasets/splits")
            if isinstance(ident, str):
                seen_ids.add(ident)
            if not isinstance(query, str) or not query.strip():
                errors.append(f"{prefix}: query must be nonempty string")
            else:
                norm = normalize_query(query)
                if not norm:
                    errors.append(f"{prefix}: query empty after normalization")
                elif norm in seen_queries:
                    errors.append(f"{prefix}: duplicate normalized query with {seen_queries[norm]}")
                seen_queries[norm] = ident
                all_records.append((suite, item, norm))
            split, family = item.get("split"), item.get("family_id")
            if category not in legal:
                errors.append(f"{prefix}: illegal category")
            if split not in {"dev", "test"}:
                errors.append(f"{prefix}: illegal split")
            elif category in legal:
                category_split[category][split] += 1
            if family not in families or families.get(family) != split:
                errors.append(f"{prefix}: family crosses dev/test or is unknown")
            refs = item.get("expected_chunk_ids")
            if not isinstance(refs, list) or any(not isinstance(r, str) for r in refs):
                errors.append(f"{prefix}: expected_chunk_ids must be string list")
                refs = []
            if len(set(refs)) != len(refs):
                errors.append(f"{prefix}: duplicate evidence")
            if set(refs) - known:
                errors.append(f"{prefix}: unknown referenced chunk")
            answerable = item.get("answerable")
            if type(answerable) is not bool:
                errors.append(f"{prefix}: answerable must be boolean")
            elif answerable != bool(refs):
                errors.append(f"{prefix}: answerable/evidence mismatch")
            for field in ["notes", "expected_answer"]:
                if not isinstance(item.get(field), str) or not item[field].strip():
                    errors.append(f"{prefix}: missing {field}")
            negatives = item.get("hard_negative_chunk_ids", [])
            if not isinstance(negatives, list) or any(not isinstance(r, str) for r in negatives):
                errors.append(f"{prefix}: invalid hard negatives")
            elif len(set(negatives)) != len(negatives) or set(negatives) - known or set(negatives) & set(refs):
                errors.append(f"{prefix}: unknown/duplicate/positive hard negative")
            if suite == "retrieval":
                if category == "multi_evidence" and len(refs) < 2:
                    errors.append(f"{prefix}: multi_evidence needs at least two chunks")
                if (category == "no_answer") != (answerable is False):
                    errors.append(f"{prefix}: no_answer category/answerability mismatch")
            else:
                tool = item.get("expected_tool")
                if "expected_tool" not in item or tool not in {None, TOOL}:
                    errors.append(f"{prefix}: illegal/missing expected_tool")
                if category == "general_no_tool" and (tool is not None or refs):
                    errors.append(f"{prefix}: general_no_tool cannot require private evidence")
                if category in {"private_single_fact", "private_multi_evidence", "private_no_answer"} and tool != TOOL:
                    errors.append(f"{prefix}: private category must search, including no-answer")
                if category == "private_single_fact" and len(refs) != 1:
                    errors.append(f"{prefix}: single fact needs one evidence chunk")
                if category == "private_multi_evidence" and len(refs) < 2:
                    errors.append(f"{prefix}: private multi needs at least two chunks")
                if category == "private_no_answer" and (refs or answerable is not False):
                    errors.append(f"{prefix}: private no-answer must lack evidence")
                if tool is None and refs:
                    errors.append(f"{prefix}: no-tool cannot require private evidence")
                if not item.get("routing_rationale"):
                    errors.append(f"{prefix}: missing routing rationale")
            if answerable is False and (suite == "retrieval" or item.get("expected_tool") == TOOL) and not item.get("no_answer_reason"):
                errors.append(f"{prefix}: missing no-answer reason")
        for category, counts in category_split.items():
            if not all(counts.values()):
                errors.append(f"{suite}: category {category} missing dev/test representative")
        stats[suite] = {"total": len(items), "split": dict(Counter(i.get("split") for i in items)),
                        "categories": category_split}
        manifest_key = "retrieval_ids" if suite == "retrieval" else "routing_ids"
        for split in ["dev", "test"]:
            expected = [i["id"] for i in items if i.get("split") == split and isinstance(i.get("id"), str)]
            declared = bundle["split"].get(manifest_key, {}).get(split, [])
            if sorted(expected) != sorted(declared):
                errors.append(f"{suite}: split manifest ID mismatch ({split})")
            locked = bundle["freeze"].get("frozen_test_ids", {}).get(suite, [])
            if split == "test" and sorted(expected) != sorted(locked):
                errors.append(f"{suite}: frozen test ID mismatch")
    threshold = bundle["config"].get("fuzzy_warning_threshold", 0.90)
    for idx, (suite_a, a, norm_a) in enumerate(all_records):
        for suite_b, b, norm_b in all_records[idx + 1:]:
            if norm_a == norm_b:
                continue  # exact duplicate 已报 error。
            similarity = SequenceMatcher(None, norm_a, norm_b, autojunk=False).ratio()
            if similarity >= threshold:
                warnings.append({"kind": "near_duplicate", "left": a["id"], "right": b["id"],
                                 "similarity": round(similarity, 6), "cross_split": a["split"] != b["split"],
                                 "same_family": a["family_id"] == b["family_id"]})
    if root is not None:
        errors.extend(verify_lock(root, bundle["freeze"]))
        # 实际重新提取和切块比对清单，而不是把手写 metadata 当真实切块结果。
        from knowledge_base_agent.vendor.rag_core.extractor import extract_documents
        from knowledge_base_agent.vendor.rag_core.chunker import chunk_fixed
        cfg = bundle["config"]
        corpus_dir = (Path(root) / cfg["corpus_dir"]).resolve()
        if not corpus_dir.is_relative_to(Path(root).resolve() / "eval/v0.2"):
            errors.append("corpus_dir must stay under isolated eval/v0.2")
        else:
            pages = extract_documents(str(corpus_dir))
            raw = chunk_fixed(pages, {"chunking": {"fixed": {"chunk_size": cfg["chunk_size"], "overlap": cfg["overlap"]}}})
            actual = [{"chunk_id": c["chunk_id"], "source": c["source_file"], "page": c["page"],
                       "chunk_index": c["chunk_index"], "text": c["text"]} for c in raw]
            if actual != chunks:
                errors.append("corpus chunks do not match frozen loader/chunker output")
            if {p.name for p in corpus_dir.glob("*.txt")} != set(sources):
                errors.append("corpus file list differs from manifest")
    return {"valid": not errors, "errors": errors, "warnings": warnings,
            "stats": {"documents": len(documents), "chunks": len(chunks), **stats},
            "hashes_checked": len(bundle["freeze"].get("files", {})) if root else 0}
