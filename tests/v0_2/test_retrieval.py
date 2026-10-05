"""实验层单测。合成向量只用于存储/接口测试，不代表真实Embedding成功。"""
from dataclasses import asdict, replace
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pytest
from experiments.v0_2.datasets import load_bundle, verify_lock
from experiments.v0_2.retrieval.backends import DenseBackend, HybridBackend, isolated_store
from experiments.v0_2.retrieval.bm25 import BM25Backend
from experiments.v0_2.retrieval.metrics import distributions, query_metrics, summarize
from experiments.v0_2.retrieval.schema import RankedResult, reciprocal_rank_fusion
from experiments.v0_2.retrieval.tokenizer import tokenize
from experiments.v0_2.retrieval import runner
from knowledge_base_agent.rag.retriever import Retriever

ROOT = Path(__file__).resolve().parents[2]

def chunks():
    return [{"chunk_id": "a:ptxt:000", "text": "Aurora-X 项目负责人甲，编号 RB-204。",
             "source": "a.txt", "page": None, "chunk_index": 0},
            {"chunk_id": "b:p2:000", "text": "Aurora 项目预算 12000 元。",
             "source": "b.txt", "page": 2, "chunk_index": 0},
            {"chunk_id": "c:ptxt:000", "text": "机房日志保留 30 天。",
             "source": "c.txt", "page": None, "chunk_index": 0}]

def result(ident, rank=1, score=1):
    return RankedResult(ident, rank, score, ident+".txt", ident+" text", None, "bm25")

@pytest.mark.parametrize("text,expected", [
    ("ORBIT-3 RB-204 Aurora-X", ["orbit-3", "rb-204", "aurora-x"]),
    ("ＲＢ－２０４", ["rb-204"]),
    ("English WORDS 2028 12000", ["english","words","2028","12000"]),
    ("项目负责人", ["项","目","负","责","人","项目","目负","负责","责人"]),
    ("项目，负责人", ["项","目","项目","负","责","人","负责","责人"]),
    ("甲Aurora-X乙", ["甲","aurora-x","乙"]),
    ("", []), ("?!", []),
])
def test_tokenizer_contract(text, expected):
    assert tokenize(text) == expected
    assert tokenize(text) == tokenize(text)

def test_tokenizer_rejects_non_string():
    with pytest.raises(TypeError): tokenize(None)

@pytest.mark.parametrize("ident", ["ORBIT-3", "RX-41R2", "ARC-TF", "SV-18B"])
def test_identifiers_remain_whole(ident):
    assert tokenize(ident) == [ident.lower()]

def test_bm25_exact_entity_and_schema():
    results = BM25Backend(chunks()).search("Aurora-X RB-204", 3)
    assert results[0].chunk_id == "a:ptxt:000"
    assert [r.rank for r in results] == [1,2,3]
    assert all(set(asdict(r)) == {"chunk_id","rank","score","source","text","page","score_kind"} for r in results)
    assert results[0].score_kind == "bm25"
    assert results[1].page == 2

def test_bm25_chinese_query():
    assert BM25Backend(chunks()).search("预算", 1)[0].chunk_id == "b:p2:000"

def test_bm25_formula():
    docs = [dict(c, text=f"RB-{204+i}") for i,c in enumerate(chunks()[:2])]
    scores = BM25Backend(docs).search("RB-204", 2)
    assert scores[0].score == pytest.approx(math.log(2))
    assert scores[1].score == 0

def test_bm25_query_duplicate_does_not_inflate():
    model = BM25Backend(chunks())
    assert model.search("Aurora-X",3) == model.search("Aurora-X Aurora-X",3)

def test_bm25_zero_overlap_tie_and_clipping():
    docs = list(reversed(chunks()))
    got = BM25Backend(docs).search("totally-unknown", 100)
    assert [x.chunk_id for x in got] == sorted(c["chunk_id"] for c in docs)
    assert all(x.score == 0 for x in got)
    assert len(got) == len(docs)

@pytest.mark.parametrize("query,k", [("",3),("   ",3),(None,3),("q",0),("q",-1),("q",True),("q",1.5)])
def test_invalid_search(query,k):
    with pytest.raises(ValueError): BM25Backend(chunks()).search(query,k)

@pytest.mark.parametrize("k1,b", [(0,.75),(-1,.75),(math.nan,.75),(1.5,-.1),(1.5,1.1)])
def test_bm25_invalid_params(k1,b):
    with pytest.raises(ValueError): BM25Backend(chunks(),k1,b)

def test_bm25_rejects_duplicate_chunks():
    with pytest.raises(ValueError): BM25Backend([chunks()[0],chunks()[0]])

def test_bm25_rejects_tokenless_corpus():
    with pytest.raises(ValueError): BM25Backend([dict(chunks()[0],text="!!!")])

def test_rrf_single_list():
    got = reciprocal_rank_fusion([[result("a"),result("b",2)]])
    assert [(r.chunk_id,r.rank) for r in got] == [("a",1),("b",2)]
    assert got[0].score == pytest.approx(1/61)

def test_rrf_shared_and_one_sided_hit():
    got = reciprocal_rank_fusion([[result("a"),result("b",2)], [result("b"),result("c",2)]])
    assert [r.chunk_id for r in got] == ["b","a","c"]
    assert got[0].score == pytest.approx(1/62+1/61)
    assert got[-1].score == pytest.approx(1/62)
    assert all(r.score_kind=="rrf" for r in got)

def test_rrf_tie_deterministic():
    for lists in ([[result("b")],[result("a")]],[[result("a")],[result("b")]]):
        assert [r.chunk_id for r in reciprocal_rank_fusion(lists)] == ["a","b"]

def test_rrf_ignores_incomparable_score_scales():
    original = [[result("a",1,.9)],[result("b",1,100)]]
    scaled = [[result("a",1,-.9)],[result("b",1,100000)]]
    assert reciprocal_rank_fusion(original) == reciprocal_rank_fusion(scaled)

@pytest.mark.parametrize("k",[0,-1,True])
def test_rrf_invalid_k(k):
    with pytest.raises(ValueError): reciprocal_rank_fusion([],k)

def test_rrf_duplicate_rank_invalid():
    with pytest.raises(ValueError): reciprocal_rank_fusion([[result("a"),result("a",2)]])
    with pytest.raises(ValueError): reciprocal_rank_fusion([[result("a",2)]])

def test_rrf_metadata_conflict():
    with pytest.raises(ValueError):
        reciprocal_rank_fusion([[result("a")],[replace(result("a"),text="changed")]])

class StubBackend:
    """仅测试融合接口，不用于真实评测。"""
    def __init__(self,results): self.results=results; self.last_latency={}
    def search(self,query,top_k):
        self.requested=(query,top_k)
        self.last_latency={"embedding_ms":1}
        return self.results[:top_k]

def test_hybrid_uses_fixed_candidate_pool():
    dense=StubBackend([result("a"),result("b",2)])
    bm=StubBackend([result("b"),result("a",2)])
    model=HybridBackend(dense,bm,20,60)
    got=model.search("test",1)
    assert dense.requested==bm.requested==("test",20)
    assert got[0].rank==1 and got[0].score_kind=="rrf"
    assert model.last_latency["hybrid_ms"]>=0
    with pytest.raises(ValueError): model.search("test",21)

def test_hybrid_invalid_query():
    with pytest.raises(ValueError): HybridBackend(StubBackend([]),StubBackend([])).search("",3)

def test_metrics_multi_evidence_and_cutoffs():
    got=query_metrics(["wrong","a","b"],["a","b"])
    assert got["HitRate@1"]==0 and got["Recall@3"]==1
    assert got["MRR@3"]==.5 and got["MRR@5"]==.5
    assert query_metrics(["a","a"],["a","b"])["Recall@3"]==.5

def test_no_answer_exclusion():
    assert query_metrics(["wrong"],[]) is None
    records=[{"answerable":False,"metrics":None},
             {"answerable":True,"metrics":query_metrics(["a"],["a"])}]
    out=summarize(records)
    assert out["answerable_count"]==1 and out["no_answer_count"]==1
    assert out["metrics"]["HitRate@1"]==1
    assert summarize(records[:1])["metrics"] is None

def test_latency_linear_p95():
    assert distributions([1,2,3,4])["median"]==2.5
    assert distributions([1,2,3,4])["p95"]==pytest.approx(3.85)
    assert distributions([]) is None

def test_v02_store_isolation(tmp_path):
    root=tmp_path
    path=root/"artifacts/v0.2/retrieval/unit/index"
    assert isolated_store(root,path)==path.resolve()
    with pytest.raises(ValueError): isolated_store(root,root/"store")
    with pytest.raises(ValueError): isolated_store(root,root/"artifacts/v0.2/retrieval/../outside")

def test_dense_reuses_original_retriever_and_faiss_reload(tmp_path,monkeypatch):
    cfg=load_bundle(ROOT)["config"]
    dense=DenseBackend(tmp_path,tmp_path/"artifacts/v0.2/retrieval/unit/index",runner.SETTINGS,cfg)
    assert isinstance(dense.retriever,Retriever)
    docs=chunks()[:2]
    raw=[dict(c,source_file=c["source"]) for c in docs]
    dense.adapter.store.build_index(np.eye(2,dtype="float32"),raw)
    assert dense.load()["ntotal"]==2
    monkeypatch.setattr("knowledge_base_agent.rag.adapter.embed_query",lambda *args,**kw: np.array([[0,1]],dtype="float32"))
    got=dense.search("unit-only",2)
    assert got[0].chunk_id=="b:p2:000" and got[0].page==2
    assert got[0].score_kind=="cosine_inner_product"
    assert not (tmp_path/"store").exists()

def test_frozen_dataset_hashes():
    bundle=load_bundle(ROOT)
    assert len(bundle["freeze"]["files"])==45
    assert verify_lock(ROOT,bundle["freeze"])==[]
    assert hashlib.sha256((ROOT/"eval/v0.2/freeze_manifest.json").read_bytes()).hexdigest()==(
        "078b30d94d2c4664a30aece15b3c255c9351345edc40a02dca15213b9fae9d18")

def test_write_json_refuses_overwrite(tmp_path):
    path=tmp_path/"test.json"
    runner.write_json(path,{"a":1})
    with pytest.raises(FileExistsError): runner.write_json(path,{"a":2})
    assert json.loads(path.read_text())=={"a":1}

def test_bad_case_candidate_labels():
    fake={}
    for method,ids in [("dense",["x","y","a"]),("bm25",["a","b","x"]),("hybrid",["x","y","a"])]:
        rows=[{"id":"unit","query":"q","category":"multi_evidence","answerable":True,
               "expected_chunk_ids":["a","b"],"results":[asdict(result(i,r)) for r,i in enumerate(ids,1)],
               "metrics":query_metrics(ids,["a","b"])}]
        fake[method]={"queries":rows}
    groups=runner.bad_cases(fake)
    assert len(groups["A_bm25_correct_dense_wrong"])==1
    assert len(groups["D_hybrid_worse_than_best_single"])==1
    assert len(groups["E_multi_evidence_coverage_failure"])==1
    assert groups["C_hybrid_correct_both_wrong"]==[]

def test_config_repeats_and_candidate_pool():
    assert runner.SETTINGS["test_latency_repeats"]>=3
    assert runner.SETTINGS["candidate_pool_size"]>=max(runner.SETTINGS["top_k_settings"])
    assert runner.SETTINGS["query_embedding_cache"] is False
