import json
import fitz
import numpy as np
import pytest
from knowledge_base_agent.vendor.rag_core.extractor import extract_documents, extract_text_from_txt
from knowledge_base_agent.vendor.rag_core.chunker import chunk_fixed
from knowledge_base_agent.vendor.rag_core.faiss_store import FaissStore
from knowledge_base_agent.vendor.ollama_embeddings import normalize_vectors
from knowledge_base_agent.rag.retriever import Retriever
from knowledge_base_agent.rag.config import load_config


def pages():
    return [{"text": "budget 128000 year 2026 " * 12, "source_file": "folder/project.pdf", "page": 3}]


def chunks():
    return [{"text": "alpha", "source_file": "folder/a.pdf", "page": 3, "chunk_id": "folder/a.pdf:p3:000"},
            {"text": "beta", "source_file": "b.txt", "page": None, "chunk_id": "b.txt:ptxt:000"}]


def test_extraction(tmp_path):
    folder=tmp_path/"nested";folder.mkdir()
    doc=fitz.open();page=doc.new_page();page.insert_text((72,72), "Year 2026 Budget 128000 RB-204");doc.new_page();doc.save(folder/"test.pdf");doc.close()
    (folder/"note.txt").write_text("中文 2026\n预算 128000",encoding="utf-8")
    (folder/"empty.txt").write_text("   ",encoding="utf-8")
    records=extract_documents(str(tmp_path))
    assert len(records)==2
    pdf=next(p for p in records if p["page"] is not None)
    assert pdf["page"]==1 and pdf["source_file"]=="nested/test.pdf"
    assert "2026" in pdf["text"] and "128000" in pdf["text"] and "RB-204" in pdf["text"]
    assert extract_text_from_txt(str(folder/"note.txt"),str(tmp_path))[0]["text"]=="中文 2026\n预算 128000"


@pytest.mark.parametrize("size,overlap",[(0,0),(-1,0),(10,-1),(10,10),(10,11),(True,0),(10,False)])
def test_chunk_validation(size,overlap):
    with pytest.raises(ValueError):chunk_fixed(pages(),{"chunking":{"fixed":{"chunk_size":size,"overlap":overlap}}})


def test_chunk_ids():
    inputs=pages()+[{"text":"second page "*20,"source_file":"folder/project.pdf","page":4}]
    cfg={"chunking":{"fixed":{"chunk_size":16,"overlap":4}}}
    result=chunk_fixed(inputs,cfg)
    assert len(set(c["chunk_id"] for c in result))==len(result)
    assert result==chunk_fixed(inputs,cfg)
    assert all(c["source_file"]=="folder/project.pdf" for c in result)
    assert {c["page"] for c in result}=={3,4}
    assert chunk_fixed([],cfg)==[]


@pytest.mark.parametrize("values",[[[0,0]],[[float("nan"),1]],[[float("inf"),1]],[],[1,2]])
def test_bad_vectors(values):
    with pytest.raises(ValueError):normalize_vectors(values)


def test_normalization():
    vectors=normalize_vectors([[3,4],[5,12]])
    assert vectors.dtype==np.float32
    assert np.allclose(np.linalg.norm(vectors,axis=1),1)


def test_store_roundtrip(tmp_path):
    store=FaissStore(tmp_path/"中文路径","test-model")
    assert store.load_index() is False
    store.build_index(np.eye(2,dtype="float32"),chunks())
    other=FaissStore(store.store_dir,"test-model");assert other.load_index()
    hits=other.search(np.array([[1,0]],dtype="float32"),99)
    assert len(hits)==2 and hits[0]["chunk_id"]==chunks()[0]["chunk_id"]
    assert hits[0]["score"]>=hits[1]["score"] and hits[0]["page"]==3
    assert json.loads((store.store_dir/"metadata.json").read_text(encoding="utf-8"))==chunks()
    with pytest.raises(ValueError):other.search(np.ones((1,3),dtype="float32"),1)
    with pytest.raises(ValueError):other.search(np.array([[1,0]],dtype="float32"),0)
    with pytest.raises(ValueError):FaissStore(store.store_dir,"wrong-model").load_index()


@pytest.mark.parametrize("field,value",[("vector_dimension",99),("chunk_count",99),("normalized",False),("index_type","IndexFlatL2")])
def test_info_mismatch(tmp_path,field,value):
    store=FaissStore(tmp_path,"test-model");store.build_index(np.eye(2,dtype="float32"),chunks())
    path=tmp_path/"index_info.json";info=json.loads(path.read_text());info[field]=value;path.write_text(json.dumps(info))
    with pytest.raises(ValueError):FaissStore(tmp_path,"test-model").load_index()


def test_metadata_corruption(tmp_path):
    store=FaissStore(tmp_path,"test-model");store.build_index(np.eye(2,dtype="float32"),chunks())
    (tmp_path/"metadata.json").write_text("[]")
    with pytest.raises(ValueError):store.load_index()


def test_count_and_duplicate_validation(tmp_path):
    store=FaissStore(tmp_path,"test-model")
    with pytest.raises(ValueError):store.build_index(np.eye(2,dtype="float32"),chunks()[:1])
    with pytest.raises(ValueError):store.build_index(np.eye(2,dtype="float32"),[chunks()[0],chunks()[0]])
    with pytest.raises(RuntimeError):store.search(np.array([[1,0]],dtype="float32"),1)


@pytest.mark.parametrize("query,k",[("",3),("   ",3),(None,3),("ok",0),("ok",-1),("ok",True)])
def test_retriever_validation(query,k):
    with pytest.raises(ValueError):Retriever(None).search(query,k)


def test_config_relative_paths(tmp_path,monkeypatch):
    (tmp_path/"config.yaml").write_text("data_dir: data\nstore_dir: store\nembedding_model: nomic-embed-text\nbase_url: http://localhost:11434\nchunk_size: 160\noverlap: 24",encoding="utf-8")
    cfg=load_config(tmp_path/"config.yaml")
    assert cfg.data_dir==tmp_path/"data" and cfg.store_dir==tmp_path/"store"
