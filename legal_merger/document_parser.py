"""
document_parser.py — Phân tích văn bản gốc thành cây Node.
"""

import re
from typing import Optional

from .models import Node, NodeType
from .patterns import (
    _RE_ARTICLE, _RE_CLAUSE, _RE_SUB_CLAUSE,
    _RE_POINT, _RE_ITEM, _RE_CHAPTER,
)


def _norm_article_id(raw: str) -> str:
    """Chuẩn hoá ID điều về dạng 'Điều N'."""
    s = re.sub(r'\s+', ' ', raw.strip())
    m = re.match(r'(?:dieu|DIEU|ĐIỀU|Điều)\s+(\d+[a-zđ]?)', s, re.IGNORECASE)
    if m:
        return f"Điều {m.group(1)}"
    return s


class DocumentParser:
    """
    Phân tích văn bản thành dict Điều → cây Node.

    Hỗ trợ cấu trúc phân cấp:
        Điều X
          1.  Khoản
          1.1   Tiểu khoản (tuỳ chọn)
            a)    Điểm
              -     Tiết  (gạch hoặc số La Mã)
    """

    def parse(self, text: str, source_name: str = "") -> tuple:
        """
        Trả về (articles_dict, order_list).
          articles_dict : { article_id -> Node }
          order_list    : [article_id, ...]  (giữ thứ tự xuất hiện)
        """
        articles: dict = {}
        order:    list = []

        current_article : Optional[Node] = None
        current_clause  : Optional[Node] = None
        current_sub     : Optional[Node] = None
        current_point   : Optional[Node] = None
        current_item    : Optional[Node] = None
        current_chapter : str = ""

        for raw_line in text.splitlines():
            line     = raw_line.rstrip()
            stripped = line.strip()
            if not stripped:
                continue

            # Chương / Mục
            if _RE_CHAPTER.match(stripped):
                current_chapter = stripped
                continue

            # Điều
            m = _RE_ARTICLE.match(stripped)
            if m:
                current_article = Node(
                    node_type  = NodeType.ARTICLE,
                    node_id    = _norm_article_id(m.group(1)),
                    label      = stripped,
                    chapter    = current_chapter,
                    source_doc = source_name,
                )
                current_clause = current_sub = current_point = current_item = None
                aid = current_article.node_id
                articles[aid] = current_article
                order.append(aid)
                continue

            if current_article is None:
                continue

            # Tiểu khoản (kiểm tra trước Khoản vì regex dài hơn)
            m = _RE_SUB_CLAUSE.match(stripped)
            if m:
                current_sub = Node(
                    node_type  = NodeType.SUB_CLAUSE,
                    node_id    = m.group(1),
                    label      = stripped,
                    source_doc = source_name,
                )
                current_point = current_item = None
                parent = current_clause if current_clause else current_article
                parent.children.append(current_sub)
                continue

            # Khoản
            m = _RE_CLAUSE.match(stripped)
            if m:
                current_clause = Node(
                    node_type  = NodeType.CLAUSE,
                    node_id    = m.group(1),
                    label      = stripped,
                    source_doc = source_name,
                )
                current_sub = current_point = current_item = None
                current_article.children.append(current_clause)
                continue

            # Điểm
            m = _RE_POINT.match(stripped)
            if m:
                current_point = Node(
                    node_type  = NodeType.POINT,
                    node_id    = m.group(1) + ")",
                    label      = stripped,
                    source_doc = source_name,
                )
                current_item = None
                parent = current_sub or current_clause or current_article
                parent.children.append(current_point)
                continue

            # Tiết
            if _RE_ITEM.match(stripped):
                item_id    = stripped.split()[0]
                current_item = Node(
                    node_type  = NodeType.ITEM,
                    node_id    = item_id,
                    label      = stripped,
                    source_doc = source_name,
                )
                parent = current_point or current_sub or current_clause or current_article
                parent.children.append(current_item)
                continue

            # Nội dung tiếp theo của node hiện tại sâu nhất
            deepest = current_item or current_point or current_sub or current_clause or current_article
            deepest.body_lines.append(stripped)

        return articles, order
