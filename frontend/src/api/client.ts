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

// Report
export async function getReport(): Promise<string> {
  const { data } = await api.get('/api/report');
  return data.content;
}

export async function generateReport(): Promise<string> {
  const { data } = await api.post('/api/report/generate');
  return data.content;
}
