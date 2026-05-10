import { useEffect, useRef } from 'react';
import type { KnowledgeNode } from '../types';

interface Props {
  node: KnowledgeNode | null;
  position: { x: number; y: number } | null;
  onClose: () => void;
}

export default function NodeDetailPopover({ node, position, onClose }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as HTMLElement)) {
        onClose();
      }
    };
    if (node) {
      document.addEventListener('mousedown', handleClick);
      return () => document.removeEventListener('mousedown', handleClick);
    }
  }, [node, onClose]);

  if (!node || !position) return null;

  const style: React.CSSProperties = {
    position: 'fixed',
    left: Math.min(position.x + 12, window.innerWidth - 360),
    top: Math.min(position.y - 20, window.innerHeight - 400),
    zIndex: 100,
  };

  return (
    <div ref={ref} className="node-popover" style={style}>
      <div className="popover-header">
        <h3>{node.name}</h3>
        <button className="popover-close" onClick={onClose}>×</button>
      </div>

      <div className="popover-body">
        <div className="popover-field">
          <div className="popover-label">定义</div>
          <div className="popover-value">{node.definition}</div>
        </div>

        <div className="popover-row">
          <div className="popover-field">
            <div className="popover-label">分类</div>
            <div className="popover-value">{node.category}</div>
          </div>
          <div className="popover-field">
            <div className="popover-label">状态</div>
            <div className="popover-value">
              <span className={`status-badge status-${node.status}`}>
                {node.status === 'merged' ? '已合并' : node.status === 'removed' ? '已移除' : node.status === 'kept' ? '已保留' : '原始'}
              </span>
            </div>
          </div>
        </div>

        <div className="popover-field">
          <div className="popover-label">来源</div>
          <div className="popover-value">{node.textbook_id} · {node.chapter} · 第{node.page}页</div>
        </div>

        {node.aliases.length > 0 && (
          <div className="popover-field">
            <div className="popover-label">别名</div>
            <div className="popover-aliases">
              {node.aliases.map((a, i) => (
                <span key={i} className="alias-tag">{a}</span>
              ))}
            </div>
          </div>
        )}

        <div className="popover-field">
          <div className="popover-label">出现频次</div>
          <div className="popover-value">{node.frequency}</div>
        </div>

        {node.source_quote && (
          <div className="popover-field">
            <div className="popover-label">原文引用</div>
            <div className="popover-quote">{node.source_quote}</div>
          </div>
        )}
      </div>
    </div>
  );
}
