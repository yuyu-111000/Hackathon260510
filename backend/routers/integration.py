from fastapi import APIRouter, HTTPException
from backend.schemas import (
    IntegrationRunResponse, MergeDecision, IntegrationStats,
    GraphResponse, DecisionAction
)
from backend.routers.graph import get_current_graph, set_merged_graph
import json
import os
from backend import config

router = APIRouter()

_decisions: list[MergeDecision] = []
_stats = IntegrationStats()


@router.post("/run", response_model=IntegrationRunResponse)
async def run_integration():
    global _decisions, _stats

    graph = get_current_graph()
    if not graph.nodes:
        raise HTTPException(400, "No graph data. Build graph first.")

    # Load original chapter content for accurate compression ratio
    import json
    original_total_chars = 0
    if os.path.exists(config.PARSED_DIR):
        for f in os.listdir(config.PARSED_DIR):
            if f.endswith(".json"):
                with open(os.path.join(config.PARSED_DIR, f), "r", encoding="utf-8") as fh:
                    tb = json.load(fh)
                    original_total_chars += tb.get("total_chars", 0)

    from backend.services.alignment_service import align_and_merge
    decisions, merged_graph, stats = align_and_merge(graph, original_total_chars)

    _decisions = decisions
    _stats = stats
    set_merged_graph(merged_graph)

    return IntegrationRunResponse(
        decisions=decisions,
        stats=stats,
        merged_graph=merged_graph,
    )


@router.get("/decisions", response_model=list[MergeDecision])
async def get_decisions():
    return _decisions


@router.patch("/decisions/{decision_id}", response_model=MergeDecision)
async def update_decision(decision_id: str, action: str = "keep"):
    global _decisions

    for d in _decisions:
        if d.decision_id == decision_id:
            try:
                d.action = DecisionAction(action)
            except ValueError:
                raise HTTPException(400, f"Invalid action: {action}")
            return d

    raise HTTPException(404, "Decision not found")
