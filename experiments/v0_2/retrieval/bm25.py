"""轻量 Okapi BM25，无分词词典或第三方搜索依赖。"""
from collections import Counter
import math
from time import perf_counter
from .schema import RankedResult, validate_chunks, validate_search
from .tokenizer import tokenize

class BM25Backend:
    def __init__(self, chunks, k1=1.5, b=0.75):
        validate_chunks(chunks)
        if not math.isfinite(k1) or k1 <= 0 or not math.isfinite(b) or not 0 <= b <= 1:
            raise ValueError("BM25 requires k1 > 0 and 0 <= b <= 1")
        self.chunks = chunks
        self.k1, self.b = k1, b
        self.terms = [Counter(tokenize(c["text"])) for c in chunks]
        self.lengths = [sum(t.values()) for t in self.terms]
        self.avgdl = sum(self.lengths)/len(chunks)
        if self.avgdl == 0:
            raise ValueError("corpus has no indexable tokens")
        self.df = Counter(term for doc in self.terms for term in doc)
        self.last_latency = {}

    def search(self, query, top_k=3):
        validate_search(query, top_k)
        start = perf_counter()
        # 一次计入每个不同 query term，不另加 query term frequency 项。
        query_terms = set(tokenize(query))
        scored = []
        n = len(self.chunks)
        for chunk, terms, dl in zip(self.chunks, self.terms, self.lengths):
            score = 0.0
            for term in sorted(query_terms):  # 固定浮点累加顺序。
                tf = terms.get(term, 0)
                if tf:
                    df = self.df[term]
                    idf = math.log(1 + (n-df+0.5)/(df+0.5))
                    norm = tf + self.k1*(1-self.b+self.b*dl/self.avgdl)
                    score += idf*tf*(self.k1+1)/norm
            scored.append((score, chunk))
        scored.sort(key=lambda item: (-item[0], item[1]["chunk_id"]))
        results = [RankedResult(c["chunk_id"], rank, float(score), c["source"],
                                c["text"], c.get("page"), "bm25")
                   for rank, (score, c) in enumerate(scored[:top_k], 1)]
        self.last_latency = {"bm25_ms": (perf_counter()-start)*1000}
        return results
