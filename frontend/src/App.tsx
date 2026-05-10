import { useState, useEffect, useCallback } from 'react';
import './App.css';
import type {
  Textbook, GraphData, MergeDecision, IntegrationStats,
  ChatMessage, KnowledgeNode, RAGResponse
} from './types';
import {
  uploadTextbook, listTextbooks, parseTextbook,
  buildGraph, buildGraphStream, getGraph, getMergedGraph,
  runIntegration, getDecisions, updateDecision,
  sendChat, getChatHistory,
  generateReport, getReport,
  buildRAGIndex, queryRAG,
} from './api/client';
import UploadPanel from './components/UploadPanel';
import TextbookList from './components/TextbookList';
import GraphView from './components/GraphView';
import RightPanel from './components/RightPanel';

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
  const [activeTab, setActiveTab] = useState<'node' | 'integration' | 'rag' | 'chat' | 'report'>('chat');
  const [selectedNode, setSelectedNode] = useState<KnowledgeNode | null>(null);
  const [ragStatus, setRagStatus] = useState<{ indexed_books: number; chunk_count: number; status: string } | null>(null);
  const [ragAnswer, setRagAnswer] = useState<RAGResponse | null>(null);

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
    if (!textbookId) {
      setLoading('构建知识图谱...');
      try {
        const g = await buildGraph();
        setGraphData(g);
      } catch (e: any) {
        alert('构建失败: ' + (e.friendlyMessage || e.message));
      } finally {
        setLoading('');
      }
      return;
    }

    const tb = textbooks.find(t => t.textbook_id === textbookId);
    const chapterCount = tb?.chapters?.length || 0;

    if (chapterCount > 5) {
      setLoading('构建中: 0/' + chapterCount + ' 章...');
      try {
        const g = await buildGraphStream(textbookId, (event) => {
          if (event.type === 'progress') {
            setLoading(`构建中: ${event.chapter}/${event.total} ${event.title || ''}`);
          }
        });
        setGraphData(g);
      } catch (e: any) {
        alert('构建失败: ' + (e.message || '未知错误'));
      } finally {
        setLoading('');
      }
    } else {
      setLoading('构建知识图谱...');
      try {
        const g = await buildGraph(textbookId);
        setGraphData(g);
      } catch (e: any) {
        alert('构建失败: ' + (e.friendlyMessage || e.message));
      } finally {
        setLoading('');
      }
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

  const handleBuildRAG = async () => {
    setLoading('构建RAG索引...');
    try {
      const result = await buildRAGIndex();
      setRagStatus({ indexed_books: result.books, chunk_count: result.chunks, status: 'ready' });
    } catch (e: any) {
      alert('RAG索引构建失败: ' + (e.friendlyMessage || e.message));
    } finally {
      setLoading('');
    }
  };

  const handleRAGQuery = async (q: string) => {
    setLoading('检索中...');
    try {
      const result = await queryRAG(q);
      setRagAnswer(result);
    } catch (e: any) {
      alert('查询失败: ' + (e.friendlyMessage || e.message));
    } finally {
      setLoading('');
    }
  };

  const handleLoadReport = async () => {
    try {
      const content = await getReport();
      if (content && content !== '报告尚未生成。请先运行整合分析。') {
        setReport(content);
      }
    } catch { /* ignore */ }
  };

  const handleUpdateDecision = async (id: string, action: string) => {
    try {
      await updateDecision(id, action);
      const mg = await getMergedGraph();
      setMergedGraph(mg);
      const updatedDecisions = await getDecisions();
      setDecisions(updatedDecisions);
    } catch (e: any) {
      alert('更新决策失败: ' + (e.friendlyMessage || e.message));
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
          rawNodeCount={graphData?.nodes.length}
          mergedNodeCount={mergedGraph?.nodes.length}
          onNodeSelect={(node) => { setSelectedNode(node); setActiveTab('node'); }}
        />
      </div>

      {/* Right Panel - Multi-tab */}
      <div className="right-panel">
        <div className="right-panel-header">
          <span>{
            activeTab === 'node' ? '节点详情' :
            activeTab === 'integration' ? '跨教材整合' :
            activeTab === 'rag' ? 'RAG 问答' :
            activeTab === 'chat' ? '教师对话' :
            '整合报告'
          }</span>
          {activeTab === 'integration' && decisions.length > 0 && (
            <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
              {decisions.length} 项决策
            </span>
          )}
          {activeTab === 'rag' && ragStatus && (
            <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>
              {ragStatus.chunk_count} 片段
            </span>
          )}
        </div>
        <div className="right-panel-body">
          <RightPanel
            activeTab={activeTab}
            setActiveTab={setActiveTab}
            selectedNode={selectedNode}
            decisions={decisions}
            stats={stats}
            onRunIntegration={handleIntegration}
            onUpdateDecision={handleUpdateDecision}
            onBuildRAG={handleBuildRAG}
            onRAGQuery={handleRAGQuery}
            ragStatus={ragStatus}
            ragAnswer={ragAnswer}
            chatHistory={chatHistory}
            onSendChat={handleSendChat}
            report={report}
            onGenerateReport={handleGenerateReport}
            onLoadReport={handleLoadReport}
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
