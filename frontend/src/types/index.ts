export interface Chapter {
  chapter_id: string;
  textbook_id: string;
  title: string;
  page_start: number;
  page_end: number;
  content: string;
  char_count: number;
}

export interface Textbook {
  textbook_id: string;
  filename: string;
  title: string;
  file_type: string;
  total_pages: number;
  total_chars: number;
  status: 'uploaded' | 'parsing' | 'parsed' | 'failed';
  chapters: Chapter[];
}

export interface KnowledgeNode {
  id: string;
  textbook_id: string;
  name: string;
  aliases: string[];
  definition: string;
  category: string;
  chapter: string;
  page: number;
  source_quote: string;
  frequency: number;
  status: 'raw' | 'merged' | 'kept' | 'removed';
}

export interface KnowledgeEdge {
  source: string;
  target: string;
  relation_type: 'prerequisite' | 'parallel' | 'contains' | 'applies_to';
  description: string;
  textbook_id: string;
}

export interface MergeDecision {
  decision_id: string;
  action: 'merge' | 'keep' | 'remove';
  affected_nodes: string[];
  result_node: string | null;
  reason: string;
  confidence: number;
  status: string;
}

export interface IntegrationStats {
  original_total_chars: number;
  compressed_chars: number;
  compression_ratio: number;
  original_node_count: number;
  merged_node_count: number;
  merge_count: number;
  keep_count: number;
  remove_count: number;
}

export interface Citation {
  textbook: string;
  chapter: string;
  page: number;
  relevance_score: number;
  quote: string;
}

export interface RAGResponse {
  answer: string;
  citations: Citation[];
  source_chunks: string[];
  benchmark?: {
    retrieval_method?: string;
    top_k?: number;
    avg_score?: number;
    max_score?: number;
    chunks_retrieved?: number;
    total_chunks?: number;
  };
}

export interface ChatMessage {
  message_id: string;
  role: 'teacher' | 'system';
  content: string;
  timestamp: string;
}

export interface GraphData {
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
}
