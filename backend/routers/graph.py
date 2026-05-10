from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from backend.schemas import GraphResponse, KnowledgeNode, KnowledgeEdge, RelationType
import os
import json
from collections import defaultdict, deque
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
def build_graph(textbook_id: str = ""):
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
        nodes, edges = extract_knowledge(textbook)
        all_nodes.extend(nodes)
        all_edges.extend(edges)

    _current_graph = GraphResponse(nodes=all_nodes, edges=all_edges)

    graph_path = os.path.join(config.GRAPHS_DIR, "graph.json")
    with open(graph_path, "w", encoding="utf-8") as f:
        f.write(_current_graph.model_dump_json(indent=2))

    return _current_graph


@router.post("/build-stream")
def build_graph_stream(textbook_id: str = ""):
    """SSE endpoint for streaming graph build progress."""
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
        raise HTTPException(404, "No parsed textbooks found.")

    def event_stream():
        global _current_graph
        all_nodes = []
        all_edges = []

        for pf in parsed_files:
            with open(pf, "r", encoding="utf-8") as f:
                textbook = json.load(f)

            from backend.services.extraction_service import extract_knowledge_stream
            for event in extract_knowledge_stream(textbook):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                if event["type"] == "complete":
                    nodes_data = event.get("nodes", [])
                    edges_data = event.get("edges", [])
                    for n in nodes_data:
                        try:
                            all_nodes.append(KnowledgeNode(**n))
                        except Exception:
                            pass
                    for e in edges_data:
                        try:
                            all_edges.append(KnowledgeEdge(**e))
                        except Exception:
                            pass

        _current_graph = GraphResponse(nodes=all_nodes, edges=all_edges)

        graph_path = os.path.join(config.GRAPHS_DIR, "graph.json")
        with open(graph_path, "w", encoding="utf-8") as f:
            f.write(_current_graph.model_dump_json(indent=2))

        yield f'data: {json.dumps({"type": "done", "total_nodes": len(all_nodes), "total_edges": len(all_edges)}, ensure_ascii=False)}\n\n'

    return StreamingResponse(event_stream(), media_type="text/event-stream")


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


@router.get("/learning-path")
def get_learning_path():
    """Generate learning path via topological sort on prerequisite edges.

    Nodes with no prerequisites come first. Nodes connected by prerequisite
    edges are ordered so learners master foundations before advanced topics.
    """
    graph = _merged_graph if _merged_graph.nodes else _current_graph
    if not graph.nodes:
        raise HTTPException(404, "No graph data. Build graph first.")

    node_map = {n.id: n for n in graph.nodes}

    # Build adjacency and in-degree
    adj: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = {n.id: 0 for n in graph.nodes}

    for e in graph.edges:
        if e.relation_type == RelationType.PREREQUISITE:
            if e.source in node_map and e.target in node_map:
                adj[e.source].append(e.target)
                in_degree[e.target] = in_degree.get(e.target, 0) + 1

    # Kahn's algorithm for topological sort
    queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
    order = []

    while queue:
        curr = queue.popleft()
        order.append(curr)
        for neighbor in adj.get(curr, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # Nodes not reached by prerequisite edges — append at end
    reached = set(order)
    for nid in node_map:
        if nid not in reached:
            order.append(nid)

    paths = []
    for i, nid in enumerate(order):
        node = node_map.get(nid)
        if not node:
            continue
        prereqs = [
            e.source for e in graph.edges
            if e.target == nid and e.relation_type == RelationType.PREREQUISITE
        ]
        paths.append({
            "order": i + 1,
            "node_name": node.name,
            "node_id": node.id,
            "category": node.category,
            "prerequisites": prereqs,
        })

    return {
        "paths": paths,
        "total_steps": len(paths),
        "methodology": "拓扑排序 — 按前置依赖关系排列学习顺序，无前置依赖的基础概念优先",
    }
