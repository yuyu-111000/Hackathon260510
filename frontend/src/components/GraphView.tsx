import { useMemo, useState, useCallback } from 'react';
import ReactECharts from 'echarts-for-react';
import type { GraphData, KnowledgeNode } from '../types';
import NodeDetailPopover from './NodeDetailPopover';

interface Props {
  graphData: GraphData | null;
  graphMode?: 'raw' | 'merged';
  onToggleMode?: () => void;
  hasMergedGraph?: boolean;
  onGenerateReport?: () => void;
  rawNodeCount?: number;
  mergedNodeCount?: number;
  onNodeSelect?: (node: KnowledgeNode) => void;
}

const COLORS = [
  '#3D6B4F', '#4A7B9B', '#B85450', '#C49B38', '#7B5EA7',
  '#5A8A6B', '#9B6B4A', '#6B8A4A', '#8B6BAA', '#4A8B7B',
];

/** Wrap long names for display */
function wrapName(name: string, maxChars: number = 10): string {
  if (name.length <= maxChars) return name;
  const lines: string[] = [];
  let remaining = name;
  while (remaining.length > 0) {
    if (remaining.length <= maxChars) {
      lines.push(remaining);
      break;
    }
    let breakAt = maxChars;
    const delimiters = ['，', '、', '的', '与', '和', '及', '（', ' ', '-'];
    for (const d of delimiters) {
      const idx = remaining.lastIndexOf(d, maxChars);
      if (idx > maxChars / 2) {
        breakAt = idx + 1;
        break;
      }
    }
    lines.push(remaining.slice(0, breakAt));
    remaining = remaining.slice(breakAt);
  }
  return lines.join('\n');
}

export default function GraphView({ graphData, graphMode = 'raw', onToggleMode, hasMergedGraph = false, onGenerateReport, onNodeSelect }: Props) {
  const [search, setSearch] = useState('');
  const [selectedNode, setSelectedNode] = useState<KnowledgeNode | null>(null);
  const [popoverPos, setPopoverPos] = useState<{ x: number; y: number } | null>(null);

  const option = useMemo(() => {
    if (!graphData || graphData.nodes.length === 0) return null;

    const searchLower = search.toLowerCase();
    const textbookIds = [...new Set(graphData.nodes.map(n => n.textbook_id))];
    const colorMap = new Map(textbookIds.map((id, i) => [id, COLORS[i % COLORS.length]]));

    // Find root nodes (never a target)
    const childSet = new Set(graphData.edges.map(e => e.target));
    const childrenMap = new Map<string, string[]>();
    graphData.edges.forEach(e => {
      if (!childrenMap.has(e.source)) childrenMap.set(e.source, []);
      childrenMap.get(e.source)!.push(e.target);
    });

    const rootIds = graphData.nodes
      .filter(n => !childSet.has(n.id))
      .map(n => n.id);

    // Assign positions: roots at center, children spread in all directions
    const positions = new Map<string, [number, number]>();
    const centerX = 500;
    const centerY = 400;

    if (rootIds.length === 1) {
      positions.set(rootIds[0], [centerX, centerY]);
    } else {
      // Spread roots in a circle
      const radius = 80;
      rootIds.forEach((id, i) => {
        const angle = (2 * Math.PI * i) / rootIds.length;
        positions.set(id, [
          centerX + radius * Math.cos(angle),
          centerY + radius * Math.sin(angle),
        ]);
      });
    }

    // BFS to assign positions to children - spread in all directions
    const visited = new Set(rootIds);
    const queue: { id: string; depth: number; angle: number; spread: number }[] = [];

    rootIds.forEach((rootId, rootIdx) => {
      const kids = childrenMap.get(rootId) || [];
      const baseAngle = rootIds.length === 1 ? 0 : (2 * Math.PI * rootIdx) / rootIds.length;
      kids.forEach((kidId, kidIdx) => {
        if (!visited.has(kidId)) {
          visited.add(kidId);
          const spread = Math.PI * 0.8; // spread angle per level
          const kidAngle = baseAngle - spread / 2 + (spread * (kidIdx + 1)) / (kids.length + 1);
          queue.push({ id: kidId, depth: 1, angle: kidAngle, spread: spread * 0.7 });
        }
      });
    });

    while (queue.length > 0) {
      const { id, depth, angle, spread } = queue.shift()!;
      const dist = 100 + depth * 130;
      const parentEdge = graphData.edges.find(e => e.target === id);
      const parentId = parentEdge?.source;
      const parentPos = parentId ? positions.get(parentId) : [centerX, centerY];
      const px = parentPos ? parentPos[0] : centerX;
      const py = parentPos ? parentPos[1] : centerY;

      positions.set(id, [
        px + dist * Math.cos(angle) * 0.5,
        py + dist * Math.sin(angle) * 0.5,
      ]);

      const kids = childrenMap.get(id) || [];
      kids.forEach((kidId, kidIdx) => {
        if (!visited.has(kidId)) {
          visited.add(kidId);
          const kidAngle = angle - spread / 2 + (spread * (kidIdx + 1)) / (kids.length + 1);
          queue.push({ id: kidId, depth: depth + 1, angle: kidAngle, spread: spread * 0.7 });
        }
      });
    }

    // Build nodes
    const nodes = graphData.nodes.map(n => {
      const matched = !search || n.name.toLowerCase().includes(searchLower) || n.definition.toLowerCase().includes(searchLower);
      const baseColor = colorMap.get(n.textbook_id) || '#3D6B4F';
      const isRoot = rootIds.includes(n.id);
      const pos = positions.get(n.id);

      const categorySymbol: string = (() => {
        const cat = (n.category || '').toLowerCase();
        if (cat.includes('核心概念') || cat.includes('core')) return 'circle';
        if (cat.includes('概念') || cat.includes('concept')) return 'roundRect';
        if (cat.includes('应用') || cat.includes('apply') || cat.includes('方法')) return 'triangle';
        if (cat.includes('原理') || cat.includes('principle')) return 'diamond';
        if (cat.includes('结构') || cat.includes('structure')) return 'rect';
        return 'circle';
      })();

      return {
        id: n.id,
        name: wrapName(n.name),
        x: pos ? pos[0] : undefined,
        y: pos ? pos[1] : undefined,
        symbol: categorySymbol,
        symbolSize: isRoot ? 20 : Math.max(8, Math.min(24, 6 + n.frequency * 2)),
        fixed: isRoot,
        itemStyle: {
          color: baseColor,
          opacity: matched ? 0.9 : 0.12,
          borderColor: n.status === 'merged' ? '#4A7B9B' :
                       n.status === 'removed' ? '#B85450' :
                       n.status === 'kept' ? '#3D6B4F' : baseColor,
          borderWidth: n.status !== 'raw' && matched ? 3 : matched ? 1 : 0,
          borderType: n.status === 'removed' ? 'dashed' : 'solid',
          shadowColor: matched && isRoot ? 'rgba(61, 107, 79, 0.3)' : 'transparent',
          shadowBlur: matched && isRoot ? 12 : 0,
        },
        label: {
          show: matched,
          position: 'right',
          fontSize: isRoot ? 13 : 10,
          color: '#2C2418',
          fontFamily: isRoot ? 'Fraunces, serif' : 'Epilogue, sans-serif',
          fontWeight: isRoot ? 700 : 500,
          overflow: 'break',
          width: 80,
          distance: 6,
        },
        category: n.category,
        _raw: n,
      };
    });

    // Build edges
    const edges = graphData.edges.map(e => ({
      source: e.source,
      target: e.target,
      lineStyle: {
        color: '#D4C9B8',
        width: 1,
        curveness: 0.2,
      },
    }));

    return {
      backgroundColor: 'transparent',
      tooltip: {
        backgroundColor: '#FFFFFF',
        borderColor: '#D4C9B8',
        borderWidth: 1,
        borderRadius: 8,
        textStyle: {
          color: '#2C2418',
          fontFamily: 'Epilogue, sans-serif',
          fontSize: 12,
        },
        formatter: (p: any) => {
          if (p.dataType === 'node') {
            const n = p.data._raw;
            if (!n) return '';
            const def = n.definition.length > 100 ? n.definition.slice(0, 100) + '...' : n.definition;
            let tip = `<span style="color:#3D6B4F;font-weight:700;font-family:Fraunces,serif;font-size:14px">${n.name}</span>`;
            if (n.category) tip += `<br/><span style="color:#6B5D4F;font-weight:600">${n.category}</span>`;
            if (n.chapter) tip += `<br/><span style="color:#9B8E80">${n.chapter}${n.page ? ' · 第' + n.page + '页' : ''}</span>`;
            tip += `<br/><span style="color:#5A5040;margin-top:4px;display:inline-block">${def}</span>`;
            return tip;
          }
          return '';
        },
      },
      series: [{
        type: 'graph',
        layout: 'none',
        roam: true,
        draggable: true,
        data: nodes,
        links: edges,
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: 5,
        emphasis: {
          focus: 'adjacency',
          itemStyle: {
            shadowColor: 'rgba(61, 107, 79, 0.3)',
            shadowBlur: 12,
          },
          lineStyle: { width: 2, color: '#3D6B4F' },
        },
      }],
    };
  }, [graphData, search]);

  const handleClick = useCallback((params: any) => {
    if (params.dataType === 'node' && params.data?._raw) {
      setSelectedNode(params.data._raw);
      setPopoverPos({ x: params.event?.offsetX || 300, y: params.event?.offsetY || 200 });
      if (onNodeSelect) onNodeSelect(params.data._raw);
    }
  }, [onNodeSelect]);

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        fontFamily: 'Epilogue, sans-serif',
      }}>
        <div style={{ textAlign: 'center' }}>
          <p style={{
            fontFamily: 'Fraunces, serif',
            fontSize: '20px',
            fontWeight: 700,
            color: '#3D6B4F',
            marginBottom: '8px',
          }}>知识思维导图</p>
          <p style={{ fontSize: '13px', color: '#9B8E80' }}>
            上传并解析教材后，点击"构建图谱"查看
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="graph-toolbar">
        <input
          placeholder="搜索知识点..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        {hasMergedGraph && onToggleMode && (
          <button
            className="btn btn-sm"
            onClick={onToggleMode}
            style={{
              background: graphMode === 'merged' ? '#3D6B4F' : '#EDE6D8',
              color: graphMode === 'merged' ? 'white' : '#2C2418',
              border: '1px solid #D4C9B8',
              borderRadius: '8px',
              padding: '8px 14px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
            }}
          >
            {graphMode === 'merged'
              ? `整合后 (${graphData.nodes.length}节点)`
              : `整合前 (${graphData.nodes.length}节点)`}
          </button>
        )}
      </div>

      <div style={{
        display: 'flex', gap: '12px', padding: '4px 12px',
        fontSize: '10px', color: '#9B8E80', fontFamily: 'Epilogue, sans-serif',
        borderBottom: '1px solid #EDE6D8',
      }}>
        <span>知识点: {graphData.nodes.length}</span>
        <span>关系: {graphData.edges.length}</span>
        <span style={{ color: '#B8A88A' }}>点击节点查看详情 · 拖拽移动</span>
        {graphMode === 'merged' && <>
          <span style={{ color: '#4A7B9B' }}>● 已合并</span>
          <span style={{ color: '#B85450' }}>● 已移除</span>
          <span style={{ color: '#3D6B4F' }}>● 已保留</span>
        </>}
      </div>

      <ReactECharts
        option={option}
        style={{ height: '100%', width: '100%' }}
        onEvents={{ click: handleClick }}
      />

      {onGenerateReport && (
        <button
          onClick={onGenerateReport}
          style={{
            position: 'absolute',
            bottom: '16px',
            right: '16px',
            background: '#3D6B4F',
            color: 'white',
            border: 'none',
            borderRadius: '10px',
            padding: '10px 18px',
            fontSize: '12px',
            fontWeight: 600,
            fontFamily: 'Epilogue, sans-serif',
            cursor: 'pointer',
            boxShadow: '0 2px 12px rgba(61,107,79,0.3)',
            zIndex: 10,
          }}
        >
          生成报告
        </button>
      )}

      <NodeDetailPopover
        node={selectedNode}
        position={popoverPos}
        onClose={() => { setSelectedNode(null); setPopoverPos(null); }}
      />
    </>
  );
}
