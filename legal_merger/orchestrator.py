"""
orchestrator.py — Hàm điều phối chính merge_legal_documents.
"""

import os
from datetime import datetime

from .models import NodeType
from .page_cleaner import read_file, extract_title
from .document_parser import DocumentParser
from .amendment_parser import AmendmentParser
from .merge_engine import MergeEngine
from .output_writer import OutputWriter
from .comparison_builder import ComparisonTableBuilder


def merge_legal_documents(
    base_file:          str,
    amendment_files:    list,
    output_file:        str,
    output_format:      str  = "txt",
    keep_deleted:       bool = True,
    comparison:         bool = True,
    comparison_formats: list = None,
    clean_pages:        bool = True,
) -> dict:

    print("\n" + "═" * 58)
    print("  🔄  HỢP NHẤT VĂN BẢN PHÁP LÝ  v3.0")
    print("═" * 58)

    if comparison_formats is None:
        comparison_formats = ["xlsx"]

    # Văn bản gốc
    print(f"\n📄 Văn bản gốc : {base_file}")
    base_text  = read_file(base_file, clean_pages=clean_pages, verbose=True)
    base_title = extract_title(base_text, os.path.basename(base_file))
    print(f"   📌 Tiêu đề    : {base_title}")
    articles, order = DocumentParser().parse(base_text, base_title)

    total_nodes = sum(_count_nodes(a) for a in articles.values())
    print(f"   ✅ {len(articles)} Điều  —  {total_nodes} node tổng cộng")
    _print_tree_preview(articles, order)

    # Văn bản sửa đổi
    all_amendments  = []
    amendment_names = []
    for af in amendment_files:
        print(f"\n📝 Văn bản sửa đổi : {af}")
        amend_text  = read_file(af, clean_pages=clean_pages, verbose=True)
        amend_title = extract_title(amend_text, os.path.basename(af))
        print(f"   📌 Tiêu đề    : {amend_title}")
        amends = AmendmentParser().parse(amend_text, source_name=amend_title)
        all_amendments.extend(amends)
        amendment_names.append(amend_title)
        for am in amends:
            print(f"   • [{am.operation.name}] {am.target_scope or am.target_id}")

    # Hợp nhất
    print(f"\n⚙️  Áp dụng {len(all_amendments)} lệnh sửa đổi ...")
    engine = MergeEngine(articles, order)
    engine.apply_amendments(all_amendments)

    # Thống kê
    keys  = ["SỬA ĐỔI", "SỬA ĐỔI, BỔ SUNG", "BỔ SUNG", "BÃI BỎ",
             "THAY CỤM TỪ", "ĐỔI TÊN", "CẢNH BÁO"]
    icons = {
        "SỬA ĐỔI"          : "✏️",
        "SỬA ĐỔI, BỔ SUNG" : "✏️➕",
        "BỔ SUNG"          : "➕",
        "BÃI BỎ"           : "🗑️",
        "THAY CỤM TỪ"      : "🔄",
        "ĐỔI TÊN"          : "🏷️",
        "CẢNH BÁO"         : "⚠️",
    }
    stats = {k: sum(1 for e in engine.merge_log if e.get("action") == k) for k in keys}
    print("\n📊 Kết quả:")
    for k, v in stats.items():
        if v: print(f"   {icons[k]}  {k}: {v}")

    # Xuất văn bản hợp nhất
    final = engine.get_ordered_articles()
    if not keep_deleted:
        final = [a for a in final if not a.is_deleted]

    meta = {
        "base_doc"      : base_title,
        "amendment_docs": amendment_names,
        "date"          : datetime.now().strftime("%d/%m/%Y"),
    }
    writer = OutputWriter()
    (writer.write_docx if output_format == "docx" else writer.write_txt)(
        final, output_file, meta)

    report_path = output_file.rsplit('.', 1)[0] + "_change_report.json"
    writer.write_change_report(engine.merge_log, report_path)

    print(f"\n✅ Hoàn tất!")
    print(f"   📄 Văn bản hợp nhất : {output_file}")
    print(f"   📋 Báo cáo thay đổi : {report_path}")

    # Bảng so sánh
    comparison_files = {}
    if comparison and engine.merge_log:
        print(f"\n📊 Tạo bảng so sánh nội dung cũ/mới ...")
        base_name = output_file.rsplit('.', 1)[0]
        builder   = ComparisonTableBuilder(engine.merge_log, meta)

        if "docx" in comparison_formats:
            cmp_docx = f"{base_name}_bang_so_sanh.docx"
            builder.write_docx(cmp_docx)
            comparison_files["docx"] = cmp_docx
            print(f"   📋 Bảng so sánh DOCX : {cmp_docx}")

        if "xlsx" in comparison_formats:
            cmp_xlsx = f"{base_name}_bang_so_sanh.xlsx"
            builder.write_xlsx(cmp_xlsx)
            comparison_files["xlsx"] = cmp_xlsx
            print(f"   📋 Bảng so sánh XLSX : {cmp_xlsx}")

    print("═" * 58 + "\n")

    return {
        "output_file"      : output_file,
        "report_file"      : report_path,
        "comparison_files" : comparison_files,
        "total_articles"   : len(final),
        "changes"          : stats,
        "clean_pages"      : clean_pages,
    }


# ── helpers ───────────────────────────────────────────────

def _count_nodes(node) -> int:
    return 1 + sum(_count_nodes(c) for c in node.children)


def _print_tree_preview(articles: dict, order: list):
    for aid in order[:5]:
        art    = articles[aid]
        counts = {t: 0 for t in NodeType}
        _count_by_type(art, counts)
        parts = []
        if counts[NodeType.CLAUSE]:     parts.append(f"{counts[NodeType.CLAUSE]} khoản")
        if counts[NodeType.SUB_CLAUSE]: parts.append(f"{counts[NodeType.SUB_CLAUSE]} tiểu khoản")
        if counts[NodeType.POINT]:      parts.append(f"{counts[NodeType.POINT]} điểm")
        if counts[NodeType.ITEM]:       parts.append(f"{counts[NodeType.ITEM]} tiết")
        desc = ", ".join(parts) if parts else "không có khoản con"
        print(f"   {aid}: {desc}")
    if len(order) > 5:
        print(f"   ... ({len(order) - 5} điều còn lại)")


def _count_by_type(node, counts: dict):
    counts[node.node_type] += 1
    for child in node.children:
        _count_by_type(child, counts)
