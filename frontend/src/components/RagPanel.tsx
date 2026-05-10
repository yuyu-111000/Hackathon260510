import { useState } from 'react';
import type { RAGResponse } from '../types';

interface Props {
  onBuildRAG: () => void;
  onQuery: (q: string) => void;
  status: { indexed_books: number; chunk_count: number; status: string } | null;
  answer: RAGResponse | null;
}

export default function RagPanel({ onBuildRAG, onQuery, status, answer }: Props) {
  const [question, setQuestion] = useState('');

  const handleSubmit = () => {
    if (question.trim()) {
      onQuery(question.trim());
    }
  };

  return (
    <div className="rag-section">
      <button className="btn btn-primary" style={{ width: '100%', marginBottom: '12px' }} onClick={onBuildRAG}>
        构建RAG索引
      </button>

      {status && (
        <div className="rag-status">
          状态: {status.status} · {status.indexed_books}本教材 · {status.chunk_count}个片段
        </div>
      )}

      <div className="rag-query-box">
        <input
          placeholder="输入问题..."
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
        />
        <button className="btn btn-primary btn-sm" onClick={handleSubmit}>查询</button>
      </div>

      {answer && (
        <div className="rag-answer">
          <div className="answer-text">{answer.answer}</div>
          {answer.citations.map((c, i) => (
            <div key={i} className="citation-card">
              <div className="cite-source">{c.textbook} · {c.chapter} · 第{c.page}页</div>
              <div className="cite-quote">"{c.quote}"</div>
            </div>
          ))}
          {answer.benchmark && Object.keys(answer.benchmark).length > 0 && (
            <div style={{ marginTop: '12px', padding: '10px', background: '#F5F0E8', borderRadius: '8px', fontSize: '11px', color: '#6B5D4F' }}>
              <div style={{ fontWeight: 600, marginBottom: '6px', color: '#3D6B4F', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '1px' }}>检索指标</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px' }}>
                <span>检索方式: {answer.benchmark.retrieval_method}</span>
                <span>返回片段: {answer.benchmark.chunks_retrieved}</span>
                <span>平均相关度: {((answer.benchmark.avg_score ?? 0) * 100).toFixed(1)}%</span>
                <span>最高相关度: {((answer.benchmark.max_score ?? 0) * 100).toFixed(1)}%</span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
