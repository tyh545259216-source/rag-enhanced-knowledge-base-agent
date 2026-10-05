"""真实AgentRunner Routing A/B，输出独立ignored artifacts。"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from experiments.v0_2.routing.runner import main
if __name__=="__main__":main()
