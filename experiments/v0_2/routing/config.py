"""通用候选与预注册选择规则；不读取test答案形成Prompt。"""
from copy import deepcopy
import hashlib,json
from pathlib import Path
TOOL = "search_knowledge_base"
BASE_DESCRIPTION = "Search the local internal knowledge base. Return evidence with sources and scores, not a final answer. Nearest neighbors may not answer the question."
BASE_INSTRUCTION = "你可以使用提供的工具完成用户任务。当回答依赖本地私有知识库的信息时，可以调用 search_knowledge_base 获取相关证据。如果工具结果不足以支持答案，请明确说明无法确定。"
DESCRIPTION_V1 = 'Search the local private knowledge base using natural-language questions; exact document or table names are not required. Use it for tasks that depend on private records, including checking whether requested information is documented. Returned passages are candidate evidence, not verified answers; state uncertainty when they do not support an answer.'
SELECTION_POLICY = {"max_additional_fp":1,"max_precision_drop":.05,
                    "priority":["recall","fewer_false_positives","shorter_prompt"],
                    "tie_preference":["A0","A1","A2"],
                    "scope":"dev only; A3 not planned"}
BASE_SETTINGS = {"model":"qwen3:1.7b","provider":"ollama","endpoint":"http://localhost:11434/v1/chat/completions",
                 "temperature":.1,"max_tokens":8192,"reasoning_effort":None,"context_window_tokens":200000,
                 "max_iterations":4,"case_timeout_seconds":300,"max_tool_result_chars":12000,
                 "finalize_on_max_iterations":False,"provider_retry_mode":"standard",
                 "formal_repeats":1,"few_shot":[]}
def canonical_hash(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")).hexdigest()
def baseline():
    return {**deepcopy(BASE_SETTINGS),"arm":"A0","tool_description":BASE_DESCRIPTION,"system_instruction":BASE_INSTRUCTION}
def validate_arm(arm):
    for key,value in BASE_SETTINGS.items():
        if arm.get(key)!=value:raise ValueError(f"generation/runtime setting changed: {key}")
    if arm.get("arm") not in {"A0","A1","A2"}:raise ValueError("unsupported arm")
    for key in ("tool_description","system_instruction"):
        if not isinstance(arm.get(key),str) or not arm[key].strip():raise ValueError(f"missing {key}")
    if arm["arm"]=="A0" and (arm["tool_description"]!=BASE_DESCRIPTION or arm["system_instruction"]!=BASE_INSTRUCTION):
        raise ValueError("A0 must preserve V0.1 text")
    if arm["arm"]=="A1" and arm["system_instruction"]!=BASE_INSTRUCTION:
        raise ValueError("A1 changes description only")
    return arm
def choose_arm(arms):
    """先筛FP/Precision，再按Recall、FP、文本长度选择；规则事前固定。"""
    base=arms["A0"]["metrics"]
    eligible=[]
    for name,data in arms.items():
        m=data["metrics"]
        if m["FP"]<=base["FP"]+SELECTION_POLICY["max_additional_fp"] and m["precision"]>=base["precision"]-SELECTION_POLICY["max_precision_drop"]:
            text=data["config"]["system_instruction"]+data["config"]["tool_description"]
            eligible.append((-m["recall"],m["FP"],len(text),SELECTION_POLICY["tie_preference"].index(name),name))
    return min(eligible)[-1]
def write_once(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    # x模式防止覆盖原正式文件。
    with path.open("x",encoding="utf-8",newline="\n") as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write("\n")
