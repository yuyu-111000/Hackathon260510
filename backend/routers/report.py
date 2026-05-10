from fastapi import APIRouter
from backend.schemas import ReportResponse
from backend.services.report_service import ReportService
import os
from backend import config

router = APIRouter()
_report_service = ReportService()


@router.get("", response_model=ReportResponse)
async def get_report():
    report_path = os.path.join(config.REPORTS_DIR, "report.md")
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read()
        return ReportResponse(content=content)
    return ReportResponse(content="报告尚未生成。请先运行整合分析。")


@router.post("/generate", response_model=ReportResponse)
async def generate_report():
    from backend.routers.integration import _decisions, _stats
    from backend.routers.graph import get_current_graph

    graph = get_current_graph()

    if _decisions and _stats and _stats.original_node_count > 0:
        report = _report_service.generate(decisions=_decisions, stats=_stats, graph=graph)
    elif graph.nodes:
        report = _report_service.generate_single(graph)
    else:
        return ReportResponse(content="暂无数据。请先上传教材、解析并构建知识图谱。")

    report_path = os.path.join(config.REPORTS_DIR, "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    root_report = os.path.join(os.path.dirname(os.path.dirname(__file__)), "report", "整合报告.md")
    os.makedirs(os.path.dirname(root_report), exist_ok=True)
    with open(root_report, "w", encoding="utf-8") as f:
        f.write(report)

    return ReportResponse(content=report)
