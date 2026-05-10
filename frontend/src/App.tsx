import { useState, useEffect, useCallback } from 'react';
import './App.css';
import type {
  Textbook, GraphData, MergeDecision, IntegrationStats,
  ChatMessage
} from './types';
import {
  uploadTextbook, listTextbooks, parseTextbook,
  buildGraph, getGraph, getMergedGraph,
  runIntegration,
  sendChat, getChatHistory,
  generateReport
} from './api/client';
import UploadPanel from './components/UploadPanel';
import TextbookList from './components/TextbookList';
import GraphView from './components/GraphView';
import ChatPanel from './components/ChatPanel';

function App() {
  const [textbooks, setTextbooks] = useState<Textbook[]>([]);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [mergedGraph, setMergedGraph] = useState<GraphData | null>(null);
  const [decisions, setDecisions] = useState<MergeDecision[]>([]);
  const [stats, setStats] = useState<IntegrationStats | null>(null);
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState<string>('');
  const [graphMode, setGraphMode] = useState<'raw' | 'merged'>('raw');
  const [report, setReport] = useState<string>('');
  const [showReport, setShowReport] = useState(false);

  const refreshTextbooks = useCallback(async () => {
    try {
      const list = await listTextbooks();
      setTextbooks(list);
    } catch { /* ignore on mount */ }
  }, []);

  const refreshGraph = useCallback(async () => {
    try {
      const g = await getGraph();
      setGraphData(g);
    } catch { /* no graph yet */ }
  }, []);

  useEffect(() => {
    refreshTextbooks();
    refreshGraph();
  }, [refreshTextbooks, refreshGraph]);

  const handleUpload = async (file: File) => {
    setLoading('上传中...');
    try {
      await uploadTextbook(file);
      await refreshTextbooks();
    } catch (e: any) {
      alert('上传失败: ' + (e.friendlyMessage || e.message));
    } finally {
      setLoading('');
    }
  };

  const handleParse = async (id: string) => {
    setLoading('解析中...');
    try {
      await parseTextbook(id);
      await refreshTextbooks();
    } catch (e: any) {
      alert('解析失败: ' + (e.friendlyMessage || e.message));
    } finally {
      setLoading('');
    }
  };

  const handleBuildGraph = async (textbookId?: string) => {
    setLoading('构建知识图谱...');
    try {
      const g = await buildGraph(textbookId);
      setGraphData(g);
    } catch (e: any) {
      alert('构建失败: ' + (e.friendlyMessage || e.message));
    } finally {
      setLoading('');
    }
  };

  const handleIntegration = async () => {
    setLoading('跨教材整合中...');
    try {
      const result = await runIntegration();
      setDecisions(result.decisions);
      setStats(result.stats);
      setMergedGraph(result.merged_graph);
      setGraphMode('merged');
    } catch (e: any) {
      alert('整合失败: ' + (e.friendlyMessage || e.message));
    } finally {
      setLoading('');
    }
  };

  const handleSendChat = async (message: string) => {
    setLoading('处理中...');
    try {
      const resp = await sendChat(message);
      const history = await getChatHistory();
      setChatHistory(history);
      if (resp.updated_decisions.length > 0) {
        setDecisions(resp.updated_decisions);
      }
      if (resp.requires_graph_update) {
        try {
          const mg = await getMergedGraph();
          setMergedGraph(mg);
        } catch { /* ignore */ }
      }
    } catch (e: any) {
      alert('发送失败: ' + (e.friendlyMessage || e.message));
    } finally {
      setLoading('');
    }
  };

  const handleGenerateReport = async () => {
    setLoading('生成报告...');
    try {
      const content = await generateReport();
      setReport(content);
      setShowReport(true);
    } catch (e: any) {
      alert('报告生成失败: ' + (e.friendlyMessage || e.message));
    } finally {
      setLoading('');
    }
  };

  const parsedCount = textbooks.filter(t => t.status === 'parsed').length;

  return (
    <div className="app-container">
      {loading && (
        <div className="loading-overlay">
          <div className="loading-spinner" />
          <span>{loading}</span>
        </div>
      )}

      {/* Left Panel */}
      <div className="left-panel">
        <h1 className="app-title">EduFusion</h1>
        <p className="app-subtitle">学科知识整合智能体</p>
        <div className="left-panel-scroll">
          <UploadPanel onUpload={handleUpload} />
          <TextbookList
            textbooks={textbooks}
            onParse={handleParse}
            onBuildGraph={handleBuildGraph}
          />
        </div>
        {/* Fixed bottom area */}
        <div className="left-panel-bottom">
          {parsedCount >= 2 && (
            <>
              <button
                className="btn btn-primary"
                onClick={handleIntegration}
                style={{ width: '100%' }}
              >
                跨教材整合 ({parsedCount}本)
              </button>
              {stats && (
                <div style={{
                  fontSize: '11px',
                  color: 'var(--text-dim)',
                  marginTop: '8px',
                  textAlign: 'center',
                }}>
                  压缩比: {stats.compression_ratio.toFixed(1)}%
                  {stats.compression_ratio <= 30 ? ' ✓' : ''}
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Center Panel - Graph */}
      <div className="center-panel">
        <GraphView
          graphData={graphMode === 'merged' && mergedGraph ? mergedGraph : graphData}
          graphMode={graphMode}
          onToggleMode={() => setGraphMode(graphMode === 'raw' ? 'merged' : 'raw')}
          hasMergedGraph={!!mergedGraph}
          onGenerateReport={handleGenerateReport}
        />
      </div>

      {/* Right Panel - Chat only */}
      <div className="right-panel">
        <div className="right-panel-header">
          <span>教师对话</span>
          {decisions.length > 0 && (
            <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
              {decisions.length} 项决策
            </span>
          )}
        </div>
        <div className="right-panel-body">
          <ChatPanel
            history={chatHistory}
            onSend={handleSendChat}
          />
        </div>
      </div>

      {/* Report Modal */}
      {showReport && report && (
        <div className="report-modal-overlay" onClick={() => setShowReport(false)}>
          <div className="report-modal" onClick={e => e.stopPropagation()}>
            <div className="report-modal-header">
              <h2>整合报告</h2>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  className="btn btn-sm"
                  onClick={() => {
                    const blob = new Blob([report], { type: 'text/markdown' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = '整合报告.md';
                    a.click();
                    URL.revokeObjectURL(url);
                  }}
                >
                  下载
                </button>
                <button className="btn btn-sm" onClick={() => setShowReport(false)}>关闭</button>
              </div>
            </div>
            <div className="report-modal-body">
              <pre>{report}</pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
