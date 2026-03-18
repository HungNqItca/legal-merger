"""
merge_engine.py — Áp dụng danh sách Amendment vào cây văn bản gốc.
"""

import re
from copy import deepcopy
from typing import Optional

from .models import Node, NodeType, Amendment, OperationType, _ids_match


class MergeEngine:

    def __init__(self, articles: dict, order: list):
        self.articles  = deepcopy(articles)
        self.order     = list(order)
        self.merge_log = []

    def apply_amendments(self, amendments: list):
        for amend in amendments:
            self._apply(amend)
        return self.articles

    def get_ordered_articles(self) -> list:
        return [self.articles[aid] for aid in self.order if aid in self.articles]

    # ─────────────────────────────────────────────────────
    # Dispatch theo OperationType
    # ─────────────────────────────────────────────────────

    def _apply(self, a: Amendment):
        op       = a.operation
        tid      = a.target_id
        log      = {"target_scope": a.target_scope or tid, "source": a.source_doc}
        citation = a.citation_label()

        if op in (OperationType.MODIFY, OperationType.MODIFY_AND_INSERT):
            node = self._find_node_in_context(tid, a.parent_article_id, a.parent_clause_id, a.parent_point_id)
            if node:
                a.original_content = node.get_text()
                a.node_title       = self._node_scope_label(node, a.target_scope)
                self._replace_content(node, a.content)
                node.add_citation(citation)
                action_label = ("SỬA ĐỔI, BỔ SUNG"
                                if op == OperationType.MODIFY_AND_INSERT else "SỬA ĐỔI")
                node.add_change(f"{action_label.lower()} theo {a.source_doc}")
                self.merge_log.append({
                    "action": action_label, "citation": citation,
                    "original_content": a.original_content,
                    "new_content": a.content, "node_title": a.node_title,
                    **log})
            else:
                self._warn(
                    f"Không tìm thấy '{a.target_scope or tid}'"
                    + (f" trong {a.parent_article_id}" if a.parent_article_id else "")
                    + " để sửa đổi — bỏ qua")

        elif op == OperationType.RENAME:
            node = self._find_node_in_context(tid, a.parent_article_id, a.parent_clause_id, a.parent_point_id)
            if node:
                a.original_content = node.label
                a.node_title       = self._node_scope_label(node, a.target_scope)
                old_label = node.label
                new_name  = a.content.strip().strip('""\u201c\u201d').strip()
                m = re.match(r'^((?:Điều|ĐIỀU)\s+\d+[a-zđ]?)[\.:\s]*',
                             node.label, re.IGNORECASE)
                if m and new_name:
                    node.label = f"{m.group(1).strip()}. {new_name}"
                elif new_name:
                    node.label = new_name
                node.add_citation(citation)
                node.add_change(f"Đổi tên theo {a.source_doc}")
                self.merge_log.append({
                    "action": "ĐỔI TÊN", "citation": citation,
                    "original_content": old_label, "new_content": node.label,
                    "node_title": a.node_title, **log})
            else:
                self._warn(f"Không tìm thấy '{a.target_scope or tid}' để đổi tên — bỏ qua")

        elif op == OperationType.DELETE:
            node = self._find_node_in_context(tid, a.parent_article_id, a.parent_clause_id, a.parent_point_id)
            if node:
                a.original_content = node.get_text()
                a.node_title       = self._node_scope_label(node, a.target_scope)
                node.is_deleted = True
                node.add_citation(citation)
                node.add_change(f"Bãi bỏ theo {a.source_doc}")
                self.merge_log.append({
                    "action": "BÃI BỎ", "citation": citation,
                    "original_content": a.original_content,
                    "new_content": "(bãi bỏ)", "node_title": a.node_title, **log})
            else:
                self._warn(
                    f"Không tìm thấy '{a.target_scope or tid}'"
                    + (f" trong {a.parent_article_id}" if a.parent_article_id else "")
                    + " để bãi bỏ — bỏ qua")

        elif op == OperationType.INSERT:
            new_node = self._insert_node(a)
            if new_node:
                new_node.add_citation(citation)
                new_node.add_change(f"Bổ sung mới từ {a.source_doc}")
            self.merge_log.append({
                "action": "BỔ SUNG", "citation": citation,
                "original_content": "(mới thêm — chưa có trong văn bản gốc)",
                "new_content": a.content,
                "node_title": self._format_scope_label(a.target_scope or a.target_id),
                **log})

        elif op == OperationType.REPLACE:
            node = self._find_node_in_context(tid, a.parent_article_id, a.parent_clause_id, a.parent_point_id)
            if node:
                node_text = node.get_text()
                # Chuẩn hoá newline → space để xử lý từ bị PDF ngắt dòng giữa chừng
                node_text_flat = node_text.replace('\n', ' ')
                if a.old_phrase.lower() not in node_text_flat.lower():
                    self._warn(
                        f'Cụm từ "{a.old_phrase}" không tìm thấy trong '
                        f'"{a.target_scope or tid}" — bỏ qua (đã được thay trước đó?)')
                else:
                    a.original_content = self._extract_sentence_with_phrase(
                        node_text_flat, a.old_phrase)
                    a.node_title = self._node_scope_label(node, a.target_scope)
                    self._replace_phrase(node, a.old_phrase, a.new_phrase)
                    new_sentence = self._extract_sentence_with_phrase(
                        node.get_text().replace('\n', ' '), a.new_phrase)
                    node.add_citation(citation)
                    node.add_change(
                        f'Thay "{a.old_phrase}" → "{a.new_phrase}" theo {a.source_doc}')
                    self.merge_log.append({
                        "action": "THAY CỤM TỪ",
                        "from": a.old_phrase, "to": a.new_phrase,
                        "citation": citation,
                        "original_content": a.original_content,
                        "new_content": new_sentence,
                        "node_title": a.node_title, **log})
            else:
                self._warn(
                    f"Không tìm thấy '{a.target_scope or tid}'"
                    + (f" trong {a.parent_article_id}" if a.parent_article_id else "")
                    + " để thay cụm từ — bỏ qua")

    # ─────────────────────────────────────────────────────
    # Tìm node
    # ─────────────────────────────────────────────────────

    def _find_node(self, target_id: str) -> Optional[Node]:
        for art in self.articles.values():
            n = art.find(target_id)
            if n:
                return n
        return None

    def _find_node_in_context(self, target_id: str,
                               parent_article_id: str = "",
                               parent_clause_id:  str = "",
                               parent_point_id:   str = "") -> Optional[Node]:
        """Tìm node có ngữ cảnh cha để tránh tìm nhầm.

        Nếu parent_article_id không tìm thấy chính xác, thử tìm gần đúng
        (bỏ qua suffix chữ cái) trước khi fallback về tìm toàn cục.
        """
        if parent_article_id:
            parent = self._find_node(parent_article_id)
            # Fallback: thử tìm gần đúng (ví dụ "Điều 3a" → "Điều 3")
            if parent is None:
                base_id = re.sub(r'([Đđ]iều\s+\d+)[a-zđ]', r'\1', parent_article_id,
                                 flags=re.IGNORECASE)
                if base_id != parent_article_id:
                    parent = self._find_node(base_id)
            if parent:
                if parent_clause_id:
                    clause_node = parent.find(parent_clause_id)
                    if clause_node:
                        if parent_point_id:
                            point_node = clause_node.find(parent_point_id)
                            if point_node:
                                found = point_node.find(target_id)
                                if found:
                                    return found
                        found = clause_node.find(target_id)
                        if found:
                            return found
                found = parent.find(target_id)
                if found:
                    return found
                return None
        return self._find_node(target_id)

    def _find_parent_and_index(self, target_id: str):
        for art in self.articles.values():
            res = self._search_parent(art, target_id)
            if res[0]:
                return res
        return None, -1

    def _search_parent(self, node: Node, target_id: str):
        for i, child in enumerate(node.children):
            if _ids_match(child.node_id, target_id):
                return node, i
            res = self._search_parent(child, target_id)
            if res[0]:
                return res
        return None, -1

    # ─────────────────────────────────────────────────────
    # Thao tác trên node
    # ─────────────────────────────────────────────────────

    def _replace_content(self, node: Node, new_content: str):
        lines = new_content.splitlines() if new_content else []
        node.label      = lines[0] if lines else node.label
        node.body_lines = lines[1:] if len(lines) > 1 else []
        node.children   = []

    def _replace_phrase(self, node: Node, old: str, new: str):
        """
        Thay cụm từ trong toàn cây node.
        - Dùng negative lookahead khi old là prefix của new để tránh double-apply.
        - Nối body_lines thành chuỗi phẳng trước khi thay để xử lý cụm từ bị
          PDF ngắt dòng giữa chừng (ví dụ: "Hệ thống thanh toán\nđiện tử...").
        """
        node.label = self._subst_phrase(node.label, old, new)

        if node.body_lines:
            # Nối các dòng, thay trên chuỗi phẳng, lưu lại thành 1 dòng nếu có thay đổi
            flat     = ' '.join(node.body_lines)
            replaced = self._subst_phrase(flat, old, new)
            if replaced != flat:
                node.body_lines = [replaced]
            else:
                node.body_lines = [self._subst_phrase(l, old, new) for l in node.body_lines]

        for child in node.children:
            self._replace_phrase(child, old, new)

    def _subst_phrase(self, text: str, old: str, new: str) -> str:
        """Thay old→new trong text, có negative lookahead khi old là prefix của new."""
        if new.startswith(old) and new != old:
            suffix  = re.escape(new[len(old):])
            pattern = re.compile(re.escape(old) + r'(?!' + suffix + r')')
            return pattern.sub(new, text)
        return text.replace(old, new)

    def _insert_node(self, a: Amendment) -> Optional[Node]:
        ntype    = self._guess_node_type(a.target_id)
        new_node = self._build_node(a.target_id, ntype, a.content, a.source_doc)

        if ntype == NodeType.ARTICLE:
            existing = self._find_node(a.target_id)
            insert_into_existing = (
                existing is not None and
                (not a.insert_after or _ids_match(a.insert_after, a.target_id))
            )
            if insert_into_existing:
                existing.children.append(new_node)
                return new_node
            after = a.insert_after
            if after and after in self.order:
                idx = self.order.index(after) + 1
                self.order.insert(idx, a.target_id)
            else:
                self.order.append(a.target_id)
            self.articles[a.target_id] = new_node
        else:
            parent, idx = self._find_parent_and_index(a.insert_after)
            if parent:
                parent.children.insert(idx + 1, new_node)
            else:
                fallback = self._find_node(a.insert_after)
                if fallback:
                    fallback.children.append(new_node)
                elif self.order:
                    self.articles[self.order[-1]].children.append(new_node)

        return new_node

    def _build_node(self, node_id, node_type, content, source) -> Node:
        lines = content.splitlines() if content else [node_id]
        return Node(
            node_type  = node_type,
            node_id    = node_id,
            label      = lines[0] if lines else node_id,
            body_lines = lines[1:] if len(lines) > 1 else [],
            source_doc = source,
        )

    def _guess_node_type(self, node_id: str) -> NodeType:
        if re.match(r'Điều\s+\d+', node_id, re.IGNORECASE): return NodeType.ARTICLE
        if re.match(r'\d+\.\d+', node_id):                   return NodeType.SUB_CLAUSE
        if re.match(r'\d+$', node_id):                       return NodeType.CLAUSE
        if re.match(r'[a-zđ]\)', node_id):                   return NodeType.POINT
        return NodeType.ITEM

    # ─────────────────────────────────────────────────────
    # Helpers nhãn / trích câu
    # ─────────────────────────────────────────────────────

    def _warn(self, msg: str):
        self.merge_log.append({"action": "CẢNH BÁO", "message": msg})
        print(f"  ⚠️  {msg}")

    def _node_scope_label(self, node: Node, fallback_scope: str = "") -> str:
        if fallback_scope:
            return self._format_scope_label(fallback_scope)
        nid   = node.node_id.strip()
        ntype = node.node_type
        if ntype == NodeType.ARTICLE:    return nid
        if ntype == NodeType.CLAUSE:     return f"Khoản {nid}"
        if ntype == NodeType.SUB_CLAUSE: return f"Khoản {nid}"
        if ntype == NodeType.POINT:      return f"Điểm {nid}"
        if ntype == NodeType.ITEM:       return f"Tiết {nid}"
        return nid

    @staticmethod
    def _format_scope_label(scope: str) -> str:
        """'khoản 10 Điều 3' → 'Điều 3, Khoản 10'."""
        sl = scope.lower().strip()
        art_m    = re.search(r'(?:điều)\s+(\d+[a-zđ]?)', sl)
        clause_m = re.search(r'khoản\s+(\d+(?:\.\d+)?)', sl)
        # "điểm b(i)" hoặc "điểm b)" hoặc "điểm b "
        point_m  = re.search(r'điểm\s+([a-zđ])(?:\((\w+)\))?\)?(?=[\s(,]|$)', sl)
        item_m   = re.search(r'tiết\s+(\S+)', sl)

        parts = []
        if art_m:    parts.append(f"Điều {art_m.group(1)}")
        if clause_m: parts.append(f"Khoản {clause_m.group(1)}")
        if point_m:
            parts.append(f"Điểm {point_m.group(1)})")
            if point_m.group(2):          # có tiết con: "b(i)"
                parts.append(f"Tiết ({point_m.group(2)})")
        if item_m:   parts.append(f"Tiết {item_m.group(1)}")

        return ", ".join(parts) if parts else scope.split("—")[0].strip()

    def _extract_sentence_with_phrase(self, text: str, phrase: str) -> str:
        if not phrase or not text:
            return text
        flat = text.replace('\n', ' ')
        sentences = re.split(r'(?<=[.;])\s+', flat)
        for sent in sentences:
            if phrase.lower() in sent.lower():
                return sent.strip()
        return flat[:200] + ("…" if len(flat) > 200 else "")
