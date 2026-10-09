"""AI 助手域子系统包。

本包承载 AI 助手**特有、且不属于标准分层（api / schemas / services / repositories /
models）**的领域能力，参考 notification/ 域子系统的组织方式。标准分层文件
（schemas/assistant.py、services/assistant_service.py 等）与各业务平级存放。

本包成员与职责：
    - tools       工具注册机制（BaseTool / ToolRegistry / ToolSource）。
                  工具可运行时动态注册；来源可插拔：内置（BuiltinToolSource）+
                  预留 MCP（MCPToolSource，受配置 ai.tools.mcp_enabled 控制）
    - memory      记忆分层接口。第 1 层长期记忆 UserLongTermMemory（Null 空实现 +
                  DbUserLongTermMemory 数据库实现）；第 2/3 层实现在 memory.py
    - knowledge   静态知识库：系统提示词 + 入口清单组装（含用户档案注入点）
    - retriever   知识检索（RAG）：RetrieverProvider 抽象 + NullRetriever 空实现，待接入

大模型客户端抽象（LLMProvider）位于 infras/llm.py（第三方 SDK 封装，遵循
infras 层「抽象基类 + 具体实现 + 工厂 + 单例」约定）。

扩展约定：
    - 新增工具 = 继承 BaseTool + 在 ToolSource 注册，编排层零改动
    - 接入长期记忆 = 实现 UserLongTermMemory 并替换依赖工厂注入
    - 接入 RAG = 实现 RetrieverProvider 并开启 ai.retriever.enabled
    - 接入 MCP = 实现 MCPToolSource.load_tools 并开启 ai.tools.mcp_enabled
"""
