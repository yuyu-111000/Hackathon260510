# EduFusion Agent - 学科知识整合智能体

## 项目简介

EduFusion 是一个**学科知识整合智能体**，能够自动解析多本教材、构建知识图谱、进行跨教材语义去重（压缩至原始内容的 ≤30%）、提供带引用的 RAG 问答、支持教师自然语言反馈修改整合决策，并生成整合报告。

## 核心功能

| 功能 | 描述 |
|------|------|
| 教材解析 | 支持 PDF/MD/TXT/DOCX 格式，自动章节检测 |
| 知识图谱 | ECharts 力导向图可视化，支持搜索高亮、拖拽、缩放、整合前后切换 |
| 跨教材整合 | 基于语义相似度的自动去重，Union-Find 聚类，压缩比自动控制 ≤30% |
| RAG 问答 | 向量检索 + 关键词混合召回，严格引用，检索指标 Benchmark |
| 教师反馈 | 自然语言指令修改整合决策（保留/删除/拆分/合并） |
| 整合报告 | 自动生成 Markdown 格式的整合报告 |

## 技术栈

- **后端**: FastAPI + Pydantic + PyMuPDF + sentence-transformers + FAISS
- **前端**: React + TypeScript + Vite + ECharts + Axios
- **LLM**: OpenAI 兼容接口（DeepSeek/Qwen 等）

## Docker 一键部署（推荐）

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 LLM_API_KEY

# 2. 一键启动
docker compose up -d

# 3. 访问
# 前端: http://localhost:5173
# API文档: http://localhost:8000/docs
```

## 快速开始

### 1. 安装依赖

```bash
# 后端
pip install -r requirements.txt

# 前端
cd frontend && npm install
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入 LLM API Key
```

### 3. 启动服务

```bash
# 后端 (端口 8000)
cd backend && python -m uvicorn main:app --reload --port 8000

# 前端 (端口 5173)
cd frontend && npm run dev
```

### 4. 访问

- 前端: http://localhost:5173
- API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

## 项目结构

```
D:\1Hackathon\
├── backend/
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py             # 配置管理
│   ├── schemas.py            # Pydantic 数据模型
│   ├── routers/              # API 路由
│   │   ├── textbooks.py      # 教材管理
│   │   ├── graph.py          # 知识图谱
│   │   ├── integration.py    # 跨教材整合
│   │   ├── rag.py            # RAG 问答
│   │   ├── chat.py           # 教师反馈
│   │   └── report.py         # 整合报告
│   ├── services/             # 业务逻辑
│   │   ├── parser_service.py # 教材解析
│   │   ├── extraction_service.py # 知识抽取
│   │   ├── alignment_service.py  # 跨教材对齐
│   │   ├── rag_service.py    # RAG 管线
│   │   ├── chat_service.py   # 对话处理
│   │   └── report_service.py # 报告生成
│   ├── prompts/              # LLM 提示词模板
│   └── storage/              # 数据存储
├── frontend/
│   ├── src/
│   │   ├── App.tsx           # 主应用（三栏布局）
│   │   ├── components/       # UI 组件
│   │   ├── api/client.ts     # API 客户端
│   │   └── types/index.ts    # TypeScript 类型
│   └── index.html
├── docs/                     # 项目文档
├── requirements.txt
├── .env.example
└── .gitignore
```

## API 接口

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/textbooks/upload | 上传教材 |
| GET | /api/textbooks | 教材列表 |
| POST | /api/textbooks/{id}/parse | 解析教材 |
| POST | /api/graph/build | 构建知识图谱 |
| GET | /api/graph | 获取图谱 |
| GET | /api/graph/merged | 获取整合后图谱 |
| POST | /api/integration/run | 运行整合 |
| GET | /api/integration/decisions | 获取决策列表 |
| PATCH | /api/integration/decisions/{id} | 修改决策 |
| POST | /api/rag/index | 构建 RAG 索引 |
| GET | /api/rag/status | RAG 状态 |
| POST | /api/rag/query | RAG 查询 |
| POST | /api/chat | 教师对话 |
| GET | /api/chat/history | 对话历史 |
| GET | /api/report | 获取报告 |
| POST | /api/report/generate | 生成报告 |

## License

MIT
