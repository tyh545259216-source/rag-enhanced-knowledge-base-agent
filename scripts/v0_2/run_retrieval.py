"""从仓库任意位置调用独立检索实验，不依赖安装experiments包。"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from experiments.v0_2.retrieval.runner import main

if __name__ == "__main__":
    main()
