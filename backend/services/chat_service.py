import re
import json
import uuid
from datetime import datetime
from backend.schemas import (
    ChatResponse, ChatMessage, MergeDecision, DecisionAction
)
from backend.routers import integration as integration_router
from backend.routers import graph as graph_router
from backend import config


class ChatService:
    def __init__(self):
        self.history: list[ChatMessage] = []

    def process(self, message: str) -> ChatResponse:
        self.history.append(ChatMessage(
            message_id=str(uuid.uuid4())[:8],
            role="teacher",
            content=message,
            timestamp=datetime.now().isoformat(),
        ))

        intent, targets, decision_id = self._parse_intent(message)

        reply = ""
        updated_decisions = []
        requires_graph_update = False

        if intent == "explain":
            decisions = integration_router._decisions
            if decisions:
                reply = self._explain(message, targets)
            else:
                # No decisions yet, treat as conversational
                reply = self._conversational_reply(message)
        elif intent in ("keep", "remove", "split", "merge"):
            decisions = integration_router._decisions
            if decisions:
                if intent == "keep":
                    reply, updated, requires_graph_update = self._keep(targets, decision_id)
                elif intent == "remove":
                    reply, updated, requires_graph_update = self._remove(targets, decision_id)
                elif intent == "split":
                    reply, updated, requires_graph_update = self._split(targets, decision_id)
                else:
                    reply, updated, requires_graph_update = self._merge_targets(targets)
                updated_decisions = updated
            else:
                reply = self._conversational_reply(message)
        elif intent == "query":
            reply = self._query_knowledge(targets)
        else:
            reply = self._conversational_reply(message)

        self.history.append(ChatMessage(
            message_id=str(uuid.uuid4())[:8],
            role="system",
            content=reply,
            timestamp=datetime.now().isoformat(),
        ))

        return ChatResponse(
            reply=reply,
            intent=intent,
            updated_decisions=updated_decisions,
            requires_graph_update=requires_graph_update,
        )

    def get_history(self) -> list[ChatMessage]:
        return self.history

    def _node_name_matches(self, target: str, decision: MergeDecision) -> bool:
        """Check if target matches any node name in the decision's affected nodes."""
        if target in (decision.reason or ""):
            return True
        if any(target in nid for nid in decision.affected_nodes):
            return True
        for graph_source in [graph_router.get_current_graph(), graph_router._merged_graph]:
            if not graph_source.nodes:
                continue
            node_map = {n.id: n for n in graph_source.nodes}
            for nid in decision.affected_nodes:
                node = node_map.get(nid)
                if not node:
                    continue
                if (target in node.name or target in node.definition or
                    target in node.chapter or
                    any(target in alias for alias in node.aliases)):
                    return True
        return False

    def _parse_intent(self, message: str) -> tuple[str, list[str], str | None]:
        targets = self._extract_targets(message)
        decision_id = self._extract_decision_id(message)

        if re.search(r"为什么|原因|解释|Why|怎么回事", message):
            return "explain", targets, decision_id
        if re.search(r"保留|不要删|别删除|请保留|恢复", message):
            return "keep", targets, decision_id
        if re.search(r"删除|去掉|移除|不要", message):
            return "remove", targets, decision_id
        if re.search(r"分开|拆开|拆分|不应该合并|不该合|分出来", message):
            return "split", targets, decision_id
        if re.search(r"合并|整合|合到一起", message):
            return "merge", targets, decision_id
        if re.search(r"什么是|介绍|解释一下|告诉我|说说|讲讲|什么是|查询|查一下|找", message):
            return "query", targets, decision_id

        return "unknown", targets, decision_id

    def _extract_targets(self, message: str) -> list[str]:
        targets = []

        quoted = re.findall(r"[""「」『』](.+?)[""「」『』]", message)
        targets.extend(quoted)

        if not targets:
            cleaned = message
            action_words = ["请", "保留", "删除", "合并", "分开", "拆开", "拆分", "为什么",
                            "不应该", "不该", "可以", "需要", "觉得", "认为", "把", "将",
                            "恢复", "不要", "去", "掉", "移除", "到", "一起",
                            "什么是", "介绍", "解释", "一下", "告诉", "说说", "讲讲",
                            "查询", "查", "找", "的", "了", "吗", "呢", "吧", "啊"]
            for w in sorted(action_words, key=len, reverse=True):
                cleaned = cleaned.replace(w, " ")

            words = re.findall(r"[一-鿿]{2,8}", cleaned)
            skip_words = {"一个", "概念", "知识", "点", "教材", "这些", "那些", "什么",
                          "怎么", "如何", "可以", "需要", "应该", "可能"}
            targets = [w for w in words if w not in skip_words and len(w) >= 2][:5]

        return targets

    def _extract_decision_id(self, message: str) -> str | None:
        match = re.search(r"(merge|keep|remove)_\d+", message)
        return match.group() if match else None

    def _explain(self, message: str, targets: list[str]) -> str:
        decisions = integration_router._decisions

        if not decisions:
            return "当前还没有整合决策。请先在左侧点击「跨教材整合」按钮运行分析。"

        for target in targets:
            for d in decisions:
                if self._node_name_matches(target, d):
                    return f"决策 {d.decision_id}：{d.reason}\n置信度：{d.confidence}\n涉及节点：{', '.join(d.affected_nodes)}"

        return f"未找到与「{'、'.join(targets)}」相关的整合决策。\n\n当前共有 {len(decisions)} 项决策，您可以：\n• 输入「查看所有决策」了解当前整合状态\n• 确认知识点名称是否正确"

    def _keep(self, targets: list[str], decision_id: str | None) -> tuple[str, list[MergeDecision], bool]:
        decisions = integration_router._decisions
        updated = []

        if not decisions:
            return "当前还没有整合决策。请先运行跨教材整合分析，然后再进行修改。", [], False

        for d in decisions:
            should_update = False

            if decision_id and d.decision_id == decision_id:
                should_update = True
            elif d.action == DecisionAction.REMOVE:
                for target in targets:
                    if self._node_name_matches(target, d):
                        should_update = True
                        break

            if should_update:
                d.action = DecisionAction.KEEP
                d.status = "active"
                updated.append(d)

        if updated:
            names = [", ".join(d.affected_nodes[:2]) for d in updated]
            return f"已将 {len(updated)} 项决策修改为保留：{'; '.join(names)}", updated, True

        return f"未找到与「{'、'.join(targets)}」相关的需要保留的决策。请确认知识点名称。", [], False

    def _remove(self, targets: list[str], decision_id: str | None) -> tuple[str, list[MergeDecision], bool]:
        decisions = integration_router._decisions
        updated = []

        if not decisions:
            return "当前还没有整合决策。请先运行跨教材整合分析。", [], False

        for d in decisions:
            should_update = False

            if decision_id and d.decision_id == decision_id:
                should_update = True
            else:
                for target in targets:
                    if self._node_name_matches(target, d):
                        should_update = True
                        break

            if should_update:
                d.action = DecisionAction.REMOVE
                updated.append(d)

        if updated:
            return f"已将 {len(updated)} 项决策修改为删除", updated, True

        return f"未找到与「{'、'.join(targets)}」相关的决策。", [], False

    def _split(self, targets: list[str], decision_id: str | None) -> tuple[str, list[MergeDecision], bool]:
        decisions = integration_router._decisions
        updated = []

        if not decisions:
            return "当前还没有整合决策。请先运行跨教材整合分析。", [], False

        for d in decisions:
            if d.action != DecisionAction.MERGE:
                continue

            should_split = False
            if decision_id and d.decision_id == decision_id:
                should_split = True
            else:
                for target in targets:
                    if self._node_name_matches(target, d):
                        should_split = True
                        break

            if should_split:
                d.action = DecisionAction.KEEP
                d.status = "split_by_teacher"
                updated.append(d)

        if updated:
            return f"已将 {len(updated)} 项合并决策拆分为独立保留", updated, True

        return f"未找到与「{'、'.join(targets)}」相关的合并决策。", [], False

    def _merge_targets(self, targets: list[str]) -> tuple[str, list[MergeDecision], bool]:
        if len(targets) < 2:
            return "请提供至少两个知识点名称来进行合并。例如：「合并 线粒体 和 叶绿体」", [], False

        return f"已收到合并请求：{' + '.join(targets)}。系统将在下次整合时处理。", [], False

    def _query_knowledge(self, targets: list[str]) -> str:
        """Look up knowledge from the graph."""
        if not targets:
            return "请告诉我要查询的知识点名称。例如：「什么是线粒体」"

        for graph_source in [graph_router.get_current_graph(), graph_router._merged_graph]:
            if not graph_source.nodes:
                continue
            for node in graph_source.nodes:
                for target in targets:
                    if target in node.name or target in node.definition or \
                       any(target in alias for alias in node.aliases):
                        result = f"**{node.name}**\n\n"
                        result += f"定义：{node.definition}\n"
                        result += f"分类：{node.category}\n"
                        result += f"来源：{node.chapter} · 第{node.page}页\n"
                        if node.aliases:
                            result += f"别名：{', '.join(node.aliases)}\n"
                        if node.source_quote:
                            result += f"原文：{node.source_quote}\n"
                        return result

        return f"在当前知识图谱中未找到「{'、'.join(targets)}」相关内容。\n\n请确认：\n• 知识点名称是否正确\n• 是否已上传并解析了相关教材\n• 是否已构建知识图谱"

    def _conversational_reply(self, message: str) -> str:
        """Always try LLM first for any unrecognized message. Fall back to rule-based."""
        # Always try LLM for conversational replies
        if config.LLM_API_KEY:
            try:
                return self._llm_reply(message)
            except Exception:
                pass

        # Rule-based fallback (only when no LLM available)
        msg = message.strip()

        if re.search(r"^(你好|hi|hello|hey|嗨|您好|哈喽)", msg, re.IGNORECASE):
            return "你好！我是 EduFusion 知识整合助手。有什么可以帮您的？\n\n您可以问我任何关于学科知识的问题，也可以让我帮您管理整合决策。"

        if re.search(r"(谢谢|感谢|thanks|thank)", msg, re.IGNORECASE):
            return "不客气！有其他问题随时问我。"

        if re.search(r"(帮助|help|怎么用|功能|能做什么)", msg, re.IGNORECASE):
            return "我能帮您：\n\n1. 回答学科知识问题\n2. 查询知识点详情 —「什么是线粒体」\n3. 保留/删除/拆分整合决策\n4. 解释整合原因\n\n随便聊，不限格式。"

        if re.search(r"(查看|列出|所有|全部).*(决策|整合|状态)", msg):
            decisions = integration_router._decisions
            if not decisions:
                return "当前还没有整合决策。需要先运行跨教材整合分析才会产生决策。"
            lines = [f"当前共有 {len(decisions)} 项整合决策：\n"]
            for d in decisions[:10]:
                action_label = {"merge": "合并", "keep": "保留", "remove": "删除"}.get(d.action.value, d.action.value)
                lines.append(f"• {d.decision_id}: {action_label} — {', '.join(d.affected_nodes[:2])}")
            if len(decisions) > 10:
                lines.append(f"\n... 还有 {len(decisions) - 10} 项")
            return "\n".join(lines)

        # Try to query knowledge graph with extracted targets
        targets = self._extract_targets(msg)
        if targets:
            result = self._query_knowledge(targets)
            if "未找到" not in result:
                return result

        # Last resort: acknowledge and guide
        return "抱歉，当前未配置大模型 API，我只能回答知识图谱中已有的内容。\n\n配置 LLM API Key 后，我可以回答任何学科问题。"

    def _llm_reply(self, message: str) -> str:
        """Use LLM for conversational reply."""
        from openai import OpenAI

        client = OpenAI(base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY)

        # Build context
        context_parts = []

        decisions = integration_router._decisions
        if decisions:
            context_parts.append(f"当前有 {len(decisions)} 项整合决策。")

        graph = graph_router.get_current_graph()
        if graph.nodes:
            node_names = [n.name for n in graph.nodes[:20]]
            context_parts.append(f"知识图谱包含 {len(graph.nodes)} 个知识点，如：{', '.join(node_names)}")

        context = "\n".join(context_parts) if context_parts else "当前没有加载任何知识数据。"

        response = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[
                {"role": "system", "content": f"""你是 EduFusion 学科知识整合智能体的教师对话助手。

你的职责：
1. 回答教师关于知识点的提问
2. 帮助教师理解和修改整合决策
3. 用简洁专业的语言回答

当前状态：
{context}

回答要求：
- 简洁、专业、有帮助
- 如果教师的指令涉及修改决策（保留/删除/拆分/合并），请确认理解并执行
- 不要自我介绍是什么模型，不要提及自己的身份或来源，直接回答问题"""},
                {"role": "user", "content": message},
            ],
            temperature=0.3,
            max_tokens=500,
        )

        return response.choices[0].message.content or "抱歉，我暂时无法回答这个问题。"
