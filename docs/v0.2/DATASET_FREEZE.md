# V0.2 Dataset Freeze Checkpoint

版本：`v0.2-dataset-1`。Phase 1.5 冻结确认时间（UTC）：`2026-10-04T15:34:43.376001+00:00`。

这是只读使用协议；不是新的数据生成器、第二套 hash 机制或模型评测结果。

## 冻结内容

唯一现有清单：`eval/v0.2/freeze_manifest.json`。

清单 SHA256：`078b30d94d2c4664a30aece15b3c255c9351345edc40a02dca15213b9fae9d18`。

Hash按文件原始字节计算（包含换行）。本次checkpoint仅以一次性`git -c core.autocrlf=false add`保留现有CRLF字节，不修改Git配置；提交前逐项验证Git暂存blob与清单一致。后续checkout或编辑不得转换已冻结数据的换行，否则校验会拒绝。

清单覆盖45文件：40份corpus原文 +corpus_manifest.json、dataset_config.json、retrieval_golden.json、agent_routing_golden.json、split_manifest.json。完整文件hash已经覆盖retrieval dev/test与routing dev/test，不复制数据。

- corpus：40文档/40chunk，独立于V0.1默认data与索引。
- Retrieval：dev36/test24；Routing：dev30/test20。
- family_id按主题互斥，共6dev/4test；固定seed42。
- 冻结checkpoint在`feat/v0.2-eval-hybrid`创建普通commit，不修改main或旧tag。提交SHA以Git历史为准，不在文件中填入自身commit造成循环更新。

## 后续读取边界

Phase 2/3可以只读test题目，并由评测器只读golden标签用于打分；不得用于参数、阈值、Prompt、Tool Description、词典/别名或规则调优。不得把expected_answer或expected_chunk_ids注入模型messages。先在dev完成参数/配置预注册，再执行test并保留所有失败。

所有正式test runs先记录config/dataset/manifest hash。得到test结果后不能删失败样本、改答案或按结果改题；不能将不同数据版本混成同一提升指标。真实标注问题应停止并请求批准新数据版本，旧版本和结果保留。

Corpus本身可以建独立V0.2检索索引，这是检索场景的一部分，不等于用test QA调参；禁止覆盖V0.1 store/index或修改默认Retriever/Tool来绕过评测。

## 审计限制

已读test只为数据质量审计，不用于选择参数/Prompt。它不是秘密blind holdout；存在人工合成模板、同split事实重复、规律角色编号和显式反例提示，见DATASET_AUDIT.md。没有发现明显同一私有事实/答案组合跨dev/test泄漏，不代表能排除全部语义shortcut。

40 documents → 40 chunks属于controlled synthetic retrieval benchmark，不代表长文档chunking性能。

## 只读复核

```powershell
& ../nanobot/.venv/Scripts/python.exe scripts/v0_2/validate_datasets.py
```

该命令读取清单和原文重验，将JSON/Markdown写入ignored artifacts/v0_2，不修改数据；不要用--report覆写既有人工审计结论。旧V0.1 tag仍为aa422d826fa484933d9949c16fc79e1a2f22eda1。

## 测试口径

V0.1 historical regression scope: 51。

V0.2 current full validation scope: 91（37原pytest +40dataset validation +11plugin verification +3独立metric checks）。48只表示Phase0.5初次未执行3项metric checks的子集；重复运行和历史clean-export复跑不加到独立测试数。
