"""独立 Phase 1 校验入口：只读数据，输出新 JSON/Markdown，不执行 Agent。"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))  # 仅定位新增实验包，不覆盖已安装的 RAG/nanobot 路径。
from experiments.v0_2.datasets import load_bundle, validate_bundle


def markdown(result, bundle):
    stats = result["stats"]
    lines = ["# V0.2 Evaluation Dataset — Phase 1", "",
             "本报告来自数据校验，不是 Retrieval/Agent benchmark。未测量 V0.2 效果指标。", "",
             "## Corpus 与隔离", "",
             f"- 文档 {stats['documents']}，实际 chunk {stats['chunks']}，全部 UTF-8 TXT、page=null。",
             "- corpus 位于 eval/v0.2/corpus/；V0.1 默认 data/ 递归扫描不会读到它。",
             "- 40 份不同虚构事实文档，10 个主题组；没有切碎或改写旧 9 个历史块来凑数。",
             "- 复用 frozen loader/chunker，chunk_size=160、overlap=24、cl100k_base 仅计量；没有 Embedding 或新 FAISS index。",
             "- 角色/项目/政策/设备数据均为虚构，2028 年排期是场景设定，不是现实事实。", "",
             "## Dataset 与 split", ""]
    for suite in ["retrieval", "routing"]:
        info = stats[suite]
        lines += [f"### {suite}", "", f"总数 {info['total']}；dev={info['split'].get('dev', 0)}，test={info['split'].get('test', 0)}。", ""]
        for category, counts in info["categories"].items():
            lines.append(f"- {category}: dev {counts['dev']} / test {counts['test']} / total {sum(counts.values())}")
        lines.append("")
    lines += ["固定 seed=42；按 family_id 分组，两套数据共用 6 个 dev 主题组、4 个 test 主题组，均为 60%/40%。",
              "同一主题的改写/证据题不跨 split；test 在任何正式模型实验前由 freeze_manifest.json 锁定。",
              "dev 可用于后续已授权的优化；不能根据 test 改 Prompt、答案、标签或删样本。",
              "不同主题仍共享人工模板与任务类型，不能把主题分组当作完全无泄漏或生产泛化保证。", "",
              "## 难度与标注", "",
              "- 相似实体：Aurora/Aurora-X、Borealis/Borealis-2、RX-41R2/R3、SABLE-18/18B、ORBIT-3/3A。",
              "- 相似角色：项目、验收、审批、维护、归档分别归不同虚构角色；示例采购审批 P-22 与归档 P-44。",
              "- 精确词：FIN-A12/FIN-AX12、BT-7/BT-7B、PC-21/21C、LOG-31/31T/32，数字与后缀必须保留。",
              "- hard negatives 标注在 hard_negative_chunk_ids；表面相似但事实类型或实体不同。没有模型排名证据，不能声称已证明它们对模型很难。",
              "- multi-evidence 涉及 2–3 份文档，expected_chunk_ids 包含全部不可替代的必要事实；未来不能只算任一命中就算完整回答。",
              "- no-answer 的 expected_chunk_ids=[]；如 ORBIT-3A 有 26 人，但 ORBIT-3 缺少人数，禁止沿用相似实体的数字。",
              "- routing boundary 同时有明确私有依据、仅文字处理、仅通用解释、虚构文案，以及按内部资料询问缺失事实。",
              "- private_no_answer 仍 expected_tool=search_knowledge_base；检索后证据不足才可拒答。",
              "- routing 的 answerable 仅表示 corpus 能否提供私有证据；general_no_tool=false 不代表普通问题无法回答。",
              "- expected_answer/notes/routing_rationale 是人工 golden 标注，不是模型产生的成功答案。", "",
              "## 自动校验结果", "",
              f"valid={result['valid']}；errors={len(result['errors'])}；near-duplicate warnings={len(result['warnings'])}；数据 hash 校验 {result['hashes_checked']} 个文件。",
              "验证唯一 ID/query/chunk、类型、类别、证据、answerable、一致 split、group 隔离、manifest、锁定哈希，以及真实重新切块。",
              "NFKC+casefold 后移除空格/标点，保留数字；exact/normalized 重复为 error。SequenceMatcher>=0.90 仅 warning，不自动删题，也不是语义重复保证。", ""]
    if result["warnings"]:
        lines += ["### 近似重复审阅", "", "以下候选原样保留；人工复核实体/属性不同与跨 split 风险，不能按警告自动删除。", ""]
        for w in result["warnings"]:
            lines.append(f"- {w['left']} / {w['right']}：ratio={w['similarity']}，cross_split={w['cross_split']}，same_family={w['same_family']}。")
    for error in result["errors"]:
        lines.append("- ERROR: " + error)
    lines += ["", "## 复跑", "", "```powershell", "& ../nanobot/.venv/Scripts/python.exe scripts/v0_2/validate_datasets.py", "```", "",
              "新 JSON/Markdown 存入 ignored artifacts/v0_2/dataset_validation/<UTC-run-id>/；既有目录拒绝覆盖。",
              "公开本报告用 --report docs/v0.2/DATASET_REPORT.md 显式更新；不编辑历史 evidence。", "",
              "## 限制与人工偏差", "",
              "人工知道语料后撰题与标注，存在设计偏差；单一作者，没有盲测外部标注者或真实用户分布。",
              "各主题短文结构清晰，40 个块远小于真实库；仅 TXT，无 OCR/表格/PDF 跨页，难度设计不能代替实测。",
              "一些问题显式提及内部资料以界定路由；含强提示，后续应分层报告，不能称完全自然用户任务。",
              "自动校验只能证明结构、锁定版本及字面重复规则，不能证明人工答案语义无误或 no-answer 的穷尽性。",
              "已有测试数据与新 V0.2 不能混算效果提升；本 Phase 没有优化 Prompt/Tool、BM25、Hybrid 或模型。", "",
              "## 测试口径", "", "测试结果在完成真实执行后写入本节；校验通过不等于所有回归已通过。", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, help="新目录，已存在则拒绝覆盖")
    parser.add_argument("--report", type=Path, help="可选公开当前 Phase 1 报告；只允许 docs/v0.2 内")
    args = parser.parse_args()
    root = args.root.resolve()
    bundle = load_bundle(root)
    result = validate_bundle(bundle, root)
    result["config"] = bundle["config"]
    result["freeze_manifest_sha256"] = hashlib.sha256((root / "eval/v0.2/freeze_manifest.json").read_bytes()).hexdigest()
    output = args.output or root / "artifacts/v0_2/dataset_validation" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = output.resolve()
    if not output.is_relative_to(root / "artifacts/v0_2"):
        parser.error("--output must stay under artifacts/v0_2")
    if args.report and not args.report.resolve().is_relative_to(root / "docs/v0.2"):
        parser.error("--report must stay under docs/v0.2")
    if output.exists():
        parser.error("output directory already exists; refusing overwrite")
    output.mkdir(parents=True, exist_ok=False)
    content = markdown(result, bundle)
    (output / "validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "REPORT.md").write_text(content, encoding="utf-8")
    if args.report:
        args.report.resolve().parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(content, encoding="utf-8")
    print(json.dumps({"valid": result["valid"], "errors": result["errors"], "warnings": len(result["warnings"]),
                      "stats": result["stats"], "output": str(output)}, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
