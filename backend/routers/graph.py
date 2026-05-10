from fastapi import APIRouter, HTTPException
from backend.schemas import GraphResponse, KnowledgeNode, KnowledgeEdge
import os
import json
import asyncio
from backend import config

router = APIRouter()

_current_graph = GraphResponse()
_merged_graph = GraphResponse()


def _load_existing_graph():
    """Load previously built graph from storage on startup."""
    graph_path = os.path.join(config.GRAPHS_DIR, "graph.json")
    if not os.path.exists(graph_path):
        return
    try:
        with open(graph_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        global _current_graph
        _current_graph = GraphResponse(**data)
    except Exception:
        pass


_load_existing_graph()


@router.post("/build", response_model=GraphResponse)
async def build_graph(textbook_id: str = ""):
    global _current_graph

    parsed_files = []
    if textbook_id:
        path = os.path.join(config.PARSED_DIR, f"{textbook_id}.json")
        if os.path.exists(path):
            parsed_files.append(path)
    else:
        if os.path.exists(config.PARSED_DIR):
            for f in os.listdir(config.PARSED_DIR):
                if f.endswith(".json"):
                    parsed_files.append(os.path.join(config.PARSED_DIR, f))

    if not parsed_files:
        raise HTTPException(404, "No parsed textbooks found. Parse a textbook first.")

    all_nodes = []
    all_edges = []

    for pf in parsed_files:
        with open(pf, "r", encoding="utf-8") as f:
            textbook = json.load(f)

        from backend.services.extraction_service import extract_knowledge
        nodes, edges = await asyncio.to_thread(extract_knowledge, textbook)
        all_nodes.extend(nodes)
        all_edges.extend(edges)

    _current_graph = GraphResponse(nodes=all_nodes, edges=all_edges)

    graph_path = os.path.join(config.GRAPHS_DIR, "graph.json")
    with open(graph_path, "w", encoding="utf-8") as f:
        f.write(_current_graph.model_dump_json(indent=2))

    return _current_graph


@router.get("", response_model=GraphResponse)
async def get_graph():
    return _current_graph


@router.get("/merged", response_model=GraphResponse)
async def get_merged_graph():
    return _merged_graph


def set_merged_graph(graph: GraphResponse):
    global _merged_graph
    _merged_graph = graph


def get_current_graph() -> GraphResponse:
    return _current_graph


def set_current_graph(graph: GraphResponse):
    global _current_graph
    _current_graph = graph
