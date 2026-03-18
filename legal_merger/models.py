"""
models.py — Kiểu dữ liệu cốt lõi: enum, dataclass, utility.

Không phụ thuộc bất kỳ module nội bộ nào → có thể import từ mọi nơi
mà không tạo vòng tròn phụ thuộc.
"""

import re
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


# ─────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────

class NodeType(Enum):
    ARTICLE       = "dieu"        # Điều X
    CLAUSE        = "khoan"       # Khoản y  (1.)
    SUB_CLAUSE    = "tieu_khoan"  # Tiểu khoản y.z  (1.1)
    POINT         = "diem"        # Điểm a)
    ITEM          = "tiet"        # Tiết  (-  hoặc  i/ii/iii)


class OperationType(Enum):
    MODIFY            = "sua_doi"
    INSERT            = "bo_sung"
    DELETE            = "bai_bo"
    REPLACE           = "thay_cum_tu"
    MODIFY_AND_INSERT = "sua_doi_bo_sung"
    RENAME            = "doi_ten"


# ─────────────────────────────────────────────────────────
# Utility
# ─────────────────────────────────────────────────────────

def _ids_match(a: str, b: str) -> bool:
    norm = lambda s: re.sub(r'\s+', ' ', s).strip().lower()
    return norm(a) == norm(b)


# ─────────────────────────────────────────────────────────
# Node — đơn vị lưu trữ một cấp trong cây văn bản
# ─────────────────────────────────────────────────────────

@dataclass
class Node:
    node_type  : NodeType
    node_id    : str
    label      : str
    body_lines : list = field(default_factory=list)
    children   : list = field(default_factory=list)
    chapter    : str  = ""
    source_doc : str  = ""
    is_deleted : bool = False
    change_log : list = field(default_factory=list)
    citations  : list = field(default_factory=list)

    def add_change(self, description: str):
        ts = datetime.now().strftime("%d/%m/%Y")
        self.change_log.append(f"[{ts}] {description}")

    def add_citation(self, citation_text: str):
        if citation_text and citation_text not in self.citations:
            self.citations.append(citation_text)

    def get_text(self) -> str:
        parts = [self.label] + self.body_lines
        for child in self.children:
            parts.append(child.get_text())
        return '\n'.join(p for p in parts if p)

    def find(self, target_id: str) -> Optional["Node"]:
        if _ids_match(self.node_id, target_id):
            return self
        for child in self.children:
            found = child.find(target_id)
            if found:
                return found
        return None


# ─────────────────────────────────────────────────────────
# Amendment — mô tả một lệnh sửa đổi
# ─────────────────────────────────────────────────────────

@dataclass
class Amendment:
    operation     : OperationType
    target_id     : str
    target_scope  : str = ""
    content       : str = ""
    insert_after  : str = ""
    old_phrase    : str = ""
    new_phrase    : str = ""
    source_doc    : str = ""
    effective_date: str = ""
    doc_level     : int = 3
    parent_article_id : str = ""
    parent_clause_id  : str = ""
    parent_point_id   : str = ""
    amending_article  : str = ""
    amending_clause   : str = ""
    amending_point    : str = ""
    original_content  : str = ""
    node_title        : str = ""

    def citation_label(self) -> str:
        op_label = {
            OperationType.MODIFY            : "sửa đổi",
            OperationType.INSERT            : "bổ sung",
            OperationType.DELETE            : "bãi bỏ",
            OperationType.REPLACE           : "thay cụm từ",
            OperationType.MODIFY_AND_INSERT : "sửa đổi, bổ sung",
            OperationType.RENAME            : "đổi tên",
        }.get(self.operation, "sửa đổi")

        parts = []
        if self.amending_point:
            parts.append(f"điểm {self.amending_point}")
        if self.amending_clause:
            parts.append(f"khoản {self.amending_clause}")
        if self.amending_article:
            parts.append(self.amending_article)

        location = " ".join(parts) if parts else ""
        doc_name = self.source_doc or "văn bản sửa đổi"
        return (f"({op_label} bởi {location} {doc_name})"
                if location else f"({op_label} bởi {doc_name})")


# ─────────────────────────────────────────────────────────
# ComparisonRow — một hàng trong bảng so sánh
# ─────────────────────────────────────────────────────────

@dataclass
class ComparisonRow:
    stt           : int
    operation     : str
    scope         : str
    old_content   : str
    new_content   : str
    citation      : str
    highlight_old : str
    highlight_new : str
