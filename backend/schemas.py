from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class TextbookStatus(str, Enum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    PARSED = "parsed"
    FAILED = "failed"


class RelationType(str, Enum):
    PREREQUISITE = "prerequisite"
    PARALLEL = "parallel"
    CONTAINS = "contains"
    APPLIES_TO = "applies_to"


class DecisionAction(str, Enum):
    MERGE = "merge"
    KEEP = "keep"
    REMOVE = "remove"


class NodeStatus(str, Enum):
    RAW = "raw"
    MERGED = "merged"
    KEPT = "kept"
    REMOVED = "removed"


class Chapter(BaseModel):
    chapter_id: str
    textbook_id: str
    title: str
    page_start: int
    page_end: int
    content: str
    char_count: int


class Textbook(BaseModel):
    textbook_id: str
    filename: str
    title: str
    file_type: str
    total_pages: int = 0
    total_chars: int = 0
    status: TextbookStatus = TextbookStatus.UPLOADED
    chapters: list[Chapter] = Field(default_factory=list)


class KnowledgeNode(BaseModel):
    id: str
    textbook_id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    definition: str
    category: str
    chapter: str
    page: int
    source_quote: str = ""
    frequency: int = 1
    status: NodeStatus = NodeStatus.RAW
    confidence: float = 1.0


class KnowledgeEdge(BaseModel):
    source: str
    target: str
    relation_type: RelationType
    description: str = ""
    textbook_id: str = ""


class MergeDecision(BaseModel):
    decision_id: str
    action: DecisionAction
    affected_nodes: list[str] = Field(default_factory=list)
    result_node: Optional[str] = None
    reason: str = ""
    confidence: float = 0.0
    status: str = "active"


class RAGChunk(BaseModel):
    chunk_id: str
    textbook_id: str
    textbook: str
    chapter: str
    page_start: int
    page_end: int
    content: str
    char_count: int = 0


class Citation(BaseModel):
    textbook: str
    chapter: str
    page: int
    relevance_score: float = 0.0
    quote: str = ""


class GraphResponse(BaseModel):
    nodes: list[KnowledgeNode] = Field(default_factory=list)
    edges: list[KnowledgeEdge] = Field(default_factory=list)


class IntegrationStats(BaseModel):
    original_total_chars: int = 0
    compressed_chars: int = 0
    compression_ratio: float = 0.0
    original_node_count: int = 0
    merged_node_count: int = 0
    merge_count: int = 0
    keep_count: int = 0
    remove_count: int = 0


class IntegrationRunResponse(BaseModel):
    decisions: list[MergeDecision] = Field(default_factory=list)
    stats: IntegrationStats = Field(default_factory=IntegrationStats)
    merged_graph: GraphResponse = Field(default_factory=GraphResponse)


class RAGQueryRequest(BaseModel):
    question: str


class RAGQueryResponse(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    source_chunks: list[str] = Field(default_factory=list)
    benchmark: dict = Field(default_factory=dict)


class RAGStatusResponse(BaseModel):
    indexed_books: int = 0
    chunk_count: int = 0
    status: str = "not_indexed"


class ChatRequest(BaseModel):
    message: str


class ChatMessage(BaseModel):
    message_id: str
    role: str
    content: str
    timestamp: str = ""


class ChatResponse(BaseModel):
    reply: str
    intent: str = ""
    updated_decisions: list[MergeDecision] = Field(default_factory=list)
    requires_graph_update: bool = False


class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessage] = Field(default_factory=list)


class ReportResponse(BaseModel):
    content: str
    generated_at: str = ""


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
