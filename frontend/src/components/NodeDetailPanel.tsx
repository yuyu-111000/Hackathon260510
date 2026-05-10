import type { KnowledgeNode } from '../types';

interface Props {
  node: KnowledgeNode | null;
}

export default function NodeDetailPanel({ node }: Props) {
  if (!node) {
    return (
      <div style={{ color: '#666', textAlign: 'center', marginTop: '40px' }}>
        <p>点击图谱节点查看详情</p>
      </div>
    );
  }

  return (
    <div className="node-detail">
      <h3>{node.name}</h3>
      <div className="field">
        <div className="label">定义</div>
        <div className="value">{node.definition}</div>
      </div>
      <div className="field">
        <div className="label">分类</div>
        <div className="value">{node.category}</div>
      </div>
      <div className="field">
        <div className="label">状态</div>
        <div className="value">
          <span style={{
            display: 'inline-block',
            padding: '2px 10px',
            borderRadius: '10px',
            fontSize: '11px',
            fontWeight: 600,
            background: node.status === 'merged' ? 'rgba(74, 123, 155, 0.1)' : node.status === 'removed' ? 'rgba(184, 84, 80, 0.1)' : 'rgba(61, 107, 79, 0.1)',
            color: node.status === 'merged' ? '#4A7B9B' : node.status === 'removed' ? '#B85450' : '#3D6B4F',
          }}>
            {node.status === 'merged' ? '已合并' : node.status === 'removed' ? '已移除' : node.status === 'kept' ? '已保留' : '原始'}
          </span>
        </div>
      </div>
      <div className="field">
        <div className="label">来源</div>
        <div className="value">{node.textbook_id} · {node.chapter} · 第{node.page}页</div>
      </div>
      {node.aliases.length > 0 && (
        <div className="field">
          <div className="label">别名</div>
          <div className="aliases">
            {node.aliases.map((a, i) => (
              <span key={i} className="alias-tag">{a}</span>
            ))}
          </div>
        </div>
      )}
      <div className="field">
        <div className="label">出现频次</div>
        <div className="value">{node.frequency}</div>
      </div>
      {node.source_quote && (
        <div className="field">
          <div className="label">原文引用</div>
          <div className="value" style={{ fontStyle: 'italic', color: '#aaa', borderLeft: '3px solid #3a3d50', paddingLeft: '10px' }}>
            {node.source_quote}
          </div>
        </div>
      )}
    </div>
  );
}
