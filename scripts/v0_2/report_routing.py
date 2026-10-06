"""从真实trace与工程人工审阅生成不覆盖的JSON/Markdown报告。"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.v0_2.routing.reporting import main
if __name__=='__main__':main()
