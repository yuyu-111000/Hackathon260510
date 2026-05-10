import math
from collections import defaultdict
from backend.schemas import (
    KnowledgeNode, KnowledgeEdge, MergeDecision, DecisionAction,
    GraphResponse, IntegrationStats, NodeStatus, RelationType
)
from backend import config


def align_and_merge(graph: GraphResponse, original_total_chars: int = 0) -> tuple[list[MergeDecision], GraphResponse, IntegrationStats]:
    """Cross-textbook knowledge alignment and deduplication pipeline.

    Pipeline: compute pairwise similarities → Union-Find clustering → generate
    merge decisions → rebuild edges → auto-trim if compression > 30%.

    Args:
        graph: Raw knowledge graph with nodes from multiple textbooks.
        original_total_chars: Total characters in source textbooks for compression calc.

    Returns:
        Tuple of (MergeDecision list, merged GraphResponse, IntegrationStats).
        Falls back to difflib if sentence-transformers is unavailable.
    """
    nodes = graph.nodes
    edges = graph.edges

    if not nodes:
        return [], GraphResponse(), IntegrationStats()

    text_pairs = [(n, f"{n.name} {n.definition}") for n in nodes]
    similarities = _compute_similarities(text_pairs)

    clusters = _build_clusters(nodes, similarities)

    decisions, merged_nodes = _generate_decisions(clusters, nodes, similarities)

    merged_edges = _rebuild_edges(edges, decisions, merged_nodes)

    merged_graph = GraphResponse(nodes=merged_nodes, edges=merged_edges)

    stats = _compute_stats(nodes, merged_nodes, decisions, original_total_chars)

    return decisions, merged_graph, stats


def _compute_similarities(text_pairs: list[tuple[KnowledgeNode, str]]) -> dict[tuple[str, str], float]:
    similarities = {}

    try:
        import numpy as np
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(config.EMBEDDING_MODEL, device=config.EMBEDDING_DEVICE)
        texts = [t for _, t in text_pairs]
        embeddings = model.encode(texts, normalize_embeddings=True)

        for i in range(len(text_pairs)):
            for j in range(i + 1, len(text_pairs)):
                sim = float(np.dot(embeddings[i], embeddings[j]))
                id_i = text_pairs[i][0].id
                id_j = text_pairs[j][0].id
                similarities[(id_i, id_j)] = sim
                similarities[(id_j, id_i)] = sim

    except Exception:
        import difflib
        for i in range(len(text_pairs)):
            for j in range(i + 1, len(text_pairs)):
                node_i, text_i = text_pairs[i]
                node_j, text_j = text_pairs[j]

                name_sim = difflib.SequenceMatcher(None, node_i.name, node_j.name).ratio()
                def_sim = difflib.SequenceMatcher(None, node_i.definition, node_j.definition).ratio()
                sim = 0.6 * name_sim + 0.4 * def_sim

                similarities[(node_i.id, node_j.id)] = sim
                similarities[(node_j.id, node_i.id)] = sim

    return similarities


class UnionFind:
    def __init__(self):
        self.parent = {}
        self.rank = {}

    def find(self, x):
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x] = 0
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x, y):
        px, py = self.find(x), self.find(y)
        if px == py:
            return
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1


def _build_clusters(
    nodes: list[KnowledgeNode],
    similarities: dict[tuple[str, str], float],
) -> list[list[str]]:
    uf = UnionFind()

    for n in nodes:
        uf.find(n.id)

    node_map = {n.id: n for n in nodes}

    for (id_a, id_b), sim in similarities.items():
        if id_a >= id_b:
            continue

        name_a = node_map[id_a].name.lower().strip()
        name_b = node_map[id_b].name.lower().strip()

        if name_a == name_b or name_a in node_map[id_b].aliases or name_b in node_map[id_a].aliases:
            uf.union(id_a, id_b)
            continue

        if sim >= config.MERGE_THRESHOLD_HIGH:
            uf.union(id_a, id_b)
        elif sim >= config.MERGE_THRESHOLD_LOW:
            if config.LLM_API_KEY:
                is_same = _llm_judge(node_map[id_a], node_map[id_b], sim)
                if is_same:
                    uf.union(id_a, id_b)

    clusters_map = defaultdict(list)
    for n in nodes:
        root = uf.find(n.id)
        clusters_map[root].append(n.id)

    return [c for c in clusters_map.values() if len(c) >= 1]


def _llm_judge(node_a: KnowledgeNode, node_b: KnowledgeNode, sim: float) -> bool:
    try:
        from openai import OpenAI
        client = OpenAI(base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY)

        prompt = f"""你是跨教材知识点对齐专家。请判断两个知识点是否表示同一概念。

判断原则：
1. 同义词、中英文术语、不同表达但定义等价，可以合并。
2. 上下位概念不能合并。
3. 应用场景相同但概念不同，不能合并。
4. 只输出 JSON。

知识点A：{node_a.name}
定义A：{node_a.definition}
教材A：{node_a.textbook_id}

知识点B：{node_b.name}
定义B：{node_b.definition}
教材B：{node_b.textbook_id}

向量相似度：{sim}

输出：{{"equivalent": true/false, "reason": "..."}}"""

        response = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=config.LLM_MAX_TOKENS,
        )

        import json
        raw = response.choices[0].message.content or "{}"
        raw = raw.strip()
        if raw.startswith("```"):
            import re
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

        result = json.loads(raw)
        return result.get("equivalent", False)

    except Exception:
        return False


def _generate_decisions(
    clusters: list[list[str]],
    all_nodes: list[KnowledgeNode],
    similarities: dict[tuple[str, str], float],
) -> tuple[list[MergeDecision], list[KnowledgeNode]]:

    node_map = {n.id: n for n in all_nodes}
    decisions = []
    merged_nodes = []
    absorbed = set()

    for i, cluster in enumerate(clusters):
        cluster_nodes = [node_map[nid] for nid in cluster if nid in node_map]

        if len(cluster_nodes) == 1:
            node = cluster_nodes[0]
            decisions.append(MergeDecision(
                decision_id=f"keep_{i:03d}",
                action=DecisionAction.KEEP,
                affected_nodes=[node.id],
                result_node=node.id,
                reason="该知识点在教材中独立存在",
                confidence=1.0,
                status="active",
            ))
            merged_nodes.append(node)
            continue

        canonical = _pick_canonical(cluster_nodes)
        to_merge = [n for n in cluster_nodes if n.id != canonical.id]

        merged_aliases = []
        for n in cluster_nodes:
            merged_aliases.append(n.name)
            merged_aliases.extend(n.aliases)
        merged_aliases = list(set(merged_aliases))

        merged_node = KnowledgeNode(
            id=f"merged_{i:03d}",
            textbook_id=canonical.textbook_id,
            name=canonical.name,
            aliases=merged_aliases,
            definition=canonical.definition,
            category=canonical.category,
            chapter=canonical.chapter,
            page=canonical.page,
            source_quote=canonical.source_quote,
            frequency=sum(n.frequency for n in cluster_nodes),
            status=NodeStatus.MERGED,
        )
        merged_nodes.append(merged_node)

        decisions.append(MergeDecision(
            decision_id=f"merge_{i:03d}",
            action=DecisionAction.MERGE,
            affected_nodes=[n.id for n in cluster_nodes],
            result_node=merged_node.id,
            reason=f"多个教材中的'{canonical.name}'描述同一概念，保留最完整版本",
            confidence=0.9,
            status="active",
        ))

        for n in to_merge:
            absorbed.add(n.id)
            decisions.append(MergeDecision(
                decision_id=f"remove_{i:03d}_{n.id}",
                action=DecisionAction.REMOVE,
                affected_nodes=[n.id],
                result_node=merged_node.id,
                reason=f"与{canonical.name}合并",
                confidence=0.9,
                status="active",
            ))

    return decisions, merged_nodes


def _pick_canonical(nodes: list[KnowledgeNode]) -> KnowledgeNode:
    def score(n: KnowledgeNode) -> float:
        return (
            len(n.definition) * 0.4 +
            len(n.source_quote) * 0.2 +
            n.frequency * 100 * 0.2 +
            len(n.aliases) * 50 * 0.2
        )
    return max(nodes, key=score)


def _rebuild_edges(
    original_edges: list[KnowledgeEdge],
    decisions: list[MergeDecision],
    merged_nodes: list[KnowledgeNode],
) -> list[KnowledgeEdge]:

    id_mapping = {}
    for d in decisions:
        if d.action == DecisionAction.MERGE and d.result_node:
            for nid in d.affected_nodes:
                id_mapping[nid] = d.result_node
        elif d.action == DecisionAction.REMOVE and d.result_node:
            for nid in d.affected_nodes:
                id_mapping[nid] = d.result_node

    valid_ids = {n.id for n in merged_nodes}
    new_edges = []
    seen = set()

    for e in original_edges:
        src = id_mapping.get(e.source, e.source)
        tgt = id_mapping.get(e.target, e.target)

        if src == tgt:
            continue
        if src not in valid_ids or tgt not in valid_ids:
            continue

        key = (src, tgt, e.relation_type)
        if key in seen:
            continue
        seen.add(key)

        new_edges.append(KnowledgeEdge(
            source=src,
            target=tgt,
            relation_type=e.relation_type,
            description=e.description,
            textbook_id=e.textbook_id,
        ))

    return new_edges


def _compute_stats(
    original: list[KnowledgeNode],
    merged: list[KnowledgeNode],
    decisions: list[MergeDecision],
    original_total_chars: int = 0,
) -> IntegrationStats:

    # If original_total_chars provided from parsed textbooks, use it as denominator
    # Otherwise fall back to node-level counting
    if original_total_chars > 0:
        original_chars = original_total_chars
    else:
        original_chars = sum(len(n.definition) + len(n.source_quote) for n in original)

    compressed_chars = sum(len(n.definition) + len(n.source_quote) for n in merged)

    ratio = (compressed_chars / original_chars * 100) if original_chars > 0 else 0.0

    # Auto-trim if compression ratio exceeds 30%
    if ratio > 30.0 and original_chars > 0:
        merged, compressed_chars = _auto_trim(merged, original_chars)
        ratio = (compressed_chars / original_chars * 100) if original_chars > 0 else 0.0

    merge_count = sum(1 for d in decisions if d.action == DecisionAction.MERGE)
    keep_count = sum(1 for d in decisions if d.action == DecisionAction.KEEP)
    remove_count = sum(1 for d in decisions if d.action == DecisionAction.REMOVE)

    return IntegrationStats(
        original_total_chars=original_chars,
        compressed_chars=compressed_chars,
        compression_ratio=round(ratio, 2),
        original_node_count=len(original),
        merged_node_count=len(merged),
        merge_count=merge_count,
        keep_count=keep_count,
        remove_count=remove_count,
    )


def _auto_trim(nodes: list[KnowledgeNode], target_chars: int) -> tuple[list[KnowledgeNode], int]:
    """Trim definitions and source_quotes to meet ≤30% compression target.
    Deep-copies nodes to avoid mutating the originals."""
    import copy
    target = int(target_chars * 0.28)  # Aim for 28% to have margin

    # Deep copy to avoid mutating original nodes
    trimmed = [copy.deepcopy(n) for n in nodes]

    # Sort by frequency (ascending) — trim low-frequency nodes first
    sorted_nodes = sorted(trimmed, key=lambda n: n.frequency)

    current = sum(len(n.definition) + len(n.source_quote) for n in trimmed)

    # Pass 1: Shorten definitions to 120 chars for low-frequency nodes
    for n in sorted_nodes:
        if current <= target:
            break
        if len(n.definition) > 120:
            saved = len(n.definition) - 120
            n.definition = n.definition[:117] + "..."
            current -= saved

    # Pass 2: Remove source_quotes from low-frequency nodes
    for n in sorted_nodes:
        if current <= target:
            break
        if n.source_quote and n.frequency <= 1:
            saved = len(n.source_quote)
            n.source_quote = ""
            current -= saved

    # Pass 3: Shorten remaining definitions to 80 chars
    for n in sorted_nodes:
        if current <= target:
            break
        if len(n.definition) > 80:
            saved = len(n.definition) - 80
            n.definition = n.definition[:77] + "..."
            current -= saved

    return trimmed, current
