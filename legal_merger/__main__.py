"""
__main__.py — Entrypoint CLI: python -m legal_merger ...
"""

import argparse
from .orchestrator import merge_legal_documents


def main():
    ap = argparse.ArgumentParser(
        description="Hợp nhất văn bản pháp lý (.txt/.docx/.pdf)  v3.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Cấu trúc phân cấp được hỗ trợ:
  Điều X  →  1. Khoản  →  1.1 Tiểu khoản  →  a) Điểm  →  - / i) Tiết

Ví dụ:
  # Hợp nhất cơ bản — tự động tạo bảng so sánh DOCX + XLSX
  python -m legal_merger luat_goc.docx --amendments nghi_dinh.pdf -o hop_nhat.txt

  # Chỉ tạo bảng Excel, không tạo DOCX bảng
  python -m legal_merger luat.txt --amendments sd.txt -o kq.txt --cmp-format xlsx

  # Tắt tạo bảng so sánh
  python -m legal_merger luat.pdf --amendments sd.txt -o out.txt --no-comparison
        """,
    )
    ap.add_argument("base_file", help="Văn bản gốc (.txt/.docx/.pdf)")
    ap.add_argument("--amendments", "-a", nargs="+", required=True,
                    help="Một hoặc nhiều văn bản sửa đổi")
    ap.add_argument("--output", "-o", default="van_ban_hop_nhat.txt",
                    help="File kết quả (mặc định: van_ban_hop_nhat.txt)")
    ap.add_argument("--format", "-f", choices=["txt", "docx"], default="txt",
                    help="Định dạng xuất văn bản hợp nhất")
    ap.add_argument("--no-deleted", action="store_true",
                    help="Không xuất điều khoản đã bị bãi bỏ")
    ap.add_argument("--no-comparison", action="store_true",
                    help="Không tạo bảng so sánh nội dung cũ/mới")
    ap.add_argument("--cmp-format", nargs="+",
                    choices=["docx", "xlsx"], default=["docx", "xlsx"],
                    metavar="FMT",
                    help="Định dạng bảng so sánh: docx xlsx (mặc định: cả hai)")
    ap.add_argument("--no-clean-pages", action="store_true",
                    help="Tắt tự động xoá số trang và header/footer")
    args = ap.parse_args()
    merge_legal_documents(
        base_file          = args.base_file,
        amendment_files    = args.amendments,
        output_file        = args.output,
        output_format      = args.format,
        keep_deleted       = not args.no_deleted,
        comparison         = not args.no_comparison,
        comparison_formats = args.cmp_format,
        clean_pages        = not args.no_clean_pages,
    )


if __name__ == "__main__":
    main()
