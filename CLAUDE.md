# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Tổng quan dự án

**Legal Merger** là công cụ hợp nhất văn bản pháp luật tiếng Việt — tự động tích hợp các văn bản sửa đổi vào văn bản gốc, theo dõi toàn bộ thay đổi và tạo bảng so sánh chi tiết.

## Cài đặt

```bash
pip install python-docx pdfplumber openpyxl
```

Yêu cầu Python 3.7+. Không có `requirements.txt` — cài thủ công các thư viện trên.

## Chạy công cụ

```bash
# Dùng package (khuyến nghị)
python -m legal_merger docs/input/15-ttkdtm.pdf -a docs/input/30-suadoi-15.pdf -o ket_qua.txt

# Hoặc dùng file gốc (shim backward-compat)
python legal_merger.py docs/input/15-ttkdtm.pdf -a docs/input/30-suadoi-15.pdf -o ket_qua.txt

# Chỉ định định dạng
python -m legal_merger goc.pdf -a suadoi.pdf -o ket_qua.docx --format docx --cmp-format xlsx

# Nhiều văn bản sửa đổi, bỏ qua bảng so sánh
python -m legal_merger goc.txt -a sd1.pdf sd2.docx -o hop_nhat.txt --no-comparison
```

## API Python

```python
from legal_merger import merge_legal_documents

result = merge_legal_documents(
    base_file="goc.pdf",
    amendment_files=["suadoi.pdf"],
    output_file="hop_nhat.txt",
    output_format="txt",      # "txt" hoặc "docx"
    comparison=True,
    comparison_formats=["docx", "xlsx"]  # một hoặc cả hai
)
```

Trích tiêu đề văn bản riêng lẻ:

```python
from legal_merger import read_file, extract_title

text  = read_file("goc.pdf")
title = extract_title(text, "goc.pdf")  # → "Thông tư 15/2024/TT-NHNN"
```

## Tham số dòng lệnh

| Tham số | Mô tả |
|---|---|
| `base_file` | Đường dẫn văn bản gốc (.txt/.docx/.pdf) |
| `--amendments` / `-a` | Một hoặc nhiều văn bản sửa đổi (bắt buộc) |
| `--output` / `-o` | Đường dẫn file đầu ra (mặc định: `van_ban_hop_nhat.txt`) |
| `--format` | `txt` hoặc `docx` (mặc định: `txt`) |
| `--no-deleted` | Ẩn các điều đã bị bãi bỏ |
| `--no-comparison` | Bỏ qua tạo bảng so sánh |
| `--cmp-format` | `docx`, `xlsx`, hoặc cả hai (mặc định: cả hai) |
| `--no-clean-pages` | Tắt tính năng xóa số trang/header/footer |

## File đầu ra

Với đường dẫn đầu ra `ket_qua.txt`, công cụ tạo ra:
- `ket_qua.txt` — Văn bản hợp nhất với chú thích nội tuyến
- `ket_qua_change_report.json` — Nhật ký thay đổi đầy đủ
- `ket_qua_bang_so_sanh.docx` — Bảng so sánh (Word, khổ A4 ngang)
- `ket_qua_bang_so_sanh.xlsx` — Bảng so sánh (Excel, 2 sheet)

Mọi tham chiếu văn bản (header, citation, bảng so sánh) dùng **tiêu đề trích từ nội dung** (ví dụ: `Thông tư 15/2024/TT-NHNN`) thay cho tên file.

## Kiến trúc — Package `legal_merger/`

Code được tổ chức thành package. File `legal_merger.py` gốc là shim backward-compat.

```
legal_merger/
├── __init__.py          # Re-export public API
├── __main__.py          # CLI: python -m legal_merger
├── models.py            # Node, Amendment, ComparisonRow, NodeType, OperationType
├── patterns.py          # Regex cấu trúc văn bản (_RE_ARTICLE, _RE_CLAUSE, ...)
├── page_cleaner.py      # PageCleaner, read_file, clean_page_artifacts, extract_title
├── document_parser.py   # DocumentParser → cây Node
├── amendment_parser.py  # AmendmentParser → list[Amendment]  (Mask→Parse→Restore)
├── merge_engine.py      # MergeEngine → áp dụng Amendment vào cây
├── output_writer.py     # OutputWriter → TXT / DOCX / JSON
├── comparison_builder.py# ComparisonTableBuilder → DOCX + XLSX bảng so sánh
└── orchestrator.py      # merge_legal_documents() — điều phối toàn pipeline
```

### Pipeline xử lý

```
Đầu vào PDF/DOCX/TXT
    → PageCleaner             (xóa số trang, header, footer, nối câu bị ngắt)
    → extract_title           (trích "Thông tư 15/2024/TT-NHNN" từ nội dung)
    → DocumentParser          (cây phân cấp: Điều→Khoản→Tiểu khoản→Điểm→Tiết)
    → AmendmentParser         (Mask→Parse→Restore → list[Amendment])
    → MergeEngine             (áp dụng sửa đổi với tìm kiếm node theo ngữ cảnh)
    → OutputWriter            (văn bản hợp nhất với chú thích nội tuyến)
    → ComparisonTableBuilder  (bảng so sánh DOCX/XLSX)
```

### Các lớp chính

- **`Node`** (dataclass) — Đơn vị cây: `node_type`, `node_id`, `label`, `body_lines`, `children`, `citations`, `change_log`, `is_deleted`.
- **`DocumentParser`** — Phân tích văn bản gốc thành `(articles_dict, order_list)`. Nhận dạng cấp phân cấp bằng regex từ `patterns.py`.
- **`AmendmentParser`** — Trích xuất `list[Amendment]`. Chiến lược **Mask→Parse→Restore**: nội dung cần chèn được che bằng token placeholder để tránh bị phân tích nhầm thành cấu trúc, sau đó khôi phục.
- **`MergeEngine`** — Áp dụng từng `Amendment`. Dùng `_find_node_in_context()` để tìm đúng node theo ngữ cảnh cha (tránh sửa nhầm "Khoản 10" ở Điều khác). `_replace_phrase()` dùng negative lookahead để tránh double-apply khi `new` là prefix của `old`.
- **`OutputWriter`** — Xuất `.txt`/`.docx`/JSON. Node bị xóa hiển thị `[BÃI BỎ]`; citation xuất hiện nội tuyến (xanh italic trong DOCX).
- **`ComparisonTableBuilder`** — Bảng nội dung cũ/mới. Tô màu theo loại thao tác; highlight đỏ/xanh lá cho cụm từ thay thế.
- **`extract_title(text, file_name)`** — Trích tiêu đề từ nội dung. Ưu tiên `"DocType số/năm/CODE"` từ dòng `Số:`; 3 cấp dự phòng; fallback về tên file.

### Các loại thao tác (`OperationType`)

| Enum | Tiếng Việt | Ý nghĩa |
|---|---|---|
| `MODIFY` | Sửa đổi | Thay toàn bộ nội dung node |
| `INSERT` | Bổ sung | Thêm node mới |
| `DELETE` | Bãi bỏ | Đánh dấu node `is_deleted` |
| `REPLACE` | Thay cụm từ | Thay một cụm từ cụ thể trong nội dung |
| `MODIFY_AND_INSERT` | Sửa đổi, bổ sung | Sửa node + thêm node liền kề |
| `RENAME` | Đổi tên | Đổi `label` của node |

### Cấu trúc phân cấp (`NodeType`)

```
Điều X            (ARTICLE  — node_id: "Điều 3")
  └─ 1.           (CLAUSE   — node_id: "1")
       └─ 1.1     (SUB_CLAUSE — node_id: "1.1")
            └─ a) (POINT    — node_id: "a)")
                 └─ -       (ITEM     — node_id: "-")
```

## Dữ liệu mẫu

- `docs/input/15-ttkdtm.pdf` — Văn bản gốc (Thông tư 15/2024/TT-NHNN, 23 Điều)
- `docs/input/30-suadoi-15.pdf` — Văn bản sửa đổi (Thông tư 30/2025/TT-NHNN, 21 thao tác)
- `docs/output/` — Kết quả đầu ra tham khảo
