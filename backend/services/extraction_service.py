import json
import re
import os
import logging
from typing import Generator
from backend.schemas import KnowledgeNode, KnowledgeEdge, RelationType, NodeStatus
from backend import config

logger = logging.getLogger(__name__)

# Per-chapter LLM timeout in seconds
LLM_CHAPTER_TIMEOUT = 15


def extract_knowledge(textbook: dict) -> tuple[list[KnowledgeNode], list[KnowledgeEdge]]:
    book_id = textbook.get("textbook_id", "unknown")
    book_title = textbook.get("title", "未知教材")
    chapters = textbook.get("chapters", [])

    all_nodes = []
    all_edges = []

    for chapter in chapters:
        content = chapter.get("content", "")
        if len(content) < 50:
            continue

        try:
            nodes, edges = _extract_from_chapter(
                book_id=book_id,
                book_title=book_title,
                chapter_title=chapter.get("title", ""),
                page_start=chapter.get("page_start", 1),
                content=content[:5000],
            )
            all_nodes.extend(nodes)
            all_edges.extend(edges)
        except Exception as e:
            logger.warning(f"Extraction failed for {chapter.get('title', '?')}: {e}")

    return all_nodes, all_edges


def extract_knowledge_stream(textbook: dict) -> Generator[dict, None, None]:
    """Yield progress events as JSON dicts for SSE streaming."""
    book_id = textbook.get("textbook_id", "unknown")
    book_title = textbook.get("title", "未知教材")
    chapters = textbook.get("chapters", [])

    valid_chapters = [ch for ch in chapters if len(ch.get("content", "")) >= 50]
    total = len(valid_chapters)

    yield {"type": "start", "total_chapters": total, "book_title": book_title}

    all_nodes = []
    all_edges = []

    for i, chapter in enumerate(valid_chapters):
        content = chapter.get("content", "")
        ch_title = chapter.get("title", f"第{i+1}章")

        try:
            nodes, edges = _extract_from_chapter(
                book_id=book_id,
                book_title=book_title,
                chapter_title=ch_title,
                page_start=chapter.get("page_start", 1),
                content=content[:5000],
            )
            all_nodes.extend(nodes)
            all_edges.extend(edges)
            yield {
                "type": "progress",
                "chapter": i + 1,
                "total": total,
                "title": ch_title,
                "nodes_found": len(nodes),
                "total_nodes": len(all_nodes),
            }
        except Exception as e:
            logger.warning(f"Extraction failed for {ch_title}: {e}")
            yield {
                "type": "progress",
                "chapter": i + 1,
                "total": total,
                "title": ch_title,
                "nodes_found": 0,
                "total_nodes": len(all_nodes),
                "error": str(e),
            }

    yield {
        "type": "complete",
        "total_nodes": len(all_nodes),
        "total_edges": len(all_edges),
        "nodes": [n.model_dump() for n in all_nodes],
        "edges": [e.model_dump() for e in all_edges],
    }


def _extract_from_chapter(
    book_id: str,
    book_title: str,
    chapter_title: str,
    page_start: int,
    content: str,
) -> tuple[list[KnowledgeNode], list[KnowledgeEdge]]:

    if config.LLM_API_KEY:
        try:
            return _llm_extract(book_id, book_title, chapter_title, page_start, content)
        except Exception as e:
            logger.warning(f"LLM extraction failed for {chapter_title}, falling back to rule-based: {e}")

    return _rule_extract(book_id, book_title, chapter_title, page_start, content)


def _llm_extract(
    book_id: str,
    book_title: str,
    chapter_title: str,
    page_start: int,
    content: str,
) -> tuple[list[KnowledgeNode], list[KnowledgeEdge]]:

    from openai import OpenAI

    client = OpenAI(
        base_url=config.LLM_BASE_URL,
        api_key=config.LLM_API_KEY,
        timeout=LLM_CHAPTER_TIMEOUT,
    )

    prompt_template_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "prompts", "extract_knowledge.txt"
    )

    if os.path.exists(prompt_template_path):
        with open(prompt_template_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()
    else:
        system_prompt = _default_extract_prompt()

    user_prompt = f"""教材名：{book_title}
章节名：{chapter_title}
起始页：{page_start}

正文：
{content}

请输出JSON："""

    response = client.chat.completions.create(
        model=config.LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
        max_tokens=config.LLM_MAX_TOKENS,
    )

    raw = response.choices[0].message.content or ""
    raw = _clean_json_response(raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        try:
            repaired = _repair_json(client, raw, system_prompt)
            data = json.loads(repaired)
        except Exception:
            return _rule_extract(book_id, book_title, chapter_title, page_start, content)

    nodes = []
    for n in data.get("nodes", []):
        try:
            nodes.append(KnowledgeNode(
                id=n.get("id", f"{book_id}_auto_{len(nodes):03d}"),
                textbook_id=book_id,
                name=n.get("name", ""),
                definition=n.get("definition", ""),
                category=n.get("category", "概念"),
                chapter=chapter_title,
                page=n.get("page", page_start),
                source_quote=n.get("source_quote", ""),
                frequency=1,
                status=NodeStatus.RAW,
            ))
        except Exception:
            continue

    edges = []
    valid_node_ids = {n.id for n in nodes}
    for e in data.get("edges", []):
        src = e.get("source", "")
        tgt = e.get("target", "")
        if src in valid_node_ids and tgt in valid_node_ids:
            try:
                rt = e.get("relation_type", "parallel")
                if rt not in [r.value for r in RelationType]:
                    rt = "parallel"
                edges.append(KnowledgeEdge(
                    source=src,
                    target=tgt,
                    relation_type=RelationType(rt),
                    description=e.get("description", ""),
                    textbook_id=book_id,
                ))
            except Exception:
                continue

    return nodes, edges


def _repair_json(client, raw: str, system_prompt: str) -> str:
    response = client.chat.completions.create(
        model=config.LLM_MODEL,
        messages=[
            {"role": "system", "content": "你是一个JSON修复专家。请将以下文本修复为合法的JSON格式。只输出JSON，不要解释。"},
            {"role": "user", "content": f"请修复以下JSON：\n{raw[:3000]}"},
        ],
        temperature=0,
        max_tokens=config.LLM_MAX_TOKENS,
    )
    result = response.choices[0].message.content or ""
    return _clean_json_response(result)


def _clean_json_response(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _rule_extract(
    book_id: str,
    book_title: str,
    chapter_title: str,
    page_start: int,
    content: str,
) -> tuple[list[KnowledgeNode], list[KnowledgeEdge]]:

    nodes = []
    edges = []

    sentences = re.split(r"[。！？\n]", content)
    key_terms = []
    for s in sentences:
        s = s.strip()
        if 5 < len(s) < 100:
            if any(kw in s for kw in ["是指", "定义", "概念", "原理", "方法", "机制", "功能", "结构", "特点", "分类"]):
                key_terms.append(s)

    seen_names = set()
    for i, term in enumerate(key_terms[:8]):
        name_match = re.match(r"^(.{2,15})(是指|的定义|是一种|为)", term)
        if name_match:
            name = name_match.group(1).strip()
        else:
            words = term.split("，")[0] if "，" in term else term[:20]
            name = words.strip()

        if name in seen_names or len(name) < 2:
            continue
        seen_names.add(name)

        nodes.append(KnowledgeNode(
            id=f"{book_id}_ch{page_start:03d}_n{i:03d}",
            textbook_id=book_id,
            name=name,
            definition=term[:120],
            category="核心概念",
            chapter=chapter_title,
            page=page_start,
            source_quote=term[:80],
            frequency=1,
            status=NodeStatus.RAW,
        ))

    if len(nodes) >= 2:
        edge_types = list(RelationType)
        for i in range(len(nodes) - 1):
            edges.append(KnowledgeEdge(
                source=nodes[i].id,
                target=nodes[i + 1].id,
                relation_type=edge_types[i % len(edge_types)],
                description=f"{nodes[i].name}与{nodes[i + 1].name}相关",
                textbook_id=book_id,
            ))

    if not nodes:
        title_words = re.findall(r"[一-鿿]{2,6}", chapter_title)
        for i, word in enumerate(title_words[:3]):
            nodes.append(KnowledgeNode(
                id=f"{book_id}_ch{page_start:03d}_n{i:03d}",
                textbook_id=book_id,
                name=word,
                definition=f"来自{chapter_title}的核心概念",
                category="概念",
                chapter=chapter_title,
                page=page_start,
                source_quote=chapter_title,
                frequency=1,
                status=NodeStatus.RAW,
            ))

    return nodes, edges


def _default_extract_prompt() -> str:
    return """你是教材知识图谱抽取专家。请从给定章节中抽取核心知识点和知识点关系。

必须遵守：
1. 只输出合法 JSON，不要输出 Markdown。
2. 只基于给定正文，不得使用外部知识。
3. nodes 中每个对象必须包含：id, name, definition, category, chapter, page, source_quote
4. edges 中每个对象必须包含：source, target, relation_type, description
5. relation_type 只能是：prerequisite, parallel, contains, applies_to
6. 最多输出 10 个节点、15 条边。
7. definition 不超过 80 字。
8. source_quote 必须是原文中的短句。

输出JSON格式：
{
  "nodes": [{"id": "", "name": "", "definition": "", "category": "", "chapter": "", "page": 0, "source_quote": ""}],
  "edges": [{"source": "", "target": "", "relation_type": "", "description": ""}]
}"""
