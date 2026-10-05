# V0.2 Evaluation Dataset — Phase 1

本报告来自数据校验，不是 Retrieval/Agent benchmark。未测量 V0.2 效果指标。

## Corpus 与隔离

- 文档 40，实际 chunk 40，全部 UTF-8 TXT、page=null。
- corpus 位于 eval/v0.2/corpus/；V0.1 默认 data/ 递归扫描不会读到它。
- 40 份不同虚构事实文档，10 个主题组；没有切碎或改写旧 9 个历史块来凑数。
- 复用 frozen loader/chunker，chunk_size=160、overlap=24、cl100k_base 仅计量；没有 Embedding 或新 FAISS index。
- 角色/项目/政策/设备数据均为虚构，2028 年排期是场景设定，不是现实事实。

## Dataset 与 split

### retrieval

总数 60；dev=36，test=24。

- entity_ambiguity: dev 6 / test 4 / total 10
- exact_keyword: dev 6 / test 4 / total 10
- hard_negative: dev 6 / test 4 / total 10
- multi_evidence: dev 6 / test 4 / total 10
- no_answer: dev 6 / test 4 / total 10
- semantic_paraphrase: dev 6 / test 4 / total 10

### routing

总数 50；dev=30，test=20。

- ambiguous_boundary: dev 6 / test 4 / total 10
- general_no_tool: dev 6 / test 4 / total 10
- private_multi_evidence: dev 6 / test 4 / total 10
- private_no_answer: dev 6 / test 4 / total 10
- private_single_fact: dev 6 / test 4 / total 10

固定 seed=42；按 family_id 分组，两套数据共用 6 个 dev 主题组、4 个 test 主题组，均为 60%/40%。
同一主题的改写/证据题不跨 split；test 在任何正式模型实验前由 freeze_manifest.json 锁定。
dev 可用于后续已授权的优化；不能根据 test 改 Prompt、答案、标签或删样本。
不同主题仍共享人工模板与任务类型，不能把主题分组当作完全无泄漏或生产泛化保证。

## 难度与标注

- 相似实体：Aurora/Aurora-X、Borealis/Borealis-2、RX-41R2/R3、SABLE-18/18B、ORBIT-3/3A。
- 相似角色：项目、验收、审批、维护、归档分别归不同虚构角色；示例采购审批 P-22 与归档 P-44。
- 精确词：FIN-A12/FIN-AX12、BT-7/BT-7B、PC-21/21C、LOG-31/31T/32，数字与后缀必须保留。
- hard negatives 标注在 hard_negative_chunk_ids；表面相似但事实类型或实体不同。没有模型排名证据，不能声称已证明它们对模型很难。
- multi-evidence 涉及 2–3 份文档，expected_chunk_ids 包含全部不可替代的必要事实；未来不能只算任一命中就算完整回答。
- no-answer 的 expected_chunk_ids=[]；如 ORBIT-3A 有 26 人，但 ORBIT-3 缺少人数，禁止沿用相似实体的数字。
- routing boundary 同时有明确私有依据、仅文字处理、仅通用解释、虚构文案，以及按内部资料询问缺失事实。
- private_no_answer 仍 expected_tool=search_knowledge_base；检索后证据不足才可拒答。
- routing 的 answerable 仅表示 corpus 能否提供私有证据；general_no_tool=false 不代表普通问题无法回答。
- expected_answer/notes/routing_rationale 是人工 golden 标注，不是模型产生的成功答案。

## 自动校验结果

valid=True；errors=0；near-duplicate warnings=0；数据 hash 校验 45 个文件。
验证唯一 ID/query/chunk、类型、类别、证据、answerable、一致 split、group 隔离、manifest、锁定哈希，以及真实重新切块。
NFKC+casefold 后移除空格/标点，保留数字；exact/normalized 重复为 error。SequenceMatcher>=0.90 仅 warning，不自动删题，也不是语义重复保证。


## 复跑

```powershell
& ../nanobot/.venv/Scripts/python.exe scripts/v0_2/validate_datasets.py
```

新 JSON/Markdown 存入 ignored artifacts/v0_2/dataset_validation/<UTC-run-id>/；既有目录拒绝覆盖。
公开本报告用 --report docs/v0.2/DATASET_REPORT.md 显式更新；不编辑历史 evidence。

## 限制与人工偏差

人工知道语料后撰题与标注，存在设计偏差；单一作者，没有盲测外部标注者或真实用户分布。
各主题短文结构清晰，40 个块远小于真实库；仅 TXT，无 OCR/表格/PDF 跨页，难度设计不能代替实测。
一些问题显式提及内部资料以界定路由；含强提示，后续应分层报告，不能称完全自然用户任务。
自动校验只能证明结构、锁定版本及字面重复规则，不能证明人工答案语义无误或 no-answer 的穷尽性。
已有测试数据与新 V0.2 不能混算效果提升；本 Phase 没有优化 Prompt/Tool、BM25、Hybrid 或模型。

## 测试口径与真实结果

### V0.1 “51 项”来源核对

- 37 项来自 `tests/test_core.py`、`test_integration.py`、`test_eval_metrics.py` 的原 pytest collection。
- 11 项来自 `scripts/verify_plugin.py` 的 PluginTests，含真实 direct Tool call。
- 3 项来自 `docs/evidence/phase3b/test_metrics.py` 的 `test_confusion`、`test_empty`、`test_distribution`。
- 忽略目录 `phase3b/test_metrics.py` 与公开 evidence 副本字节相同；两个副本只能计一次，不能算 6 项。
- 这 3 项调用 phase3b 的 routing_metrics/distribution，与原 pytest 中的 retrieval metrics checks 不同，不是重复计数。
- `python docs/evidence/phase3b/test_metrics.py -v` 实际可执行，3 项通过；未运行 evaluate.py 的 main，未覆盖旧 evaluation.json。

### Phase 1 最终回归

- 原 pytest 37 +新增 dataset validation 40 = **77 passed**，12.05 秒，0 failure/error/skip。
- plugin verification **11 passed**；entry point/schema/原 baseline direct call 均通过。
- 独立 routing metric checks **3 passed**。
- 本轮独立检查总数 **91 =37+40+11+3**。重复执行与临时 clean-export 复跑不重复增加这个数。
- 新增 40 项测试覆盖 schema 非法值、ID/query/chunk 重复、证据、answerable、multi、private no-answer 路由、split/family、哈希损坏、跨目录读取、真实重切块、禁止 HTTP、JSON/Markdown 输出和拒绝覆盖。
- Windows 子进程编码警告已在新增 CLI/test 中修复；最终整套 pytest 无该 warning。原 fitz 导入弃用提示保留，未改上游代码。

运行命令：

```powershell
& ../nanobot/.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --junitxml=artifacts/v0_2/phase1_pytest.xml
& ../nanobot/.venv/Scripts/python.exe scripts/verify_plugin.py
& ../nanobot/.venv/Scripts/python.exe docs/evidence/phase3b/test_metrics.py -v
```

实际 JUnit、metric 原始日志、回归 JSON 见 ignored `artifacts/v0_2/phase1_pytest.xml`、`phase1_metric_checks.txt`、`phase1_regression.json`。校验器默认复跑只重新检查数据，不自动执行这些回归或声称它们再次通过。

## 冻结完整性

25 项 V0.1 frozen SHA256 全部不变；index/metadata 哈希一致；默认 V0.1 data/ 仍产生 9 个 chunk。所有 docs/evidence、docs/releases 与旧 tag 无变化；nanobot core clean；原 tracked files 无 diff。

V0.1 tag 目标仍为 `aa422d826fa484933d9949c16fc79e1a2f22eda1`。

新 test 内容锁定清单：`eval/v0.2/freeze_manifest.json`，SHA256 `078b30d94d2c4664a30aece15b3c255c9351345edc40a02dca15213b9fae9d18`；清单覆盖 40 份 corpus 文档与 5 份数据/配置文件。新建数据尚未 commit，SHA256 是本阶段的审阅锚点，不是防止恶意篡改的签名。

## 本轮文件

- `eval/v0.2/corpus/`：40 份虚构 TXT。
- `eval/v0.2/`：corpus manifest、dataset config、retrieval/routing golden、split manifest、freeze manifest。
- `experiments/v0_2/datasets.py` 与必要 __init__.py：仅数据校验。
- `scripts/v0_2/validate_datasets.py`：可重复运行，保存 JSON/Markdown；不安装依赖或运行模型。
- `tests/v0_2/test_datasets.py`：40 项新增测试。
- 本报告及 PLAN 中最新阶段说明；历史审计/phase evidence 原样保留。

没有 BM25/RRF/Hybrid、Prompt/Tool Description 优化、threshold、新索引或 Agent benchmark；没有 commit/push。后续阶段等待审阅，不依据当前 test 设计或调参。

## Phase 1.5 质量审计与 checkpoint

40 documents → 40 chunks 属于 **controlled synthetic retrieval benchmark**，不代表长文档 chunking 性能。实际每块46–67个cl100k计量token，没有触发160窗口拆分；每块主要肯定事实2–4条，不能外推长文档、overlap、跨页或OCR。

审阅14个代表样本、全体事实/主题组、重复权重与提示风险见[DATASET_AUDIT.md](DATASET_AUDIT.md)；只读冻结协议见[DATASET_FREEZE.md](DATASET_FREEZE.md)。现有45文件hash清单已覆盖corpus与四个dev/test分区，无新重复机制。

当前文档统一口径：**V0.1 historical regression scope: 51**；**V0.2 current full validation scope: 91**。48是Phase0.5最初只执行pytest/plugin的子集，不能作为完整V0.1口径。未发现明显跨split同一私有事实/答案组合泄漏，保留模板/编码/同split重复等warning，按用户授权准备普通checkpoint commit；不修改数据、main或旧tag，不push。
