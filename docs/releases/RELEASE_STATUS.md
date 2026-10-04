# V1 release status

Version identifier: v0.1-agentic-rag-baseline（拟定标识，当前尚未创建Git tag）。
仓库已初始化，原项目此前没有commit；当前Git author name/email尚未配置，首次commit与tag需用户指定身份后完成，不虚构作者邮箱，不修改全局设置。

## Completed
- README、Evaluation、Bad Cases、Demo、Resume Notes、三份第三方许可证及归属。
- 公开候选文件路径/密钥启发式扫描无发现，无>5MB文件。
- 9份含本机路径的原始证据生成脱敏副本；原始历史报告本机保留，root原始phase目录不进入Git。
- 51项原回归测试通过；干净安装副本37项通过、pip check通过、真实Embedding重建/回读TopK匹配。
- 3题自主smoke与1题forced structured smoke成功，7个请求HTTP200。保留Aurora犹豫及ORBIT-3证据概括偏差。
- nanobot core Git clean；66份原始冻结实现/数据/证据SHA256不变。

## Reproducibility scope
全新venv复现了RAG安装及索引重建；固定commit nanobot环境复现插件及真实Agent smoke。没有在全新机器重装Windows/Ollama/nanobot；安装步骤对照当前官方checkout README。未提供完整nanobot传递依赖锁，模型tag可变，因此manifest保留digest，不能承诺跨平台逐位可复现。

## Remaining required release action
用户提供本仓库Git author name/email后创建首个本地commit，并将实际hash记录在单独release记录，然后创建上述tag。没有设置remote或push；GitHub地址由用户决定。

## Not required fixes
路由FN、generation误读、无答案score重叠、fitz弃用提示是已公开的V1限制/未来工作，本轮不改baseline。
