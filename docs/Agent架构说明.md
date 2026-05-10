# Agent 架构说明

## 1. 架构概述

EduFusion 采用**单编排器 + 工具代理（Orchestrator + Tool-Agent）**架构，而非复杂的多 Agent 协作系统。

```
┌─────────────────────────────────────────────┐
│              Orchestrator (FastAPI)           │
│  - 请求路由                                   │
│  - 状态管理                                   │
│  - 流程编排                                   │
└─────────────────┬───────────────────────────┘
                  │
    ┌─────────────┼─────────────┐
    ▼             ▼             ▼
┌────────┐  ┌────────┐  ┌────────┐
│ Parser │  │ RAG    │  │ Chat   │  ...
│ Agent  │  │ Agent  │  │ Agent  │
└────────┘  └────────┘  └────────┘
```

### 1.1 为什么不用多 Agent？

| 考虑因素 | 多 Agent 协作 | 单编排器 + 工具 |
|---------|--------------|----------------|
| 复杂度 | 高（通信、协调、冲突解决） | 低（线性流程） |
| 可预测性 | 低（Agent 行为不确定） | 高（确定性状态流） |
| 调试难度 | 高 | 低 |
| 开发时间 | 长 | 短 |
| 适用场景 | 开放式探索 | 确定性工作流 |

**5 小时黑客松约束**下，确定性状态流是更安全的选择。

## 2. 工具代理设计

每个服务模块是一个 Tool-Agent，具有清晰的 I/O 接口：

### 2.1 Parser Agent

```python
输入: PDF/MD/TXT 文件
输出: Textbook + Chapter[]

职责:
- 文件格式识别
- 页面提取 (PyMuPDF)
- 章节检测 (正则)
- 虚拟章节回退
```

### 2.2 Extraction Agent

```python
输入: Chapter 内容
输出: KnowledgeNode[] + KnowledgeEdge[]

职责:
- LLM 知识抽取（优先）
- 规则抽取（回退）
- JSON 修复
- Pydantic 校验
```

### 2.3 Alignment Agent

```python
输入: KnowledgeNode[] + KnowledgeEdge[]
输出: MergeDecision[] + Merged Graph + Stats

职责:
- 文本嵌入计算
- 余弦相似度矩阵
- Union-Find 聚类
- LLM 判断（模糊区间）
- 合并决策生成
- 边重建
```

### 2.4 RAG Agent

```python
输入: 用户问题 + 教材文本
输出: 答案 + 引用

职责:
- 滑动窗口分片
- 向量嵌入
- 相似度检索
- LLM 答案生成
- 引用标注
```

### 2.5 Chat Agent

```python
输入: 教师自然语言指令
输出: 回复 + 修改后的决策

职责:
- 意图识别（规则优先）
- 目标提取
- 决策修改
- 历史记录
```

## 3. 降级策略

每个 Agent 都有完整的降级链：

```
LLM API → 本地模型 → 规则引擎 → 返回空/错误
```

| Agent | 降级路径 |
|-------|---------|
| Extraction | LLM → 规则提取 → 从标题生成 |
| Alignment | sentence-transformers → difflib |
| RAG | 向量检索 → 关键词检索 |
| Chat | LLM → 规则匹配 |
| Report | LLM → 模板生成 |

## 4. 提示词工程

### 4.1 提示词模板

所有 LLM 调用使用独立的提示词模板文件：

```
backend/prompts/
├── extract_knowledge.txt  # 知识抽取
├── merge_judge.txt        # 合并判断
├── rag_answer.txt         # RAG 答案
└── feedback_parse.txt     # 反馈解析
```

### 4.2 设计原则

1. **严格约束输出格式**: 只输出 JSON，无额外文本
2. **上下文隔离**: 每个任务独立的系统提示词
3. **少量示例**: 关键任务提供 few-shot 示例
4. **温度控制**: 事实性任务使用 temperature=0.1

## 5. 状态管理

### 5.1 内存状态

```python
# 各路由器维护的状态
_textbooks: dict[str, Textbook]     # textbooks.py
_current_graph: GraphResponse        # graph.py
_merged_graph: GraphResponse         # graph.py
_decisions: list[MergeDecision]      # integration.py
_stats: IntegrationStats             # integration.py
_rag_service: RAGService             # rag.py
_chat_service: ChatService           # chat.py
```

### 5.2 持久化

- 教材文件: `storage/uploads/`
- 解析结果: `storage/parsed/`
- 图谱数据: `storage/graphs/`
- 报告文件: `storage/reports/` + `report/整合报告.md`

## 6. 未来演进

如果需要从单编排器升级到更复杂的系统：

1. **LangGraph 状态机**: 将当前的线性流程转为有向图
2. **消息总线**: 引入异步消息传递
3. **Agent 协作**: 允许 Agent 之间直接通信
4. **外部记忆**: 使用 Redis/数据库替代内存状态

但在当前黑客松约束下，单编排器架构是最优选择。

## 7. 已知局限

| # | 局限 | 影响 | 改进方向 |
|---|------|------|---------|
| 1 | **LLM 每章 15 秒超时**：长章节（>5000 字）可能被截断，导致部分知识点遗漏 | 教材页数较多的章节，尾部知识点抽取不完整 | 分段后并行调用 LLM（当前每章限定 5000 字） |
| 2 | **规则降级时同义词识别精度低**：`_rule_extract` 基于关键词匹配，无法理解"细胞凋亡"="程序性细胞死亡"这类语义等价 | 无法加载 LLM 时，知识点可能漏抽或错分 | 引入同义词词典（如 HowNet）辅助规则匹配 |
| 3 | **内存状态不支持多 Worker**：所有状态存储在模块级全局变量中（`_textbooks`、`_current_graph` 等），多进程部署时状态不共享 | 生产环境使用 `uvicorn --workers 4` 时状态不一致 | 迁移到 Redis 或数据库（SQLite/PostgreSQL） |
| 4 | **FAISS 未真正启用**：向量检索当前使用 numpy dot product（O(n)），`_build_vector_index` 中注释掉了 FAISS 索引创建 | 教材总量超过 5000 chunks 时检索延迟显著增加 | 向量数 > 5000 时切换到 FAISS IndexFlatIP |
| 5 | **章节检测依赖正则**：`CHAPTER_PATTERNS` 只覆盖中英文常见标题格式，某些教材的章节格式（如纯数字编号、罗马数字）可能漏检 | 特殊格式教材检测不到章节，全部归入虚拟章节 | 增加更多章节模式，或使用 LLM 辅助章节边界检测 |
