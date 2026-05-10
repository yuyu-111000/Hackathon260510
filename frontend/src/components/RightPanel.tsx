import type {
  KnowledgeNode, MergeDecision, IntegrationStats,
  RAGResponse, ChatMessage
} from '../types';
import NodeDetailPanel from './NodeDetailPanel';
import IntegrationPanel from './IntegrationPanel';
import RagPanel from './RagPanel';
import ChatPanel from './ChatPanel';
import ReportPanel from './ReportPanel';

interface Props {
  activeTab: 'node' | 'integration' | 'rag' | 'chat' | 'report';
  setActiveTab: (tab: Props['activeTab']) => void;
  selectedNode: KnowledgeNode | null;
  decisions: MergeDecision[];
  stats: IntegrationStats | null;
  onRunIntegration: () => void;
  onUpdateDecision: (id: string, action: string) => void;
  onBuildRAG: () => void;
  onRAGQuery: (q: string) => void;
  ragStatus: { indexed_books: number; chunk_count: number; status: string } | null;
  ragAnswer: RAGResponse | null;
  chatHistory: ChatMessage[];
  onSendChat: (msg: string) => void;
  report: string;
  onGenerateReport: () => void;
  onLoadReport: () => void;
}

const tabs = [
  { key: 'node' as const, label: '详情' },
  { key: 'integration' as const, label: '整合' },
  { key: 'rag' as const, label: 'RAG' },
  { key: 'chat' as const, label: '对话' },
  { key: 'report' as const, label: '报告' },
];

export default function RightPanel(props: Props) {
  return (
    <>
      <div className="tab-bar">
        {tabs.map(t => (
          <button
            key={t.key}
            className={props.activeTab === t.key ? 'active' : ''}
            onClick={() => props.setActiveTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="tab-content">
        {props.activeTab === 'node' && <NodeDetailPanel node={props.selectedNode} />}
        {props.activeTab === 'integration' && (
          <IntegrationPanel
            decisions={props.decisions}
            stats={props.stats}
            onRunIntegration={props.onRunIntegration}
            onUpdateDecision={props.onUpdateDecision}
          />
        )}
        {props.activeTab === 'rag' && (
          <RagPanel
            onBuildRAG={props.onBuildRAG}
            onQuery={props.onRAGQuery}
            status={props.ragStatus}
            answer={props.ragAnswer}
          />
        )}
        {props.activeTab === 'chat' && (
          <ChatPanel
            history={props.chatHistory}
            onSend={props.onSendChat}
          />
        )}
        {props.activeTab === 'report' && (
          <ReportPanel
            report={props.report}
            onGenerate={props.onGenerateReport}
            onLoad={props.onLoadReport}
          />
        )}
      </div>
    </>
  );
}
