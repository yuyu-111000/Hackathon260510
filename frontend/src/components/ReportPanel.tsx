import { useEffect } from 'react';

interface Props {
  report: string;
  onGenerate: () => void;
  onLoad: () => void;
}

export default function ReportPanel({ report, onGenerate, onLoad }: Props) {
  useEffect(() => {
    if (!report) onLoad();
  }, []);

  return (
    <div className="report-section">
      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
        <button className="btn btn-primary" style={{ flex: 1 }} onClick={onGenerate}>
          生成报告
        </button>
        <button className="btn btn-secondary" onClick={onLoad}>
          刷新
        </button>
      </div>
      {report ? (
        <div className="report-content">{report}</div>
      ) : (
        <div style={{ color: '#666', textAlign: 'center', marginTop: '40px', fontSize: '13px' }}>
          <p>暂无报告</p>
          <p style={{ marginTop: '8px', fontSize: '11px' }}>请先运行整合，然后点击"生成报告"</p>
        </div>
      )}
    </div>
  );
}
