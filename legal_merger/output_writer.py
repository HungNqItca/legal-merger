"""
output_writer.py — Xuất văn bản hợp nhất ra TXT / DOCX / JSON.
"""

import json
from datetime import datetime

from .models import Node, NodeType


_INDENT = {
    NodeType.ARTICLE    : "",
    NodeType.CLAUSE     : "  ",
    NodeType.SUB_CLAUSE : "    ",
    NodeType.POINT      : "      ",
    NodeType.ITEM       : "        ",
}


class OutputWriter:

    # ── TXT ───────────────────────────────────────────────

    def write_txt(self, articles: list, path: str, meta: dict):
        lines = [
            "=" * 65, "VĂN BẢN HỢP NHẤT", "=" * 65,
            f"Văn bản gốc  : {meta.get('base_doc','')}",
            f"Sửa đổi bởi  : {', '.join(meta.get('amendment_docs',[]))}",
            f"Ngày hợp nhất: {datetime.now().strftime('%d/%m/%Y')}",
            "=" * 65, "",
        ]
        for art in articles:
            lines += self._render_txt(art)
            lines.append("")
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    def _render_txt(self, node: Node, depth: int = 0) -> list:
        ind   = _INDENT.get(node.node_type, "  " * depth)
        lines = []

        if node.is_deleted:
            cite = f"  {node.citations[0]}" if node.citations else ""
            lines.append(f"{ind}[BÃI BỎ] {node.label}{cite}")
            return lines

        cite_inline = f"  {node.citations[0]}" if node.citations else ""
        lines.append(f"{ind}{node.label}{cite_inline}")

        for c in node.citations[1:]:
            lines.append(f"{ind}  {c}")

        for bl in node.body_lines:
            lines.append(f"{ind}{bl}")

        for child in node.children:
            lines += self._render_txt(child, depth + 1)

        return lines

    # ── DOCX ──────────────────────────────────────────────

    def write_docx(self, articles: list, path: str, meta: dict):
        from docx import Document
        from docx.shared import Pt, Cm
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        doc = Document()
        for section in doc.sections:
            section.top_margin = section.bottom_margin = Cm(2)
            section.left_margin = section.right_margin = Cm(3)

        t = doc.add_heading("VĂN BẢN HỢP NHẤT", level=1)
        t.alignment = WD_ALIGN_PARAGRAPH.CENTER

        p = doc.add_paragraph()
        r = p.add_run("Văn bản gốc: ")
        r.bold = True
        p.add_run(meta.get('base_doc', ''))
        doc.add_paragraph(f"Ngày hợp nhất: {datetime.now().strftime('%d/%m/%Y')}")
        doc.add_paragraph()

        for art in articles:
            self._render_docx(doc, art)

        doc.save(path)

    def _render_docx(self, doc, node: Node, depth: int = 0):
        from docx.shared import Pt, RGBColor, Cm

        ind        = Cm(depth * 0.7)
        CITE_COLOR = RGBColor(0x44, 0x72, 0xC4)
        DEL_COLOR  = RGBColor(0x99, 0x99, 0x99)

        if node.is_deleted:
            p   = doc.add_paragraph()
            p.paragraph_format.left_indent = ind
            run = p.add_run(f"[BÃI BỎ] {node.label}")
            run.font.color.rgb = DEL_COLOR
            run.font.strike    = True
            run.font.size      = Pt(10)
            if node.citations:
                cr = p.add_run(f"  {node.citations[0]}")
                cr.font.color.rgb = DEL_COLOR
                cr.font.size      = Pt(9)
                cr.font.italic    = True
            return

        p   = doc.add_paragraph()
        p.paragraph_format.left_indent = ind
        p.paragraph_format.space_after = Pt(2)

        run = p.add_run(node.label)
        run.bold      = (node.node_type == NodeType.ARTICLE)
        run.font.size = {
            NodeType.ARTICLE    : Pt(12),
            NodeType.CLAUSE     : Pt(11),
            NodeType.SUB_CLAUSE : Pt(10.5),
            NodeType.POINT      : Pt(10),
            NodeType.ITEM       : Pt(10),
        }.get(node.node_type, Pt(10))

        if node.citations:
            for cite in node.citations:
                cr = p.add_run(f"  {cite}")
                cr.font.color.rgb = CITE_COLOR
                cr.font.size      = Pt(8.5)
                cr.font.italic    = True

        for bl in node.body_lines:
            bp = doc.add_paragraph(bl)
            bp.paragraph_format.left_indent = Cm((depth + 0.5) * 0.7)
            bp.paragraph_format.space_after = Pt(1)
            for r in bp.runs:
                r.font.size = Pt(10)

        for child in node.children:
            self._render_docx(doc, child, depth + 1)

    # ── Báo cáo JSON ──────────────────────────────────────

    def write_change_report(self, merge_log: list, path: str):
        report = {
            "generated_at" : datetime.now().isoformat(),
            "total_changes": len([e for e in merge_log if e.get("action") != "CẢNH BÁO"]),
            "warnings"     : len([e for e in merge_log if e.get("action") == "CẢNH BÁO"]),
            "changes"      : merge_log,
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
