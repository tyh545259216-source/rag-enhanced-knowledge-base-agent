# Retrieval baseline — Phase 1 unchanged

时间：2026-10-03T16:49:18.065462+08:00
20 个有答案问题（15 单块、5 多块）+ 10 个无答案问题。标注依据现有九段虚构资料；不是独立留出集。

## 指标定义
HitRate@K：至少命中一个相关 chunk 的问题比例。
Recall@K：每题命中相关块数 / 标注相关块总数，再做宏平均。
MRR@K：Top-K 内首个相关块倒数排名的平均值，未命中计零。
无答案问题相关集合为空，不纳入上述三个指标；不把空集合 recall 记为 1。

## 结果
- K=1: HitRate=0.850, Recall=0.750, MRR=0.850
- K=3: HitRate=1.000, Recall=0.975, MRR=0.925
- K=5: HitRate=1.000, Recall=1.000, MRR=0.925

## Latency
一个首请求单独记录，随后30题各3次，共90个顺序请求；不做并发压测。首请求不能代表真正模型冷启动。
检索一次获取 Top-5，K=1/3/5 指标从同一排名截断；延迟对应 Top-5，不是各 K 独立测量。
- embedding_ms: mean=151.650ms, p50=138.644ms, p95=251.727ms
- faiss_ms: mean=0.281ms, p50=0.247ms, p95=0.493ms
- total_ms: mean=151.950ms, p50=138.886ms, p95=252.149ms
- wall_ms: mean=151.960ms, p50=138.896ms, p95=252.160ms

## No-answer score distributions
Top-1 相似度不是相关性概率，也不证明答案存在。以下每题只贡献一个 top1 分数，重复请求不扩大分布样本数。
- answerable_top1: n=20, min=0.772871, max=0.892266, mean=0.819129, p50=0.813721, p95=0.864564
- no_answer_top1: n=10, min=0.601635, max=0.867672, mean=0.752533, p50=0.792352, p95=0.853732
- no_answer_top5_all: n=50, min=0.531384, max=0.867672, mean=0.648917, p50=0.605317, p95=0.814809

## Bad cases
- q01 项目 Aurora 的负责人是谁？：top1_wrong；Top-1=note_02.txt / 0.863106；Top-3缺失=[]
- q05 Aurora 的预算金额和预算审批人是谁？：top1_wrong；Top-1=note_02.txt / 0.814452；Top-3缺失=[]
- q19 Aurora 和 Borealis 的负责人分别是谁？：top1_wrong；Top-1=note_02.txt / 0.791406；Top-3缺失=[]
- q20 Aurora 的预算是多少，日志保留几天？：partial_recall_at_3；Top-1=note_06.txt / 0.810900；Top-3缺失=['note_03.txt:ptxt:000']
- q21 火星殖民地的量子传送门密码是什么？：no_answer_returns_neighbors；Top-1=note_09.txt / 0.601635；Top-3缺失=[]
- q22 项目 Zephyr 的负责人是谁？：no_answer_returns_neighbors；Top-1=note_02.txt / 0.661064；Top-3缺失=[]
- q23 项目 Aurora 的负责人手机号码是多少？：no_answer_returns_neighbors；Top-1=note_02.txt / 0.836694；Top-3缺失=[]
- q24 Aurora 的预算审批日期是哪一天？：no_answer_returns_neighbors；Top-1=note_02.txt / 0.780318；Top-3缺失=[]
- q25 机器人 RB-204 的电池容量是多少？：no_answer_returns_neighbors；Top-1=note_05.txt / 0.818431；Top-3缺失=[]
- q26 服务器 SABLE-17 的管理员密码是什么？：no_answer_returns_neighbors；Top-1=note_06.txt / 0.804386；Top-3缺失=[]
- q27 NORTH-6 仓库的街道地址是什么？：no_answer_returns_neighbors；Top-1=note_08.txt / 0.735807；Top-3缺失=[]
- q28 ORBIT-3 会议室最多容纳多少人？：no_answer_returns_neighbors；Top-1=note_09.txt / 0.867672；Top-3缺失=[]
- q29 Cedar 的发布负责人邮箱是什么？：no_answer_returns_neighbors；Top-1=note_07.txt / 0.810383；Top-3缺失=[]
- q30 海王星空间站的咖啡配送频率是多少？：no_answer_returns_neighbors；Top-1=note_09.txt / 0.608936；Top-3缺失=[]

## 分析与限制
- 项目负责人、验收负责人、维护负责人之间存在语义混淆；相关证据排名偏后时，HitRate 高并不代表排序准确。
- 多块问题需要全部证据；MRR 只看首个相关块，不能替代 Recall。
- 同实体但缺少属性的无答案问题可得到很高分，与有答案样本明显重叠；本轮不设置阈值。
- 当前30题/9块规模很小，问题按资料人工编写，结果不能外推到真实大知识库。
- 未调用生成模型，因此不评价回答正确性、groundedness 或 Agent 工具选择。
- 所有 src/data/store/config 文件运行前后 SHA256 相同；没有重建索引或改变 Phase 1 实现。
- 原始结果、全部文本与指纹见 retrieval_baseline.json。
