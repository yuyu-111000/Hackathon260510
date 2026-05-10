import type { MergeDecision, IntegrationStats } from '../types';

interface Props {
  decisions: MergeDecision[];
  stats: IntegrationStats | null;
  onRunIntegration: () => void;
  onUpdateDecision: (id: string, action: string) => void;
}

export default function IntegrationPanel({ decisions, stats, onRunIntegration, onUpdateDecision }: Props) {
  return (
    <div className="integration-section">
      <button className="btn btn-primary" style={{ width: '100%', marginBottom: '16px' }} onClick={onRunIntegration}>
        运行跨教材整合
      </button>

      {stats && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-value">{stats.original_node_count}</div>
            <div className="stat-label">原始节点</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.merged_node_count}</div>
            <div className="stat-label">整合后节点</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.compression_ratio.toFixed(1)}%</div>
            <div className="stat-label">压缩率</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.merge_count}</div>
            <div className="stat-label">合并数</div>
          </div>
        </div>
      )}

      {decisions.length > 0 && (
        <div>
          <h4 style={{ fontSize: '13px', color: '#888', marginBottom: '8px' }}>决策列表 ({decisions.length})</h4>
          {decisions.map((d) => (
            <div key={d.decision_id} className="decision-card">
              <div className="decision-header">
                <span className={`decision-action action-${d.action}`}>{d.action}</span>
                <span style={{ fontSize: '11px', color: '#666' }}>置信度 {(d.confidence * 100).toFixed(0)}%</span>
              </div>
              <div className="decision-reason">{d.reason}</div>
              <div className="decision-nodes">节点: {d.affected_nodes.join(', ')}</div>
              <div className="decision-actions">
                {d.action !== 'keep' && (
                  <button onClick={() => onUpdateDecision(d.decision_id, 'keep')}>保留</button>
                )}
                {d.action !== 'remove' && (
                  <button onClick={() => onUpdateDecision(d.decision_id, 'remove')}>删除</button>
                )}
                {d.action !== 'merge' && d.affected_nodes.length > 1 && (
                  <button onClick={() => onUpdateDecision(d.decision_id, 'merge')}>合并</button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
