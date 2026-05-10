# Claude Code 开发作战手册：5 小时 AI 全栈黑客松执行指南

> 目标目录：`D:\1Hackathon\docs\plans\Claude_Code开发作战手册.md`  
> 适用项目：EduFusion Agent / 学科知识整合智能体  
> 核心目标：用 Claude Code 高效完成“上传解析 → 知识图谱 → 跨教材整合 → RAG 问答 → 教师反馈 → 报告与部署”的 P0 闭环。

---

## 0. 使用原则

这份文档不是 Claude Code 入门教程，而是黑客松期间的“开发指挥手册”。它回答这些问题：

1. 总体要给 Claude Code 哪些文件。
2. 分几轮发送上下文。
3. 每一步用什么提示词。
4. 哪些步骤开启 Plan Mode。
5. 哪些步骤需要 Claude 高推理模型，哪些步骤普通模型即可。
6. 哪些步骤要用 Claude Code 的 Skill、Subagent、Slash Command 或普通对话。
7. 哪些文件不能给 Claude Code 读取或提交。

最终策略：

```text
Plan Mode 做架构与高风险决策
Sonnet/普通执行模式做代码落地
Skills/Commands 固化重复流程
Subagents 只用于并行 review / docs / test，不把系统搞复杂
```

黑客松时间只有 5 小时，不建议把大量时间花在搭建复杂 Claude Code 工具链上。Claude Code 工具链的目标是提升开发速度，而不是成为新的工程负担。

---

## 1. 赛题执行结论

本项目必须优先完成赛题 P0：

```text
多格式上传解析
PDF 章节识别
知识点抽取
知识图谱交互
跨教材整合去重
压缩比 ≤ 30%
RAG 带引用问答
教师对话修改整合决策
Web SPA
整合报告
README + docs 文档
公网部署
```

Claude Code 的所有任务都围绕这个闭环推进，避免让 Claude 发散到 OCR、GraphRAG、复杂多 Agent、完整 7 本教材全量高精度处理等高风险方向。

---

## 2. Claude Code 启动与基础配置

### 2.1 推荐启动方式

在项目根目录启动：

```bash
cd D:\1Hackathon
claude --model opusplan --permission-mode plan
```

如果 `opusplan` 不可用，则用：

```bash
claude --model sonnet --permission-mode plan
```

推荐逻辑：

| 阶段 | 推荐模型 | 原因 |
|---|---|---|
| 总体架构、复杂取舍、算法边界 | `opusplan` 或 `opus` | 需要高推理与全局规划 |
| 常规代码实现 | `sonnet` | 代码能力强、成本/速度平衡 |
| 文档补全、README、简单样式调整 | `sonnet` 或 `haiku` | 难度低，不必用最强模型 |
| 批量生成小文件、简单修复 | `haiku` 可用 | 不涉及复杂判断 |

### 2.2 常用 Slash Commands

| 命令 | 用途 | 本项目怎么用 |
|---|---|---|
| `/init` | 生成项目 `CLAUDE.md` | 第一次进入项目后运行 |
| `/model` | 切换模型 | 架构/融合/RAG 用强模型，普通代码用 Sonnet |
| `/permissions` | 管理文件和命令权限 | 禁止读取 `.env`、教材 PDF、secrets |
| `/cost` | 查看 token 成本 | 每完成一个大阶段检查一次 |
| `/compact` | 压缩上下文 | 完成后端/前端/RAG阶段后使用 |
| `/clear` | 清空上下文 | 新开完全无关任务时才用 |
| `/agents` | 管理 subagents | 可创建 docs/reviewer/test subagent |
| `/review` | 请求代码审查 | 最后 30 分钟跑一次 |
| `/doctor` | 检查安装状态 | 开赛前运行 |

### 2.3 Plan Mode 使用规则

Plan Mode 用于只读分析和制定计划，不让 Claude 直接改文件。适合：

```text
1. 初始架构设计
2. API 边界设计
3. 数据模型设计
4. 跨教材整合算法设计
5. RAG 策略设计
6. 部署前风险排查
7. 最终代码审查
```

不要在每一步都开 Plan Mode。实现阶段要切回普通模式或 accept edits，否则 Claude 不能写文件。

切换方式：

```text
Shift + Tab 循环切换 permission mode
看到 “plan mode on” 表示已进入 Plan Mode
```

或启动时：

```bash
claude --permission-mode plan
```

### 2.4 权限与敏感文件保护

建议创建 `.claude/settings.json`：

```json
{
  "permissions": {
    "deny": [
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(./secrets/**)",
      "Read(./backend/storage/uploads/**)",
      "Read(./data/textbooks/**)",
      "Read(./**/*.pdf)",
      "Bash(curl:*)",
      "Bash(rm -rf:*)"
    ],
    "ask": [
      "Bash(git push:*)",
      "Bash(npm install:*)",
      "Bash(pip install:*)",
      "Bash(docker:*)"
    ],
    "allow": [
      "Bash(git status:*)",
      "Bash(git diff:*)",
      "Bash(npm run lint:*)",
      "Bash(npm run build:*)",
      "Bash(pytest:*)",
      "Bash(python -m pytest:*)"
    ],
    "defaultMode": "default"
  }
}
```

注意：

```text
不要让 Claude 读取真实 API Key
不要把教材 PDF 提交到 GitHub
不要让 Claude 任意执行 rm -rf、curl 下载未知脚本、上传 secret
```

---

## 3. 总体要发送给 Claude Code 的文件

### 3.1 第一轮必须提供的上下文文件

第一轮只给最关键的上下文，避免上下文污染。

建议让 Claude Code 读取：

```text
@docs/plans/最终执行方案设计.md
@docs/plans/Claude_Code开发作战手册.md
@README.md                    # 如果已有
@package.json                 # 如果已有
@requirements.txt             # 如果已有
```

如果赛题 PDF 已经转成 Markdown 摘要，则优先给 Markdown 摘要，不建议直接让 Claude 处理 PDF。

推荐在项目里准备：

```text
docs/spec/赛题要求摘要.md
```

内容只保留：

```text
P0 功能要求
评分标准
提交要求
技术建议
README/docs/report 文件要求
```

### 3.2 不建议一次性发送的文件

不要一上来就把三份长方案、所有报告、PDF 原文、教材文件全部塞给 Claude。

原因：

```text
1. 上下文会被稀释
2. Claude 可能在方案之间摇摆
3. 编码阶段不需要研究报告全文
4. 大文件会浪费 token 和时间
```

### 3.3 三份方案如何使用

三份方案只在“规划阶段”使用一次。规划完成后以 `最终执行方案设计.md` 为唯一准绳。

| 文件 | 什么时候给 Claude | 用途 |
|---|---|---|
| `AI黑客松赛题方案设计（gemini）.md` | 只在架构/技术论证阶段 | 提取语义对齐、P2、架构深度 |
| `需求拆解与产品设计（claude）.md` | 只在评分和产品结构阶段 | 提取评分拆解、产品流程 |
| `研究报告（gpt）.md` | 只在技术路线与 Prompt 阶段 | 提取 MVP、接口、Prompt、排期 |
| `最终执行方案设计.md` | 全程使用 | 唯一执行准则 |

### 3.4 每个开发阶段给 Claude 的文件范围

| 阶段 | 发送/引用文件 | 不要发送 |
|---|---|---|
| 架构规划 | `最终执行方案设计.md`、赛题摘要 | PDF 教材、代码无关文件 |
| 后端骨架 | `最终执行方案设计.md`、当前 `backend/` | 前端大文件、研究报告全文 |
| 前端开发 | `frontend/`、接口文档、图谱 JSON 示例 | 后端无关日志、PDF |
| RAG 开发 | `backend/services/rag_service.py`、`schemas.py`、Prompt | 真实教材全文 |
| 文档生成 | `最终执行方案设计.md`、当前代码结构 | API Key、上传数据 |
| 部署检查 | `README.md`、`.env.example`、部署配置 | `.env`、secrets |

---

## 4. 建议创建的 CLAUDE.md

在项目根目录放置 `CLAUDE.md`，这是 Claude Code 的项目记忆。建议内容如下：

```markdown
# EduFusion Agent 项目说明

## 项目目标
在 5 小时黑客松内实现“学科知识整合智能体”的 P0 闭环：上传教材、解析章节、抽取知识点、构建交互式知识图谱、跨教材整合去重、压缩到原始体量 30% 以内、RAG 带引用问答、教师反馈修改整合决策、生成报告并部署。

## 最高优先级
1. P0 全覆盖优先于算法完美。
2. 所有功能必须有前端入口、后端接口、可见结果。
3. 不做 OCR、复杂 GraphRAG、复杂多 Agent、自主全量教材深处理。
4. 压缩比口径是“整合后内容总字数 / 原始总字数 ≤ 30%”，不是节点数。
5. RAG 回答必须引用教材名、章节、页码；找不到答案必须回复“当前知识库中未找到相关信息”。

## 技术栈
- Backend: FastAPI + Pydantic + PyMuPDF + FAISS/可选 BM25 + SQLite/JSON
- Frontend: React + Vite + TypeScript + ECharts Graph
- LLM: OpenAI-compatible adapter，可接 DeepSeek/Qwen/OpenAI/Claude
- Storage: 本地 JSON/SQLite，上传文件与向量索引不提交 GitHub

## 项目目录
参考 @docs/plans/最终执行方案设计.md。

## 代码要求
- 后端模块化：parser/extractor/graph/alignment/compression/rag/feedback/report
- Pydantic schema 必须集中管理
- 所有 LLM 输出必须做 JSON 校验和失败兜底
- 不读取 `.env`、secrets、教材 PDF 原文
- 不把 PDF、向量索引、上传文件提交到 GitHub

## 演示优先级
上传 → 解析 → 图谱 → 整合 → RAG → 教师反馈 → 报告。
```

运行：

```text
/init
```

然后把上面内容补充进去。

---

## 5. 建议使用的 Skills / Subagents / Commands

Claude Code 中有三类容易混淆的机制：

| 名称 | 触发方式 | 适合做什么 | 本项目建议 |
|---|---|---|---|
| `CLAUDE.md` | 启动时自动加载 | 全局项目规则 | 必用 |
| Custom Slash Command | 用户输入 `/xxx` | 重复执行的固定提示词 | 推荐 |
| Skill | Claude 自动判断或 `/skill-name` | 特定工作流、可带说明/脚本/模板 | 可选 |
| Subagent | 主 Claude 委派任务 | 专项 review / docs / test | 可选，不要过度 |

### 5.1 必用：CLAUDE.md

这是最低成本、最高收益的配置。所有团队成员都应该共享。

### 5.2 推荐：Custom Slash Commands

创建目录：

```bash
mkdir -p .claude/commands
```

#### `/p0-check`

文件：`.claude/commands/p0-check.md`

```markdown
---
description: Check current implementation against P0 requirements
allowed-tools: Read, Grep, Glob, LS, Bash(git status:*), Bash(git diff:*)
---

请根据 @docs/plans/最终执行方案设计.md 检查当前项目是否覆盖 P0。
输出：
1. 已完成项
2. 未完成项
3. 高风险项
4. 30 分钟内最该补的 5 件事
5. 不要修改文件，只做检查
```

#### `/api-check`

文件：`.claude/commands/api-check.md`

```markdown
---
description: Verify backend API completeness for hackathon demo
allowed-tools: Read, Grep, Glob, LS
---

检查后端接口是否覆盖：
- /api/textbooks/upload
- /api/textbooks/{id}/parse
- /api/graph/build
- /api/integration/run
- /api/rag/index
- /api/rag/status
- /api/rag/query
- /api/chat
- /api/report

输出缺失接口、字段不一致、前端可能无法调用的位置。
```

#### `/demo-check`

文件：`.claude/commands/demo-check.md`

```markdown
---
description: Prepare final demo checklist
allowed-tools: Read, Grep, Glob, LS, Bash(git status:*)
---

请按比赛演示顺序检查项目：
上传 → 解析 → 图谱 → 整合 → RAG → 教师反馈 → 报告 → README → 部署。
输出一份 10 分钟演示脚本和当前风险清单。
不要修改文件。
```

#### `/docs-score`

文件：`.claude/commands/docs-score.md`

```markdown
---
description: Score docs against contest rubric and suggest improvements
allowed-tools: Read, Grep, Glob, LS
---

请根据赛题评分维度检查 docs 与 report：
- README
- docs/需求分析.md
- docs/系统设计.md
- docs/Agent架构说明.md
- report/整合报告.md

输出：
1. 文档缺失项
2. 按 A/D/E/F 维度的预计得分
3. 每份文档最应该补的内容
4. 不要修改文件，先给建议
```

### 5.3 可选：Project Skills

如果 Claude Code 已支持 Skills，建议创建 4 个轻量 Skill。Skills 不要太宽泛，保持“一项能力一个 Skill”。

目录：

```text
.claude/skills/
├── hackathon-p0-executor/
│   └── SKILL.md
├── fastapi-rag-backend/
│   └── SKILL.md
├── echarts-graph-frontend/
│   └── SKILL.md
└── scoring-docs-writer/
    └── SKILL.md
```

#### Skill 1：hackathon-p0-executor

```markdown
---
name: hackathon-p0-executor
description: Use for implementing P0 features of the EduFusion hackathon project under strict time constraints.
allowed-tools: Read, Grep, Glob, LS, Edit, MultiEdit, Write, Bash(npm run build:*), Bash(pytest:*), Bash(git diff:*)
---

# Hackathon P0 Executor

## Rules
- Prioritize P0 completeness over elegance.
- Every feature must have API + UI + visible result.
- Do not add OCR, GraphRAG, complex multi-agent, auth, or heavy databases.
- Use FastAPI, Pydantic, React, ECharts, FAISS/JSON as defined in the plan.
- Never read `.env`, secrets, uploaded PDFs, or vector data.

## Output Style
For each implementation, report:
1. Files changed
2. API/UI behavior added
3. How to test
4. Remaining risk
```

#### Skill 2：fastapi-rag-backend

```markdown
---
name: fastapi-rag-backend
description: Use when building FastAPI backend modules for parsing, graph, integration, RAG, chat, or reports.
allowed-tools: Read, Grep, Glob, LS, Edit, MultiEdit, Write, Bash(pytest:*), Bash(python -m pytest:*)
---

# FastAPI RAG Backend Skill

## Requirements
- Use Pydantic schemas.
- Keep routers and services separated.
- Add failure fallback for LLM, parser, embedding, and vector search.
- Preserve textbook/chapter/page metadata in every chunk and citation.
- API responses must match frontend needs.

## Required Modules
- parser_service.py
- extraction_service.py
- graph_service.py
- alignment_service.py
- compression_service.py
- rag_service.py
- feedback_service.py
- report_service.py
```

#### Skill 3：echarts-graph-frontend

```markdown
---
name: echarts-graph-frontend
description: Use when building React ECharts graph visualization and the SPA interface.
allowed-tools: Read, Grep, Glob, LS, Edit, MultiEdit, Write, Bash(npm run build:*), Bash(npm run lint:*)
---

# ECharts Graph Frontend Skill

## Requirements
- Use three-column SPA layout.
- Middle area is ECharts graph.
- Node color indicates source textbook.
- Node size indicates frequency.
- Node click opens detail panel.
- Support graph search/highlight if time allows.
- Keep UI simple and demo-friendly.
```

#### Skill 4：scoring-docs-writer

```markdown
---
name: scoring-docs-writer
description: Use when writing README, requirements analysis, system design, Agent architecture docs, and integration report.
allowed-tools: Read, Grep, Glob, LS, Edit, MultiEdit, Write
---

# Scoring Docs Writer

## Required Docs
- README.md
- docs/需求分析.md
- docs/系统设计.md
- docs/Agent架构说明.md
- report/整合报告.md

## Writing Rules
- Map content to scoring criteria.
- Include Mermaid diagrams in Agent architecture and system design.
- Explain design tradeoffs: why single Orchestrator + tools, why not complex multi-agent.
- Include RAG chunk size rationale and compression ratio formula.
- Include known limitations and future work.
```

### 5.4 可选：Subagents

使用 `/agents` 创建。建议只建 3 个，避免管理成本过高。

| Subagent | 什么时候用 | 工具权限 | 模型要求 |
|---|---|---|---|
| `backend-reviewer` | 后端完成后检查 API、schema、异常兜底 | Read/Grep/Glob/Bash pytest | Sonnet 即可 |
| `frontend-reviewer` | 前端完成后检查界面和接口绑定 | Read/Grep/Glob/Bash npm build | Sonnet 即可 |
| `docs-scorer` | 最后检查文档和评分映射 | Read/Grep/Glob | Sonnet/Haiku 即可 |

不要创建“全能实现 subagent”，主线程亲自控制任务更稳。

---

## 6. 分步骤发送给 Claude Code 的执行流程

下面是正式开发时的推荐顺序。每一步都包含：文件、模式、模型、提示词、产出、模型要求。

---

## Step 0：开赛前环境检查

### 是否开启 Plan Mode

不开。普通模式即可。

### 模型要求

无所谓，`sonnet` 或默认模型即可。

### 给 Claude 的文件

无需文件。

### 提示词

```text
请检查当前项目开发环境是否适合 5 小时黑客松：
1. 检查 Node、npm、Python、pip 是否可用
2. 检查当前目录结构
3. 如果没有项目文件，请不要创建大工程，只输出最小初始化命令
4. 不要读取 .env、PDF 或 secrets
```

### 手动命令

```bash
node -v
npm -v
python --version
pip --version
claude doctor
```

### 产出

```text
确认能启动 FastAPI 和 React/Vite。
```

---

## Step 1：总体架构确认与任务拆分

### 是否开启 Plan Mode

必须开启。

### 模型要求

高。推荐 `opusplan` 或 `opus`。

### 给 Claude 的文件

```text
@docs/plans/最终执行方案设计.md
@docs/spec/赛题要求摘要.md     # 如果有
```

### 提示词

```text
你现在是 5 小时黑客松的技术负责人。
请只基于 @docs/plans/最终执行方案设计.md 制定执行计划，不要引入复杂新方案。

要求：
1. 输出 0-300 分钟开发排期
2. 输出 P0 必做清单
3. 输出后端/前端/文档的并行分工
4. 输出本项目最小可交付功能边界
5. 明确哪些功能不做：OCR、GraphRAG、复杂多 Agent、全量七本高精度处理
6. 不要修改文件，只给计划
```

### 产出

```text
最终任务列表与开发顺序。
```

### 完成后

确认计划无误后切回普通模式。

---

## Step 2：生成项目骨架

### 是否开启 Plan Mode

先 Plan 5 分钟，确认目录；然后关闭 Plan Mode 让 Claude 写文件。

### 模型要求

中等。`sonnet` 足够。

### 给 Claude 的文件

```text
@docs/plans/最终执行方案设计.md
```

### 提示词

```text
请按照 @docs/plans/最终执行方案设计.md 创建 EduFusion Agent 的最小项目骨架。

要求：
1. 后端使用 FastAPI，目录为 backend/
2. 前端使用 React + Vite + TypeScript，目录为 frontend/
3. 创建 docs/ 与 report/ 目录
4. 创建 README.md、requirements.txt、.env.example、.gitignore
5. 创建 backend/main.py、backend/schemas.py、backend/routers、backend/services、backend/prompts
6. 创建 frontend/src/App.tsx 与基础三栏布局组件占位
7. 不要实现复杂逻辑，只要项目能启动
8. .gitignore 必须排除 *.pdf、.env、上传目录、向量目录、node_modules
9. 完成后告诉我启动命令
```

### 产出

```text
最小可启动项目。
```

### 验收

```bash
cd backend
uvicorn main:app --reload

cd frontend
npm install
npm run dev
```

---

## Step 3：实现后端 Pydantic 数据模型与 API 骨架

### 是否开启 Plan Mode

不开。普通实现模式。

### 模型要求

中等，`sonnet`。

### 给 Claude 的文件

```text
@backend/main.py
@backend/schemas.py
@docs/plans/最终执行方案设计.md
```

### 提示词

```text
请先实现后端数据模型和 API 路由骨架，不要做复杂算法。

需要的 schemas：
- Textbook
- Chapter
- KnowledgeNode
- KnowledgeEdge
- MergeDecision
- RAGChunk
- RAGQueryRequest
- RAGQueryResponse
- ChatRequest
- ChatResponse
- ReportResponse

需要的 routers：
- textbooks.py
- graph.py
- integration.py
- rag.py
- chat.py
- report.py

要求：
1. 每个接口先能返回 mock 或空结构
2. 响应结构要稳定，方便前端接入
3. 用 Pydantic 校验
4. main.py 注册所有 router
5. 添加 /health
6. 不要读取真实 PDF，不要调用 LLM
```

### 产出

```text
后端接口骨架 + OpenAPI 可见。
```

### 验收

打开：

```text
http://localhost:8000/docs
```

---

## Step 4：实现教材上传与解析

### 是否开启 Plan Mode

不开，直接实现。PDF 章节规则复杂时可短暂开 Plan。

### 模型要求

中等。`sonnet` 足够。

### 给 Claude 的文件

```text
@backend/schemas.py
@backend/routers/textbooks.py
@backend/services/parser_service.py
```

### 提示词

```text
请实现教材上传与解析模块。

功能要求：
1. 支持 PDF、Markdown、TXT
2. PDF 使用 PyMuPDF 逐页解析，不要一次性加载整本书
3. Markdown/TXT 直接读取
4. 章节识别使用正则：第X章、第X节、Chapter X、1.1 标题
5. 章节识别失败时，按每 10 页创建虚拟章节；TXT/MD 创建默认章节
6. 输出 Textbook + Chapter[]
7. 保存解析结果到 backend/storage/parsed/*.json
8. 文件状态包括 uploaded / parsing / parsed / failed
9. 不做 OCR
10. 添加基本错误处理

请实现后端代码，并给出 curl 测试命令。
```

### 产出

```text
上传与解析可用。
```

### 验收

```text
上传一个小 PDF 或 TXT 后，前端/接口能看到 chapters[]。
```

### 模型能力要求

```text
普通模型即可，关键是工程细节和兜底。
```

---

## Step 5：实现前端三栏布局与教材管理

### 是否开启 Plan Mode

不开。

### 模型要求

普通。`sonnet` 或更低都可以。

### 给 Claude 的文件

```text
@frontend/src/App.tsx
@frontend/src/components/UploadPanel.tsx
@frontend/src/components/TextbookList.tsx
@frontend/src/api/*
```

如果文件还不存在，让 Claude 创建。

### 提示词

```text
请实现前端基础三栏布局和教材管理功能。

要求：
1. React + TypeScript
2. 左侧：上传区、文件列表、解析状态、章节树
3. 中间：先放图谱占位区域
4. 右侧：Tabs，占位为 节点详情 / 整合决策 / RAG问答 / 教师对话 / 报告
5. 调用后端 /api/textbooks/upload 和 /api/textbooks/{id}/parse
6. 上传后展示文件名、格式、大小、状态
7. 解析后展示章节标题、页码、字数
8. UI 简洁，不要引入复杂状态库
9. 不要做花哨动效
```

### 产出

```text
可以上传、解析、显示章节树的前端。
```

---

## Step 6：实现知识点抽取与图谱 JSON

### 是否开启 Plan Mode

建议先 Plan 5 分钟确认 Prompt 和 schema，然后执行。

### 模型要求

高。这里涉及 LLM 输出约束、JSON 校验和知识关系，推荐 `opusplan` 规划，`sonnet` 实现。

### 给 Claude 的文件

```text
@backend/schemas.py
@backend/services/extraction_service.py
@backend/services/graph_service.py
@backend/prompts/extract_knowledge.txt
@docs/plans/最终执行方案设计.md
```

### 提示词

```text
请实现知识点抽取与图谱构建模块。

目标：
从章节文本中生成 nodes[] 和 edges[]，用于前端 ECharts 图谱。

要求：
1. 每章最多抽取 5-10 个知识点
2. 每章最多 15 条边
3. 关系类型只能是 prerequisite / parallel / contains / applies_to
4. LLM Prompt 放在 backend/prompts/extract_knowledge.txt
5. LLM 调用用一个 OpenAI-compatible adapter，读取环境变量：LLM_BASE_URL、LLM_API_KEY、LLM_MODEL
6. 如果没有 LLM_API_KEY，则使用规则兜底：从章节标题和高频词生成 mock nodes
7. LLM 输出必须经过 Pydantic/JSON 校验
8. 校验失败允许一次 repair，仍失败则规则兜底
9. /api/graph/build 可以触发构建
10. /api/graph 返回当前图谱 JSON
11. 图谱数据保存到 backend/storage/graphs/graph.json

请先实现稳定可运行版本，不要追求抽取质量完美。
```

### 产出

```text
Graph JSON：nodes + edges。
```

### API 模型能力要求

```text
较高。
运行时 LLM 需要较强中文理解、结构化输出、关系抽取能力。
若预算有限，知识抽取可用强模型；报告和反馈解析用弱模型。
```

---

## Step 7：实现 ECharts 知识图谱

### 是否开启 Plan Mode

不开。

### 模型要求

普通，`sonnet` 足够。

### 使用 Skill

如果已创建，使用 `echarts-graph-frontend` Skill。

### 给 Claude 的文件

```text
@frontend/src/components/GraphView.tsx
@frontend/src/components/NodeDetailPanel.tsx
@frontend/src/App.tsx
@frontend/src/api/*
```

### 提示词

```text
请实现 ECharts 知识图谱可视化。

要求：
1. 调用 /api/graph 获取 nodes 和 edges
2. 使用 ECharts graph series，layout=force
3. 支持缩放、拖拽画布、拖拽节点
4. 节点颜色区分教材来源
5. 节点大小反映 frequency
6. 点击节点后在右侧节点详情 Tab 展示 name、definition、category、chapter、page、source_quote
7. 边展示 relation_type
8. 添加一个搜索框，输入关键词后高亮匹配节点；如果时间紧，搜索可以只做节点过滤/高亮
9. 图谱为空时显示引导文案
```

### 产出

```text
核心可视化演示能力。
```

### 模型能力要求

```text
普通代码能力即可。重点是接口字段匹配和 UI 可靠。
```

---

## Step 8：实现跨教材整合与压缩比

### 是否开启 Plan Mode

必须先开启 Plan Mode。

### 模型要求

高。推荐 `opusplan` 或 `opus` 规划，`sonnet` 实现。

### 给 Claude 的文件

```text
@backend/schemas.py
@backend/services/alignment_service.py
@backend/services/compression_service.py
@backend/services/graph_service.py
@backend/routers/integration.py
@docs/plans/最终执行方案设计.md
```

### 提示词：Plan 阶段

```text
请只读分析，不要改文件。
基于当前 schemas 和 graph 数据结构，为跨教材整合设计一个 5 小时内可实现的算法。

必须满足：
1. 生成 merge/keep/remove 决策
2. 每个决策有 reason 和 confidence
3. 压缩比口径为 整合后内容总字数 / 原始教材总字数 <= 30%
4. 优先降低误合并风险
5. 无 embedding 模型时要有字符串相似度兜底
6. 教师反馈可以修改决策

请输出实现步骤、阈值、数据结构、API 响应，不要修改代码。
```

确认后切回普通模式。

### 提示词：实现阶段

```text
请实现跨教材整合与压缩比模块。

算法要求：
1. 对所有 KnowledgeNode 使用 name + definition 做归一化文本
2. 优先用 embedding 相似度；如果 embedding 不可用，用 difflib/字符相似度兜底
3. similarity >= 0.90 自动 merge
4. 0.82 <= similarity < 0.90 标记为候选；如果没有 LLM judge，就保守 keep
5. 使用并查集合并重复节点
6. 生成 MergeDecision[]，action 包含 merge/keep/remove
7. 每个 merge 有 affected_nodes、result_node、reason、confidence
8. 生成 merged_graph
9. 计算 original_chars、compressed_chars、compression_ratio
10. 如果 compression_ratio > 30%，按低重要性节点裁剪 source_quote/definition，直到 <= 30%
11. /api/integration/run 触发整合
12. /api/integration/decisions 返回决策
13. /api/graph?mode=merged 返回整合后图谱
```

### 产出

```text
核心难点可演示：merge/keep/remove + 30% 压缩比。
```

### API 模型能力要求

```text
高。
如果使用 LLM 判断等价概念，这一步需要模型具备强语义辨析能力，尤其是“同义词 vs 上下位概念 vs 相关但不同概念”。
如果时间紧，先不用 LLM judge，采用高阈值 embedding + 教师反馈纠错。
```

---

## Step 9：实现 RAG 索引与带引用问答

### 是否开启 Plan Mode

先开 Plan Mode 设计检索链路，然后执行。

### 模型要求

高。推荐 `opusplan` 设计，`sonnet` 实现。

### 使用 Skill

如果已创建，使用 `fastapi-rag-backend` Skill。

### 给 Claude 的文件

```text
@backend/services/rag_service.py
@backend/routers/rag.py
@backend/schemas.py
@backend/prompts/rag_answer.txt
@docs/plans/最终执行方案设计.md
```

### 提示词：Plan 阶段

```text
请只读分析当前项目，设计 RAG Pipeline，不要改文件。

必须符合赛题：
1. chunk_size 500-800 字，建议 600
2. overlap 50-100 字，建议 80
3. 每个 chunk 保留 textbook、chapter、page_start、page_end、content
4. 检索 top-5
5. 回答必须带 [教材名, 章节, 第X页]
6. 找不到答案时回复“当前知识库中未找到相关信息”
7. 如果 FAISS/embedding 不可用，要有 BM25/关键词兜底

请输出实现计划和接口返回结构。
```

### 提示词：实现阶段

```text
请实现 RAG 模块。

要求：
1. /api/rag/index 对已解析教材建立索引
2. chunk_size=600，overlap=80
3. 每个 chunk 保存教材名、章节、页码、内容
4. 如果 sentence-transformers/FAISS 可用，用向量检索
5. 如果不可用，使用简单 BM25/关键词检索兜底
6. /api/rag/status 返回 indexed_books、chunk_count、status
7. /api/rag/query 输入 question，返回 answer、citations、source_chunks
8. answer 必须只基于 source_chunks
9. citations 至少包含 textbook、chapter、page、relevance_score
10. 点击引用可展开原文 chunk，因此 source_chunks 必须返回 content
11. LLM Prompt 放在 backend/prompts/rag_answer.txt
12. 无 LLM_API_KEY 时，返回基于 top chunk 的 extractive answer 兜底
```

### 产出

```text
RAG 精准问答能力。
```

### API 模型能力要求

```text
中高。
RAG 生成模型不一定要最强，但必须指令遵循稳定，能严格引用来源，不乱编。
真正影响引用准确率的是 chunk 元数据和检索质量。
```

---

## Step 10：实现教师反馈对话

### 是否开启 Plan Mode

不开，除非要设计复杂状态机。

### 模型要求

低到中等。

### 给 Claude 的文件

```text
@backend/services/feedback_service.py
@backend/routers/chat.py
@frontend/src/components/ChatPanel.tsx
@frontend/src/components/IntegrationPanel.tsx
```

### 提示词

```text
请实现教师反馈对话模块。

要求：
1. 前端提供聊天输入框和历史消息
2. 后端 /api/chat 接收 message
3. 先使用规则解析：
   - 包含“为什么” -> explain
   - 包含“保留” -> keep
   - 包含“删除” -> remove
   - 包含“合并” -> merge
   - 包含“分开/拆开/不应该合并” -> split
4. 支持至少 keep 和 split 修改真实决策状态
5. 修改后 updated_decisions 返回给前端
6. 前端刷新整合决策列表和图谱
7. 同一会话保存 chat_history 到内存或 JSON
8. 不要实现复杂自由聊天
```

### 产出

```text
教师能通过自然语言修改至少一项整合决策。
```

### API 模型能力要求

```text
低。
规则解析足够覆盖验收。LLM 可选，不要把这一步做成依赖强模型的功能。
```

---

## Step 11：实现报告生成与文档

### 是否开启 Plan Mode

文档结构可开 Plan Mode；实际写文件切回普通模式。

### 模型要求

Agent 架构说明需要较强模型；README 和普通报告用 Sonnet 即可。

### 使用 Skill

使用 `scoring-docs-writer` Skill。

### 给 Claude 的文件

```text
@docs/plans/最终执行方案设计.md
@backend/
@frontend/
@README.md
```

### 提示词

```text
请生成比赛要求的文档。

必须创建或补全：
1. README.md
2. docs/需求分析.md
3. docs/系统设计.md
4. docs/Agent架构说明.md
5. report/整合报告.md

要求：
- README 包含项目简介、技术栈、环境依赖、安装步骤、配置说明、启动命令、使用流程、部署说明
- 需求分析覆盖知识点粒度、重复判定标准、压缩比计算方式、教学连贯性保障、RAG 分块依据
- 系统设计包含架构图、数据流、API 一览、技术选型理由
- Agent 架构说明重点论证：为什么选择单主控 Orchestrator + 多工具模块，为什么不做复杂多 Agent
- 整合报告包含：整合概览、决策摘要、图谱统计、3-5 个重点案例、教学完整性说明
- 文档要与当前代码实际功能一致，不要夸大未实现功能
```

### 产出

```text
评分文档齐全。
```

### API 模型能力要求

```text
文档生成无所谓强模型，但 Agent 架构说明最好用强模型润色一次，因为 D 维度 20 分很关键。
```

---

## Step 12：部署前代码审查与 P0 检查

### 是否开启 Plan Mode

必须开启。

### 模型要求

中高。`sonnet` 足够，若时间足够用 `opusplan`。

### 使用命令

```text
/p0-check
/api-check
/docs-score
/demo-check
/review
```

### 提示词

```text
请进入只读审查模式，不要修改文件。
根据赛题 P0 和 @docs/plans/最终执行方案设计.md 检查当前项目。

重点检查：
1. 上传/解析是否可演示
2. 图谱是否有 nodes/edges 和点击详情
3. 整合是否有 merge/keep/remove 和压缩比 <= 30%
4. RAG 是否有引用来源
5. 教师对话是否能修改决策
6. README/docs/report 是否齐全
7. .gitignore 是否排除 PDF、.env、上传目录、向量目录
8. 是否存在会导致部署失败的问题

输出：
- 立即必须修复的问题
- 可以接受的风险
- 演示时应避开的坑
```

### 产出

```text
最后修复清单。
```

---

## Step 13：最终部署与演示脚本

### 是否开启 Plan Mode

部署前检查用 Plan Mode，实际部署命令不用。

### 模型要求

普通。

### 给 Claude 的文件

```text
@README.md
@package.json
@requirements.txt
@frontend/package.json
@backend/main.py
@.env.example
```

### 提示词

```text
请根据当前项目生成最终部署与演示检查清单。

要求：
1. 输出本地启动命令
2. 输出线上部署前的环境变量清单
3. 输出 GitHub 提交前检查清单
4. 输出 8 分钟现场演示脚本
5. 确认不要提交 PDF、.env、上传目录、向量索引
6. 不要执行 git push，只给命令建议
```

### 产出

```text
部署检查清单与演示脚本。
```

---

## 7. Runtime API 模型能力要求表

这里说的是“项目运行时调用的 LLM/API 模型”，不是 Claude Code 自己的模型。

| 功能 | 是否依赖强模型 | 推荐能力 | 可降级方案 |
|---|---|---|---|
| 知识点抽取 | 高 | 中文教材理解、结构化 JSON、关系抽取 | 规则抽取 mock 节点 |
| 跨教材合并判断 | 很高 | 概念辨析、同义/上下位/相关关系区分 | 高阈值 embedding + 教师反馈 |
| RAG 回答 | 中高 | 指令遵循、引用格式稳定、防幻觉 | extractive answer：直接拼 top chunk |
| 教师反馈解析 | 低 | 意图分类 | 关键词规则解析 |
| 报告生成 | 中低 | 总结与格式化 | 模板填充 |
| Prompt repair | 中 | JSON 修复 | 直接兜底 |
| 前端/后端普通逻辑 | 不需要 | 无 | 不调用 LLM |

推荐模型分配：

```text
知识抽取：强模型
合并判断：强模型或不用 LLM
RAG 生成：中强模型
教师反馈：弱模型或规则
报告：普通模型
```

如果预算或额度紧张，优先保障：

```text
1. RAG 引用稳定
2. 知识点抽取能出 JSON
3. 合并决策有 reason
```

---

## 8. Claude Code 自身模型要求表

| Claude Code 阶段 | 推荐模型 | 是否必须强模型 | 原因 |
|---|---|---|---|
| 总体架构与排期 | `opusplan` / `opus` | 是 | 涉及取舍与评分策略 |
| 后端骨架 | `sonnet` | 否 | 常规工程实现 |
| PDF 解析 | `sonnet` | 否 | 主要是库使用和兜底 |
| LLM Prompt + schema | `opusplan` 规划 + `sonnet` 实现 | 是/部分 | 输出稳定性影响后续 |
| 跨教材整合算法 | `opusplan` / `opus` 规划 | 是 | 容易误合并，需强判断 |
| RAG Pipeline | `opusplan` 规划 + `sonnet` 实现 | 是/部分 | 引用准确性是硬指标 |
| ECharts 前端 | `sonnet` | 否 | 普通 UI 实现 |
| 教师反馈规则 | `sonnet` / `haiku` | 否 | 关键词规则足够 |
| README | `sonnet` / `haiku` | 否 | 模板文档 |
| Agent 架构说明 | `opus` / `sonnet` | 建议强 | 评分 20 分，值得用强模型 |
| 最终代码审查 | `sonnet` 或 `opusplan` | 建议中高 | 避免漏 P0 |

---

## 9. 每一步是否需要 Skill / Plan Mode / Subagent

| 步骤 | Plan Mode | Skill | Subagent | 说明 |
|---|---|---|---|---|
| Step 1 架构确认 | 必须 | 不必 | 不必 | 先只读规划 |
| Step 2 项目骨架 | 短暂 | `hackathon-p0-executor` 可选 | 不必 | 确认目录后直接写 |
| Step 3 API 骨架 | 不必 | `fastapi-rag-backend` 可选 | 不必 | 普通实现 |
| Step 4 上传解析 | 不必 | `fastapi-rag-backend` 可选 | 不必 | 注意 PDF 逐页 |
| Step 5 前端布局 | 不必 | `echarts-graph-frontend` 可选 | 不必 | 快速实现 |
| Step 6 知识抽取 | 建议 | `fastapi-rag-backend` 推荐 | 不必 | Prompt/schema 高风险 |
| Step 7 图谱前端 | 不必 | `echarts-graph-frontend` 推荐 | 不必 | UI 任务 |
| Step 8 跨教材整合 | 必须 | `hackathon-p0-executor` 可选 | 不必 | 核心难点 |
| Step 9 RAG | 必须 | `fastapi-rag-backend` 推荐 | 不必 | 引用硬指标 |
| Step 10 教师反馈 | 不必 | 不必 | 不必 | 规则优先 |
| Step 11 文档 | 建议 | `scoring-docs-writer` 推荐 | `docs-scorer` 可选 | 文档拿分 |
| Step 12 代码审查 | 必须 | `/p0-check` 推荐 | reviewer 可选 | 只读检查 |
| Step 13 部署 | 短暂 | `/demo-check` 推荐 | 不必 | 避免误操作 |

---

## 10. 提示词总表

比赛时可以直接复制下面这些短提示。

### 10.1 规划提示词

```text
请开启只读规划。基于 @docs/plans/最终执行方案设计.md，输出 5 小时内 P0 全覆盖的开发顺序、文件结构、接口列表和风险兜底。不要修改文件。
```

### 10.2 后端实现提示词

```text
请实现当前阶段的 FastAPI 后端模块。要求：Pydantic schema、router/service 分离、错误处理、mock/兜底可用、接口响应稳定。不要引入复杂依赖，不要读取 .env 或 PDF 数据。
```

### 10.3 前端实现提示词

```text
请实现 React + TypeScript 前端模块。要求：三栏 SPA、接口调用稳定、错误状态可见、演示优先、不要复杂状态库、不要花哨动效。
```

### 10.4 图谱提示词

```text
请用 ECharts graph 实现知识图谱。节点颜色表示教材来源，节点大小表示频次，支持缩放、拖拽、点击详情和搜索高亮。
```

### 10.5 整合提示词

```text
请实现跨教材整合：embedding/字符串相似度对齐、merge/keep/remove 决策、reason/confidence、压缩比 <=30%、整合前后图谱切换。优先避免误合并。
```

### 10.6 RAG 提示词

```text
请实现 RAG：600 字 chunk、80 字 overlap、保留教材/章节/页码元数据、top-5 检索、答案带 citations、source_chunks 可展开，找不到答案时返回“当前知识库中未找到相关信息”。
```

### 10.7 教师反馈提示词

```text
请实现教师反馈：explain/keep/remove/merge/split 五类意图，规则解析优先，至少支持 keep 和 split 修改决策并刷新前端状态。
```

### 10.8 文档提示词

```text
请根据当前代码和 @docs/plans/最终执行方案设计.md 补齐 README、需求分析、系统设计、Agent架构说明、整合报告。不要夸大未实现功能，必须映射评分标准。
```

### 10.9 审查提示词

```text
请只读审查当前项目是否满足 P0。输出缺失项、风险项、30 分钟内优先修复项、演示时避坑提示。不要改文件。
```

---

## 11. 开发节奏建议

### 11.1 单人节奏

```text
0-20 min：骨架
20-60 min：上传解析
60-110 min：知识抽取 + 图谱
110-155 min：整合 + 压缩比
155-205 min：RAG
205-225 min：教师反馈
225-260 min：文档
260-285 min：部署
285-300 min：彩排
```

Claude Code 用法：

```text
每个阶段只发一个明确任务
不要让 Claude 同时做后端、前端、文档、部署
每完成一个阶段就运行 build/test
每完成两个阶段就 /compact
```

### 11.2 两人节奏

| 人员 | Claude Code 任务 | 备注 |
|---|---|---|
| A | 后端、RAG、整合 | 用强模型做核心算法 |
| B | 前端、文档、部署 | 用 Sonnet 足够 |

避免两个人同时让 Claude 改同一个文件。

### 11.3 三人节奏

| 人员 | 负责 | Claude Code 建议 |
|---|---|---|
| A | 后端核心 | 强模型规划，Sonnet 写代码 |
| B | 前端展示 | Sonnet 快速 UI |
| C | 文档/部署/评分 | `/docs-score`、`/demo-check` |

---

## 12. 常见错误与纠正提示词

### 错误 1：Claude 想做复杂多 Agent

纠正提示：

```text
不要实现复杂多 Agent 框架。本项目只采用单主控 Orchestrator + 多工具模块。请删除 LangGraph/CrewAI/AutoGen 的实现计划，只保留文档中的架构论证。
```

### 错误 2：Claude 想做 OCR

```text
不要做 OCR。扫描件 PDF 可以提示“不支持扫描版解析”。当前优先 PyMuPDF 逐页文本解析和章节兜底。
```

### 错误 3：Claude 忘记压缩比口径

```text
压缩比不是节点数。请按 compressed_chars / original_chars * 100 计算，目标 <= 30%。compressed_chars 由合并后定义、关系说明和代表性 source_quote/chunk 组成。
```

### 错误 4：RAG 没有引用

```text
请修复 RAG：每个 source chunk 必须携带 textbook/chapter/page，answer 必须包含 citations，引用格式为 [教材名, 章节, 第X页]。
```

### 错误 5：前端只显示 mock，不接后端

```text
请把前端组件改为调用真实 API。mock 只允许作为后端无数据时的 fallback，不能替代真实流程。
```

### 错误 6：文档写了未实现功能

```text
请重新检查当前代码，只写已经实现或明确作为未来工作的内容，不要把未实现功能写成已完成。
```

---

## 13. 最后 30 分钟 Claude Code 检查清单

最后 30 分钟不要再大改架构，只做检查和小修。

运行：

```text
/p0-check
/api-check
/docs-score
/demo-check
```

必须确认：

```text
[ ] README 存在且能指导运行
[ ] docs/需求分析.md 存在
[ ] docs/系统设计.md 存在
[ ] docs/Agent架构说明.md 存在
[ ] report/整合报告.md 存在
[ ] .gitignore 排除 *.pdf、.env、uploads、vectors
[ ] 前端能打开
[ ] 上传接口可用
[ ] 解析后有 chapters[]
[ ] 图谱有节点和边
[ ] 节点点击有详情
[ ] 整合有 merge/keep/remove
[ ] 压缩比 <= 30%
[ ] RAG 有 citations
[ ] 教师反馈能改决策
[ ] 公网部署链接可访问
[ ] GitHub 仓库 public
```

---

## 14. 推荐给 Claude Code 的最终演示脚本提示词

```text
请根据当前项目生成 8 分钟比赛演示脚本。

脚本必须覆盖：
1. 项目一句话介绍
2. 上传教材并展示解析状态
3. 展示章节树
4. 生成知识图谱并点击节点
5. 展示跨教材整合决策和压缩比
6. RAG 提问并展示引用来源
7. 教师对话修改一项决策
8. 展示整合报告和 README/docs
9. 最后强调 P0 覆盖、Agent 架构、RAG 引用、防幻觉、教师可控

请输出逐句讲稿和操作顺序。
```

---

## 15. 总结

Claude Code 在这个项目中的最佳用法是：

```text
用 Plan Mode 做少量关键决策
用 CLAUDE.md 固化项目规则
用 Custom Commands 做 P0/文档/演示检查
用 Skills 固化重复的后端、前端、文档工作流
用 Subagents 做最后 review，不用它们承担核心实现
用强模型处理架构、整合、RAG；普通模型处理 UI、文档、常规代码
```

最终目标不是让 Claude Code “自己全自动完成项目”，而是让它在明确边界内快速产出可演示工程。比赛中必须始终回到赛题：

```text
功能闭环 > 算法完美
可演示 > 可研究
P0 全覆盖 > P1 炫技
引用准确 > 回答华丽
文档论证 > 工具堆砌
```

---

## 参考依据

- 官方赛题文档：《AI 全栈极速黑客松·赛题文档》
- Claude Code 官方文档：Overview、Getting Started、Interactive Mode、Common Workflows、Slash Commands、Subagents、Settings、Memory、Model Configuration、Agent Skills
- 已整理方案：`docs/plans/最终执行方案设计.md`
