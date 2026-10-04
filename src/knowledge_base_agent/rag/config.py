from dataclasses import dataclass
from pathlib import Path
import yaml

@dataclass(frozen=True)
class RAGConfig:
    data_dir: Path
    store_dir: Path
    embedding_model: str
    base_url: str
    chunk_size: int
    overlap: int
    timeout: float = 120

def load_config(path: str | Path) -> RAGConfig:
    file = Path(path).resolve()
    cfg = yaml.safe_load(file.read_text(encoding="utf-8"))
    return RAGConfig((file.parent / cfg["data_dir"]).resolve(), (file.parent / cfg["store_dir"]).resolve(),
                     cfg["embedding_model"], cfg["base_url"], cfg["chunk_size"], cfg["overlap"], cfg.get("timeout",120))
