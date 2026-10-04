"""改编来源：https://github.com/tajwarchy/rag-from-scratch
原始文件：core/chunker.py:chunk_fixed(), _make_chunk()
commit：4c4e039177ce2a7ac475339cff7a1187a6fd68bf
MIT License，完整版权声明见 licenses/。
修改：保留 fixed 循环；验证参数；只保留 fixed；字符串 ID 和每页序号。
"""
import tiktoken
_TOKENIZER = tiktoken.get_encoding("cl100k_base")

def chunk_fixed(pages: list[dict], cfg: dict) -> list[dict]:
    """
    Split each page's text into fixed-size token windows with overlap.
    Uses tiktoken so chunk sizes are exact token counts, not character counts.

    Config keys used:
        chunking.fixed.chunk_size   (default 256)
        chunking.fixed.overlap      (default 32)
    """
    chunk_size = cfg["chunking"]["fixed"]["chunk_size"]
    overlap    = cfg["chunking"]["fixed"]["overlap"]

    if not isinstance(chunk_size, int) or isinstance(chunk_size, bool) or chunk_size <= 0:
        raise ValueError("chunk_size must be positive integer")
    if not isinstance(overlap, int) or isinstance(overlap, bool) or not 0 <= overlap < chunk_size:
        raise ValueError("Require 0 <= overlap < chunk_size")
    chunks = []
    chunk_id = 0

    for page in pages:
        chunk_id = 0  # 每个来源/页内的稳定序号
        tokens = _TOKENIZER.encode(page["text"])
        start = 0
        while start < len(tokens):
            end = start + chunk_size
            window_tokens = tokens[start:end]
            text = _TOKENIZER.decode(window_tokens).strip()
            if text:
                chunks.append(_make_chunk(chunk_id, page, text, "fixed"))
                chunk_id += 1
            start += chunk_size - overlap  # slide forward with overlap

    return chunks


def _make_chunk(chunk_id: int, page: dict, text: str, strategy: str) -> dict:
    return {
        "chunk_id": f"{page['source_file']}:p{page['page'] if page['page'] is not None else 'txt'}:{chunk_id:03d}",
        "chunk_index": chunk_id,
        "source_file": page["source_file"],
        "page":        page["page"],
        "text":        text,
        "strategy":    strategy,
    }
