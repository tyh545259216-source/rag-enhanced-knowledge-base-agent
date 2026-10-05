"""执行隔离消融阶段，不覆盖任何已有正式结果。"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.v0_2.ablation.runner import main
if __name__=='__main__':main()
