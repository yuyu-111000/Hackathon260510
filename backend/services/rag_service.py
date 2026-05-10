import os
import json
import re
import math
from backend.schemas import RAGQueryResponse, Citation
from backend import config


class RAGService:
    def __init__(self):
        self.chunks: list[dict] = []
        self.indexed_books: int = 0
        self.chunk_count: int = 0
        self._embeddings = None
        self._index = None
        self._bm25 = None

    def build_index(self, textbooks: list[dict]):
        self.chunks = []
        self.indexed_books = len(textbooks)

        for textbook in textbooks:
            book_title = textbook.get("title", "未知教材")
            book_id = textbook.get("textbook_id", "")

            for chapter in textbook.get("chapters", []):
                ch_content = chapter.get("content", "")
                ch_title = chapter.get("title", "")
                page_start = chapter.get("page_start", 1)
                page_end = chapter.get("page_end", page_start)

                chapter_chunks = _sliding_window_chunk(
                    ch_content, config.CHUNK_SIZE, config.CHUNK_OVERLAP
                )

                for i, chunk_text in enumerate(chapter_chunks):
                    estimated_page = page_start + (page_end - page_start) * i // max(len(chapter_chunks), 1)
                    self.chunks.append({
                        "chunk_id": f"{book_id}_{ch_title[:10]}_{i:03d}",
                        "textbook_id": book_id,
                        "textbook": book_title,
                        "chapter": ch_title,
                        "page_start": estimated_page,
                        "page_end": min(estimated_page + 1, page_end),
                        "content": chunk_text,
                        "char_count": len(chunk_text),
                    })

        self.chunk_count = len(self.chunks)
        self._build_vector_index()

    def _build_vector_index(self):
        if not self.chunks:
            return

        try:
            import numpy as np
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(config.EMBEDDING_MODEL, device=config.EMBEDDING_DEVICE)
            texts = [c["content"] for c in self.chunks]
            self._embeddings = model.encode(texts, normalize_embeddings=True)
            self._embeddings = np.array(self._embeddings, dtype=np.float32)

        except Exception:
            self._embeddings = None

    def query(self, question: str) -> RAGQueryResponse:
        if not self.chunks:
            return RAGQueryResponse(
                answer="当前知识库中未找到相关信息",
                citations=[],
                source_chunks=[],
            )

        top_chunks = self._retrieve(question, config.RAG_TOP_K)

        if not top_chunks:
            return RAGQueryResponse(
                answer="当前知识库中未找到相关信息",
                citations=[],
                source_chunks=[],
            )

        if config.LLM_API_KEY:
            try:
                return _llm_answer(question, top_chunks)
            except Exception:
                pass

        return _extractive_answer(question, top_chunks)

    def _retrieve(self, question: str, top_k: int) -> list[dict]:
        if self._embeddings is not None:
            return self._vector_retrieve(question, top_k)

        return self._keyword_retrieve(question, top_k)

    def _vector_retrieve(self, question: str, top_k: int) -> list[dict]:
        import numpy as np

        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(config.EMBEDDING_MODEL, device=config.EMBEDDING_DEVICE)
            q_emb = model.encode([question], normalize_embeddings=True)
            q_emb = np.array(q_emb, dtype=np.float32)

            scores = np.dot(self._embeddings, q_emb.T).flatten()

            top_indices = np.argsort(scores)[::-1][:top_k]
            results = []
            for idx in top_indices:
                chunk = dict(self.chunks[idx])
                chunk["score"] = float(scores[idx])
                results.append(chunk)

            return results

        except Exception:
            return self._keyword_retrieve(question, top_k)

    def _keyword_retrieve(self, question: str, top_k: int) -> list[dict]:
        keywords = re.findall(r"[一-鿿]{2,}|[a-zA-Z]{3,}", question)
        if not keywords:
            return self.chunks[:top_k]

        scored = []
        for chunk in self.chunks:
            text = chunk["content"].lower()
            score = sum(1 for kw in keywords if kw.lower() in text)
            if score > 0:
                c = dict(chunk)
                c["score"] = score / len(keywords)
                scored.append(c)

        scored.sort(key=lambda x: x["score"], reverse=True)

        if not scored:
            return self.chunks[:top_k]

        return scored[:top_k]


def _sliding_window_chunk(text: str, chunk_size: int, overlap: int) -> list[str]:
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end]

        if chunk.strip():
            chunks.append(chunk)

        if end >= len(text):
            break

        start = end - overlap

    return chunks


def _llm_answer(question: str, top_chunks: list[dict]) -> RAGQueryResponse:
    from openai import OpenAI

    client = OpenAI(base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY)

    context_parts = []
    for i, chunk in enumerate(top_chunks):
        context_parts.append(
            f"[{chunk['textbook']}, {chunk['chapter']}, 第{chunk['page_start']}页]\n{chunk['content']}"
        )
    context = "\n\n".join(context_parts)

    prompt_template_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "prompts", "rag_answer.txt"
    )

    if os.path.exists(prompt_template_path):
        with open(prompt_template_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()
    else:
        system_prompt = _default_rag_prompt()

    response = client.chat.completions.create(
        model=config.LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"用户问题：{question}\n\n教材片段：\n{context}\n\n请输出JSON："},
        ],
        temperature=0.1,
        max_tokens=config.LLM_MAX_TOKENS,
    )

    raw = response.choices[0].message.content or "{}"
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return _extractive_answer(question, top_chunks)

    citations = []
    for c in data.get("citations", []):
        citations.append(Citation(
            textbook=c.get("textbook", ""),
            chapter=c.get("chapter", ""),
            page=c.get("page", 0),
            relevance_score=c.get("relevance_score", 0.0),
            quote=c.get("quote", ""),
        ))

    return RAGQueryResponse(
        answer=data.get("answer", "当前知识库中未找到相关信息"),
        citations=citations,
        source_chunks=[c["content"][:200] for c in top_chunks],
        benchmark={
            "retrieval_method": "vector" if hasattr(top_chunks[0], 'get') else "keyword",
            "top_k": len(top_chunks),
            "avg_score": round(sum(c.get("score", 0) for c in top_chunks) / max(len(top_chunks), 1), 3),
            "max_score": round(max(c.get("score", 0) for c in top_chunks), 3) if top_chunks else 0,
            "chunks_retrieved": len(top_chunks),
            "total_chunks": len(top_chunks),
        },
    )


def _extractive_answer(question: str, top_chunks: list[dict]) -> RAGQueryResponse:
    answer_parts = []
    citations = []

    for chunk in top_chunks[:3]:
        answer_parts.append(chunk["content"][:300])
        citations.append(Citation(
            textbook=chunk["textbook"],
            chapter=chunk["chapter"],
            page=chunk["page_start"],
            relevance_score=chunk.get("score", 0.0),
            quote=chunk["content"][:100],
        ))

    answer = "根据教材内容：\n" + "\n".join(answer_parts)
    if len(answer) > 800:
        answer = answer[:800] + "..."

    return RAGQueryResponse(
        answer=answer,
        citations=citations,
        source_chunks=[c["content"][:200] for c in top_chunks],
        benchmark={
            "retrieval_method": "keyword_fallback",
            "top_k": len(top_chunks),
            "avg_score": round(sum(c.get("score", 0) for c in top_chunks) / max(len(top_chunks), 1), 3),
            "max_score": round(max(c.get("score", 0) for c in top_chunks), 3) if top_chunks else 0,
            "chunks_retrieved": len(top_chunks),
        },
    )


def _default_rag_prompt() -> str:
    return """你是严格基于教材内容回答问题的教学助手。

规则：
1. 只能使用下方提供的教材片段回答。
2. 不得使用外部知识。
3. 如果上下文不足，请回答："当前知识库中未找到相关信息"。
4. 每个关键结论都必须附引用。
5. 引用格式为：[教材名称, 章节, 第X页]。
6. 只输出JSON。

输出格式：
{
  "answer": "回答内容",
  "citations": [
    {"textbook": "教材名", "chapter": "章节", "page": 页码, "relevance_score": 0.9, "quote": "原文引用"}
  ]
}"""
