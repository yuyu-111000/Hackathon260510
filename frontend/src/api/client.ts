import axios from 'axios';
import type {
  Textbook, GraphData, MergeDecision, IntegrationStats,
  RAGResponse, ChatMessage
} from '../types';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 300000,
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg = err.response?.data?.detail || err.message || '请求失败';
    err.friendlyMessage = msg;
    return Promise.reject(err);
  }
);

// Textbooks
export async function uploadTextbook(file: File): Promise<Textbook> {
  const form = new FormData();
  form.append('file', file);
  const { data } = await api.post('/api/textbooks/upload', form);
  return data;
}

export async function listTextbooks(): Promise<Textbook[]> {
  const { data } = await api.get('/api/textbooks');
  return data;
}

export async function getTextbook(id: string): Promise<Textbook> {
  const { data } = await api.get(`/api/textbooks/${id}`);
  return data;
}

export async function parseTextbook(id: string): Promise<Textbook> {
  const { data } = await api.post(`/api/textbooks/${id}/parse`);
  return data;
}

// Graph
export async function buildGraph(textbookId?: string): Promise<GraphData> {
  const params = textbookId ? { textbook_id: textbookId } : {};
  const { data } = await api.post('/api/graph/build', null, { params });
  return data;
}

export interface BuildProgressEvent {
  type: 'start' | 'progress' | 'complete' | 'done';
  total_chapters?: number;
  chapter?: number;
  total?: number;
  title?: string;
  nodes_found?: number;
  total_nodes?: number;
  total_edges?: number;
  error?: string;
  nodes?: any[];
  edges?: any[];
  book_title?: string;
}

export function buildGraphStream(
  textbookId: string,
  onEvent: (event: BuildProgressEvent) => void,
): Promise<GraphData> {
  const base = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const params = new URLSearchParams({ textbook_id: textbookId });
  const url = `${base}/api/graph/build-stream?${params}`;

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', url);
    xhr.setRequestHeader('Accept', 'text/event-stream');

    let buffer = '';
    let finalNodes: any[] = [];
    let finalEdges: any[] = [];

    xhr.onprogress = () => {
      buffer += xhr.responseText;
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const event = JSON.parse(line.slice(6));
          onEvent(event);

          if (event.type === 'complete') {
            finalNodes = event.nodes || [];
            finalEdges = event.edges || [];
          }
        } catch { /* skip malformed */ }
      }
    };

    xhr.onload = () => {
      // Process remaining buffer
      if (buffer.startsWith('data: ')) {
        try {
          const event = JSON.parse(buffer.slice(6));
          onEvent(event);
          if (event.type === 'complete') {
            finalNodes = event.nodes || [];
            finalEdges = event.edges || [];
          }
        } catch { /* skip */ }
      }
      resolve({ nodes: finalNodes, edges: finalEdges });
    };

    xhr.onerror = () => reject(new Error('连接失败'));
    xhr.send();
  });
}

export async function getGraph(): Promise<GraphData> {
  const { data } = await api.get('/api/graph');
  return data;
}

export async function getMergedGraph(): Promise<GraphData> {
  const { data } = await api.get('/api/graph/merged');
  return data;
}

// Integration
export interface IntegrationResult {
  decisions: MergeDecision[];
  stats: IntegrationStats;
  merged_graph: GraphData;
}

export async function runIntegration(): Promise<IntegrationResult> {
  const { data } = await api.post('/api/integration/run');
  return data;
}

export async function getDecisions(): Promise<MergeDecision[]> {
  const { data } = await api.get('/api/integration/decisions');
  return data;
}

export async function updateDecision(id: string, action: string): Promise<MergeDecision> {
  const { data } = await api.patch(`/api/integration/decisions/${id}`, null, {
    params: { action },
  });
  return data;
}

// RAG
export async function buildRAGIndex(): Promise<{ status: string; books: number; chunks: number }> {
  const { data } = await api.post('/api/rag/index');
  return data;
}

export async function getRAGStatus(): Promise<{ indexed_books: number; chunk_count: number; status: string }> {
  const { data } = await api.get('/api/rag/status');
  return data;
}

export async function queryRAG(question: string): Promise<RAGResponse> {
  const { data } = await api.post('/api/rag/query', { question });
  return data;
}

// Chat
export async function sendChat(message: string): Promise<{
  reply: string;
  intent: string;
  updated_decisions: MergeDecision[];
  requires_graph_update: boolean;
}> {
  const { data } = await api.post('/api/chat', { message });
  return data;
}

export async function getChatHistory(): Promise<ChatMessage[]> {
  const { data } = await api.get('/api/chat/history');
  return data.messages;
}

// Learning Path
export interface LearningPathItem {
  order: number;
  node_name: string;
  node_id: string;
  category: string;
  prerequisites: string[];
}
export interface LearningPathResponse {
  paths: LearningPathItem[];
  total_steps: number;
  methodology: string;
}
export async function getLearningPath(): Promise<LearningPathResponse> {
  const { data } = await api.get('/api/graph/learning-path');
  return data;
}

// Report
export async function getReport(): Promise<string> {
  const { data } = await api.get('/api/report');
  return data.content;
}

export async function generateReport(): Promise<string> {
  const { data } = await api.post('/api/report/generate');
  return data.content;
}
