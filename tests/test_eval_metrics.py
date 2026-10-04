import importlib.util
from pathlib import Path
import pytest
p=Path(__file__).resolve().parents[1]/"eval/baseline.py"
spec=importlib.util.spec_from_file_location("baseline",p);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

def test_partial_recall():
    assert mod.metrics(["wrong","a","b"],["a","b","c"],3)=={"hit_rate":1.,"recall":2/3,"mrr":.5}

def test_no_hit():
    assert mod.metrics(["x"],["a"],1)=={"hit_rate":0.,"recall":0.,"mrr":0.}

def test_no_answer_excluded():
    assert mod.metrics(["x"],[],3) is None

def test_duplicate_not_double_counted():
    assert mod.metrics(["a","a"],["a","b"],3)["recall"]==.5

def test_k_truncation():
    assert mod.metrics(["x","a"],["a"],1)["hit_rate"]==0

def test_quantile():
    assert mod.distribution([1,2,3,4])["p50"]==2.5
