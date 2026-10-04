"""仅恢复中断后的未保存题目；不重测已有结果，不改变原始实验脚本。"""
from pathlib import Path
source_path=Path(__file__).with_name("run_routing.py")
source=source_path.read_text(encoding="utf-8")
source=source.replace('before=frozen();', 'before=json.loads((OUT/"frozen_before.json").read_text(encoding="utf-8"));assert before==frozen();')
start=source.index('    report={"timestamp":')
end=source.index('    for item in dataset["items"]:',start)
source=source[:start]+'''    report=json.loads((OUT/"trace.json").read_text(encoding="utf-8"))
    completed={case["id"] for case in report["cases"]}
    report["execution_interruption"]="Execution host lost process after r15 checkpoint; resume only unsaved cases."
'''+source[end:]
source=source.replace('    for item in dataset["items"]:', '    for item in dataset["items"]:\n        if item["id"] in completed:continue')
exec(compile(source,str(source_path),"exec"),{"__name__":"__main__","__file__":str(source_path)})
