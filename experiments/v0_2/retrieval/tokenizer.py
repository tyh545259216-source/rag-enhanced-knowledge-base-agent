"""确定性离线分词，版本固定后不得按 test 题目添加例外。"""
import re
import unicodedata

VERSION = "nfkc-ascii-id-cjk12-v1"
# ASCII 连字符编号作为整体；中文连续段产生 unigram 与相邻 bigram。
PARTS = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*|[\u3400-\u4dbf\u4e00-\u9fff]+")

def tokenize(text: str) -> list[str]:
    if not isinstance(text, str):
        raise TypeError("text must be string")
    normalized = unicodedata.normalize("NFKC", text).casefold()
    tokens = []
    for match in PARTS.finditer(normalized):
        part = match.group()
        if part[0].isascii():
            tokens.append(part)
        else:
            tokens.extend(part)
            tokens.extend(part[i:i+2] for i in range(len(part)-1))
    return tokens
