"""在首次推理前冻结评分口径、策略差异和所有运行参数。"""
from pathlib import Path
from experiments.v0_2.routing.config import canonical_hash,write_once
ROOT=Path(__file__).resolve().parents[3]
CONFIG=ROOT/'experiments/v0_2/ablation/EVAL_CONFIG.json'
RUBRIC={
 'version':'ablation-rubric-1',
 'classes':{
  'correct':'全部必要核心事实完整、正确，且没有错误或unsupported private claim；仅泛化措辞差异可接受。',
  'partial':'部分必要核心事实正确，但遗漏其余必要事实；不能含事实错误、错误实体归属或unsupported private claim。',
  'incorrect':'核心事实错误、张冠李戴、unsupported private claim、答非所问或对有答案问题仅拒答；错误附加私有事实也判incorrect。',
  'correct_abstention':'仅用于private_no_answer：明确无法确定所问属性，没有猜测或虚构私有事实。'},
 'strict_accuracy':'(correct + correct_abstention) / 20; partial无strict credit；不另调权重。',
 'grounding':'先匿名判reference_grounded yes/no；再对照实际送达模型的tool evidence独立工程复核provided_evidence_grounded yes/no。公开Grounded指标用后者，两阶段都保存。诚实说明没有访问权限不构造私有事实，但未检索就声称资料不存在/已查过不grounded。通用问题依据通用知识，不要求知识库证据。',
 'unsupported_private_claims':'统计含至少一个不支持/错误私有断言的case数，不冒充原子claim数量；包含未检索却声称查询/知识库不存在。诚实无法访问不计。',
 'evidence_completeness':'由真实ToolResult与frozen required chunk IDs计算：全部complete、部分partial、零none；no-answer/general无required IDs为not_applicable，不因返回TopK就complete。',
 'answer_fact_completeness':'匿名工程判定candidate是否覆盖全部/部分/零必要事实；无私有证据需求和no-answer用not_applicable。它与retrieved evidence completeness分开。',
 'abstention':'no-answer只有correct_abstention才算成功；先说无法确定又猜具体值/角色不算成功。',
 'rates':{'tool_call':'至少实际执行一次知识库的cases/20','unnecessary':'expected_use_tool=false且执行检索的cases/5；同时给per-query率','missed':'expected_use_tool=true未执行检索的cases/15；B0标strategy-imposed而非router error','average_calls':'全部真实知识库执行数/20'},
 'blindness':'judgment input隐藏strategy/category/source-run标签，稳定hash排序，只提供query、gold expected facts/required evidence、candidate。助手已见Phase3A部分B2答案，不能声称真正独立blind；provided-evidence grounding的第二阶段必然不blind。无额外judge模型。',
 'limitations':['20-query synthetic controlled benchmark; 5 categories x4; single Qwen3:1.7b and single KB tool','manual corpus/questions and engineering answer judgments; no statistical significance or production-scale claims','B1固定调度真实tool后单次生成，无planning LLM；B2通常两次LLM且复用较早运行，E2E不是等LLM调用成本/同一时段性能比较','B1使用原query、同题A2实际top_k；B2可能自主改写query，效果差异不能全部归因routing','不新增threshold、Hybrid或Prompt调参；失败不删除、不重复采样挑结果']}
CLASSES=set(RUBRIC['classes']);COMPLETENESS={'complete','partial','none','not_applicable'}
def forced_args(item,b2):
    calls=b2['tool_calls']
    if len(calls)>1:raise ValueError('matched top_k ambiguous; stop rather than guess')
    k=calls[0]['arguments'].get('top_k',3) if calls else 3
    if type(k) is not int or not 1<=k<=10:raise ValueError('invalid frozen top_k')
    return {'query':item['query'],'top_k':k}
