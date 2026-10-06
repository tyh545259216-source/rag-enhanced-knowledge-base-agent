"""从项目根目录运行，所有结果派生自首次Phase2，不重新检索。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from experiments.v0_2.no_answer.runner import main
if __name__ == "__main__":
    main()
