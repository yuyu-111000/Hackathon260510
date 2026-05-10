from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from backend.routers import textbooks, graph, integration, rag, chat, report
from backend.schemas import HealthResponse

app = FastAPI(
    title="EduFusion Agent",
    description="学科知识整合智能体 - 多教材知识融合、图谱可视化与RAG问答系统",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(textbooks.router, prefix="/api/textbooks", tags=["教材管理"])
app.include_router(graph.router, prefix="/api/graph", tags=["知识图谱"])
app.include_router(integration.router, prefix="/api/integration", tags=["跨教材整合"])
app.include_router(rag.router, prefix="/api/rag", tags=["RAG问答"])
app.include_router(chat.router, prefix="/api/chat", tags=["教师反馈"])
app.include_router(report.router, prefix="/api/report", tags=["整合报告"])


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", version="1.0.0")


@app.get("/api/health", response_model=HealthResponse)
async def api_health():
    return HealthResponse(status="ok", version="1.0.0")
