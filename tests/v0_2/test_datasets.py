"""新增数据契约测试；不触发模型调用，不改变历史黄金标签。"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
from experiments.v0_2.datasets import load_bundle, normalize_query, validate_bundle, verify_lock

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def bundle():
    return deepcopy(load_bundle(ROOT))


def assert_invalid(bundle, reason):
    result = validate_bundle(bundle)
    assert not result["valid"]
    assert any(reason in error for error in result["errors"]), result["errors"]


def test_real_bundle_and_actual_chunks(bundle):
    result = validate_bundle(bundle, ROOT)
    assert result["valid"], result["errors"]
    assert result["stats"]["documents"] == result["stats"]["chunks"] == 40
    assert result["stats"]["retrieval"]["split"] == {"dev": 36, "test": 24}
    assert result["stats"]["routing"]["split"] == {"dev": 30, "test": 20}
    assert result["hashes_checked"] == 45


@pytest.mark.parametrize("field,value,reason", [
    ("id", None, "id must"), ("id", "", "id must"),
    ("query", None, "query must"), ("query", "   ", "query must"),
    ("query", "？？！", "empty after normalization"),
    ("category", "invented_category", "illegal category"),
    ("split", "train", "illegal split"),
    ("answerable", 1, "answerable must"),
    ("expected_chunk_ids", None, "must be string list"),
    ("notes", "", "missing notes"), ("expected_answer", None, "missing expected_answer"),
])
def test_schema_rejects_invalid_fields(bundle, field, value, reason):
    bundle["retrieval"]["items"][0][field] = value
    assert_invalid(bundle, reason)


def test_global_ids_cannot_repeat(bundle):
    bundle["routing"]["items"][0]["id"] = bundle["retrieval"]["items"][0]["id"]
    assert_invalid(bundle, "duplicate ID")


def test_query_cannot_repeat_across_split_and_suite(bundle):
    original = bundle["retrieval"]["items"][0]
    target = next(x for x in bundle["routing"]["items"] if x["split"] != original["split"])
    target["query"] = original["query"] + " ！"
    assert_invalid(bundle, "duplicate normalized query")


def test_normalization_handles_unicode_without_erasing_entities():
    assert normalize_query(" ＡＵＲＯＲＡ－Ｘ？ ") == normalize_query("aurora-x")
    assert normalize_query("RX-41R2") != normalize_query("RX-41R3")
    assert normalize_query("12000元") != normalize_query("75000元")


@pytest.mark.parametrize("refs,reason", [
    (["missing.txt:ptxt:000"], "unknown referenced chunk"),
    (["aurora_finance.txt:ptxt:000"] * 2, "duplicate evidence"),
    ([], "answerable/evidence mismatch"),
])
def test_evidence_integrity(bundle, refs, reason):
    bundle["retrieval"]["items"][0]["expected_chunk_ids"] = refs
    assert_invalid(bundle, reason)


def test_no_answer_cannot_have_evidence(bundle):
    item = next(x for x in bundle["retrieval"]["items"] if x["category"] == "no_answer")
    item["expected_chunk_ids"] = [bundle["corpus"]["chunks"][0]["chunk_id"]]
    assert_invalid(bundle, "answerable/evidence mismatch")


def test_corpus_chunk_ids_unique(bundle):
    bundle["corpus"]["chunks"][1]["chunk_id"] = bundle["corpus"]["chunks"][0]["chunk_id"]
    assert_invalid(bundle, "duplicate corpus chunk_id")


def test_document_sources_unique(bundle):
    bundle["corpus"]["documents"][1]["source"] = bundle["corpus"]["documents"][0]["source"]
    assert_invalid(bundle, "duplicate corpus document source")


def test_family_may_not_cross_split(bundle):
    item = bundle["retrieval"]["items"][0]
    item["split"] = "dev" if item["split"] == "test" else "test"
    assert_invalid(bundle, "family crosses dev/test")


def test_split_manifest_requires_all_ids(bundle):
    bundle["split"]["retrieval_ids"]["dev"].pop()
    assert_invalid(bundle, "split manifest ID mismatch")


def test_test_lock_requires_exact_ids(bundle):
    bundle["freeze"]["frozen_test_ids"]["routing"].pop()
    assert_invalid(bundle, "frozen test ID mismatch")


@pytest.mark.parametrize("suite,category", [
    ("retrieval", "multi_evidence"), ("routing", "private_multi_evidence"),
])
def test_multi_evidence_needs_multiple_independent_chunks(bundle, suite, category):
    item = next(x for x in bundle[suite]["items"] if x["category"] == category)
    item["expected_chunk_ids"] = item["expected_chunk_ids"][:1]
    assert_invalid(bundle, "at least two chunks")


@pytest.mark.parametrize("category", ["private_single_fact", "private_multi_evidence", "private_no_answer"])
def test_private_cases_including_no_answer_require_search(bundle, category):
    item = next(x for x in bundle["routing"]["items"] if x["category"] == category)
    item["expected_tool"] = None
    assert_invalid(bundle, "private category must search")


def test_general_task_cannot_require_tool(bundle):
    bundle["routing"]["items"][0]["expected_tool"] = "search_knowledge_base"
    assert_invalid(bundle, "general_no_tool cannot")


def test_unknown_tool_not_allowed(bundle):
    bundle["routing"]["items"][0]["expected_tool"] = "exec"
    assert_invalid(bundle, "illegal/missing expected_tool")


def test_hard_negative_cannot_also_be_positive(bundle):
    item = bundle["retrieval"]["items"][0]
    item["hard_negative_chunk_ids"] = item["expected_chunk_ids"][:]
    assert_invalid(bundle, "positive hard negative")


def test_no_answer_has_explicit_reason(bundle):
    item = next(x for x in bundle["routing"]["items"] if x["category"] == "private_no_answer")
    item.pop("no_answer_reason")
    assert_invalid(bundle, "missing no-answer reason")


def test_version_mismatch_rejected(bundle):
    bundle["routing"]["version"] = "other"
    assert_invalid(bundle, "dataset version mismatch")


def test_fuzzy_duplicate_warns_without_deleting(bundle):
    a, b = bundle["retrieval"]["items"][:2]
    b["query"] = a["query"] + "请说明"
    before = len(bundle["retrieval"]["items"])
    result = validate_bundle(bundle)
    assert result["valid"], result["errors"]
    assert any({w["left"], w["right"]} == {a["id"], b["id"]} for w in result["warnings"])
    assert len(bundle["retrieval"]["items"]) == before


def test_hash_tampering_and_missing_files_detected(tmp_path):
    target = tmp_path / "eval/v0.2/check.json"
    target.parent.mkdir(parents=True)
    target.write_text("original")
    lock = {"files": {"eval/v0.2/check.json": hashlib.sha256(target.read_bytes()).hexdigest()}}
    assert verify_lock(tmp_path, lock) == []
    target.write_text("modified")
    assert "hash mismatch" in verify_lock(tmp_path, lock)[0]
    target.unlink()
    assert "missing frozen file" in verify_lock(tmp_path, lock)[0]


def test_lock_cannot_read_outside_isolated_dataset(tmp_path):
    assert "unsafe frozen path" in verify_lock(tmp_path, {"files": {"../private.json": "x"}})[0]


def test_manifest_cannot_fake_chunk_text(bundle):
    bundle["corpus"]["chunks"][0]["text"] += "invented"
    result = validate_bundle(bundle, ROOT)
    assert not result["valid"]
    assert "corpus chunks do not match frozen loader/chunker output" in result["errors"]


def test_validation_never_calls_http(bundle, monkeypatch):
    import httpx
    def blocked(*args, **kwargs):
        raise AssertionError("Dataset validation must not call model endpoints")
    monkeypatch.setattr(httpx.Client, "send", blocked)
    assert validate_bundle(bundle, ROOT)["valid"]


def test_cli_raw_json_markdown_and_no_overwrite(tmp_path):
    shutil.copytree(ROOT / "eval/v0.2", tmp_path / "eval/v0.2")
    output = tmp_path / "artifacts/v0_2/check"
    cmd = [sys.executable, "-X", "utf8", str(ROOT / "scripts/v0_2/validate_datasets.py"),
           "--root", str(tmp_path), "--output", str(output)]
    first = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    assert first.returncode == 0, first.stderr
    record = json.loads((output / "validation.json").read_text(encoding="utf-8"))
    assert record["valid"] and record["config"]["seed"] == 42
    report = output / "REPORT.md"
    assert "不是 Retrieval/Agent benchmark" in report.read_text(encoding="utf-8")
    snapshot = report.read_bytes()
    second = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    assert second.returncode != 0 and report.read_bytes() == snapshot
