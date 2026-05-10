import { useState } from 'react';
import type { Textbook } from '../types';

interface Props {
  textbooks: Textbook[];
  onParse: (id: string) => void;
  onBuildGraph: (id?: string) => void;
}

export default function TextbookList({ textbooks, onParse, onBuildGraph }: Props) {
  const [expanded, setExpanded] = useState<string | null>(null);

  if (textbooks.length === 0) {
    return (
      <div className="textbook-section">
        <h3>教材列表</h3>
        <p style={{ fontSize: '12px', color: '#666' }}>暂无教材，请上传</p>
      </div>
    );
  }

  return (
    <div className="textbook-section">
      <h3>教材列表 ({textbooks.length})</h3>
      {textbooks.map((tb) => (
        <div key={tb.textbook_id} className="textbook-card" onClick={() => setExpanded(expanded === tb.textbook_id ? null : tb.textbook_id)}>
          <div className="name">{tb.title || tb.filename}</div>
          <div className="meta">{tb.file_type.toUpperCase()} · {tb.total_pages}页 · {tb.total_chars}字</div>
          <span className={`status status-${tb.status}`}>{tb.status}</span>
          {tb.status === 'uploaded' && (
            <div className="textbook-actions">
              <button onClick={(e) => { e.stopPropagation(); onParse(tb.textbook_id); }}>解析</button>
            </div>
          )}
          {tb.status === 'parsed' && (
            <div className="textbook-actions">
              <button onClick={(e) => { e.stopPropagation(); onBuildGraph(tb.textbook_id); }}>构建图谱</button>
            </div>
          )}
          {expanded === tb.textbook_id && tb.chapters.length > 0 && (
            <div className="chapter-tree">
              {tb.chapters.map((ch) => (
                <div key={ch.chapter_id} className="chapter-item">
                  {ch.title} (p.{ch.page_start}-{ch.page_end})
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
      {textbooks.some(t => t.status === 'parsed') && (
        <button
          className="btn btn-primary"
          style={{ width: '100%', marginTop: '8px' }}
          onClick={() => onBuildGraph()}
        >
          构建全部图谱
        </button>
      )}
    </div>
  );
}
