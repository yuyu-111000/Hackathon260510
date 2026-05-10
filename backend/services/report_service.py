from datetime import datetime
from collections import Counter
from backend.schemas import (
    MergeDecision, IntegrationStats, GraphResponse,
    DecisionAction
)


class ReportService:
    def generate(
        self,
        decisions: list[MergeDecision],
        stats: IntegrationStats,
        graph: GraphResponse,
    ) -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        merge_decisions = [d for d in decisions if d.action == DecisionAction.MERGE]
        keep_decisions = [d for d in decisions if d.action == DecisionAction.KEEP]
        remove_decisions = [d for d in decisions if d.action == DecisionAction.REMOVE]

        report = f"""# 教材知识整合报告

> 生成时间：{now}
> 生成系统：EduFusion Agent - 学科知识整合智能体

---

## 1. 整合概览

| 指标 | 数值 |
|------|------|
| 原始知识点数量 | {stats.original_node_count} |
| 整合后知识点数量 | {stats.merged_node_count} |
| 原始内容总字数 | {stats.original_total_chars:,} |
| 整合后内容字数 | {stats.compressed_chars:,} |
| 压缩比 | {stats.compression_ratio:.1f}% |
| 是否满足 ≤30% 要求 | {'✅ 是' if stats.compression_ratio <= 30 else '❌ 否'} |

---

## 2. 整合决策摘要

| 决策类型 | 数量 |
|----------|------|
| 合并 (merge) | {stats.merge_count} |
| 保留 (keep) | {stats.keep_count} |
| 删除 (remove) | {stats.remove_count} |
| **总计** | {len(decisions)} |

---

## 3. 知识图谱统计

| 指标 | 整合前 | 整合后 |
|------|--------|--------|
| 节点数 | {stats.original_node_count} | {stats.merged_node_count} |
| 关系数 | {len(graph.edges)} | - |

---

## 4. 重点整合案例

"""
        if merge_decisions:
            for i, d in enumerate(merge_decisions[:5]):
                report += f"""### 案例 {i + 1}

- **决策ID**: {d.decision_id}
- **动作**: 合并 (merge)
- **涉及节点**: {', '.join(d.affected_nodes[:5])}
- **结果节点**: {d.result_node or 'N/A'}
- **理由**: {d.reason}
- **置信度**: {d.confidence:.2f}

"""
        else:
            report += "暂无合并决策案例。\n\n"

        report += f"""---

## 5. 知识点重要性评分

> 公式: importance = 0.35 × frequency + 0.25 × graph_degree + 0.20 × chapter_weight + 0.20 × citation_support

| 知识点 | 频次 | 图谱度数 | 章节权重 | 引用支撑 | 综合评分 |
|--------|------|----------|----------|----------|----------|
"""
        importance_data = self._compute_importance(graph)
        for name, score_data in importance_data[:10]:
            report += f"| {name} | {score_data['freq']:.0f} | {score_data['degree']:.0f} | {score_data['chapter']:.2f} | {score_data['citation']:.2f} | **{score_data['total']:.2f}** |\n"

        report += f"""
---

## 6. 教学完整性说明

本系统通过以下机制保障教学逻辑链路的完整性：

1. **前置依赖保护**: 前置依赖关系链上的核心知识点不会被删除
2. **高频知识点优先保留**: 出现频次高的知识点在压缩时获得更高权重
3. **教师可干预机制**: 教师可以通过自然语言对话修改任何整合决策
4. **保守合并策略**: 系统采用高阈值（相似度≥0.90）自动合并，模糊区间（0.82-0.90）保守保留
5. **完整溯源**: 每个保留的知识点都携带原文引用，便于教师验证

### 重要性评分公式

```
importance = 0.35 × frequency + 0.25 × graph_degree + 0.20 × chapter_weight + 0.20 × citation_support
```

### 压缩控制策略

- 目标压缩比: 25%~28%（内部目标），对外展示 ≤30%
- 超过30%时自动执行：删除低频节点、缩短定义、精简引用

---

*本报告由 EduFusion Agent 自动生成*
"""
        return report

    def generate_single(self, graph: GraphResponse) -> str:
        """Generate a report for a single textbook (no integration)."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        textbook_ids = list(set(n.textbook_id for n in graph.nodes))
        chapters = list(set(n.chapter for n in graph.nodes if n.chapter))
        categories = {}
        for n in graph.nodes:
            categories[n.category] = categories.get(n.category, 0) + 1

        report = f"""# 教材知识图谱报告

> 生成时间：{now}
> 生成系统：EduFusion Agent - 学科知识整合智能体

---

## 1. 概览

| 指标 | 数值 |
|------|------|
| 教材数量 | {len(textbook_ids)} |
| 知识点总数 | {len(graph.nodes)} |
| 关系总数 | {len(graph.edges)} |
| 章节数 | {len(chapters)} |

---

## 2. 知识点分类分布

| 分类 | 数量 |
|------|------|
"""
        for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
            report += f"| {cat} | {count} |\n"

        report += f"""
---

## 3. 重要知识点 TOP 10

"""
        importance_data = self._compute_importance(graph)
        for i, (name, score_data) in enumerate(importance_data[:10]):
            report += f"{i+1}. **{name}** — 综合评分 {score_data['total']:.2f} (频次{score_data['freq']:.0f}, 度数{score_data['degree']:.0f})\n"

        report += f"""
---

## 4. 知识点关联

共 {len(graph.edges)} 条关系，涉及以下类型：

"""
        rel_types = {}
        for e in graph.edges:
            rt = e.relation_type.value if hasattr(e.relation_type, 'value') else str(e.relation_type)
            rel_types[rt] = rel_types.get(rt, 0) + 1
        for rt, count in sorted(rel_types.items(), key=lambda x: -x[1]):
            report += f"- **{rt}**: {count} 条\n"

        report += f"""
---

*本报告由 EduFusion Agent 自动生成*
"""
        return report

    def _compute_importance(self, graph: GraphResponse) -> list[tuple[str, dict]]:
        """Compute importance scores for all nodes in the graph."""
        # Compute graph degree (number of edges per node)
        degree_count: Counter[str] = Counter()
        for edge in graph.edges:
            degree_count[edge.source] += 1
            degree_count[edge.target] += 1

        # Chapter weight: nodes from chapters with more nodes get slightly higher weight
        chapter_count: Counter[str] = Counter()
        for n in graph.nodes:
            chapter_count[n.chapter] += 1

        max_freq = max((n.frequency for n in graph.nodes), default=1) or 1
        max_degree = max((degree_count.get(n.id, 0) for n in graph.nodes), default=1) or 1

        results = []
        for n in graph.nodes:
            freq_norm = n.frequency / max_freq
            degree_norm = degree_count.get(n.id, 0) / max_degree
            chapter_norm = 1.0 / max(chapter_count.get(n.chapter, 1), 1)  # fewer nodes = higher weight
            citation_norm = 1.0 if n.source_quote else 0.0

            total = (0.35 * freq_norm + 0.25 * degree_norm +
                     0.20 * chapter_norm + 0.20 * citation_norm)

            results.append((n.name, {
                'freq': n.frequency,
                'degree': degree_count.get(n.id, 0),
                'chapter': chapter_norm,
                'citation': citation_norm,
                'total': total,
            }))

        results.sort(key=lambda x: x[1]['total'], reverse=True)
        return results
