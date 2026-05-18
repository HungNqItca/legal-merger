# DESIGN.md — Tài liệu thiết kế Legal Merger

> Phiên bản: v5.2 · Cập nhật: 2026-05-18

---

## Mục lục

1. [Mục tiêu thiết kế](#1-mục-tiêu-thiết-kế)
2. [Kiến trúc tổng thể](#2-kiến-trúc-tổng-thể)
3. [Mô hình dữ liệu](#3-mô-hình-dữ-liệu)
4. [Các module chi tiết](#4-các-module-chi-tiết)
   - 4.1 [patterns.py](#41-patternspy)
   - 4.2 [page_cleaner.py](#42-page_cleanerpy)
   - 4.3 [document_parser.py](#43-document_parserpy)
   - 4.4 [amendment_parser.py](#44-amendment_parserpy)
   - 4.5 [merge_engine.py](#45-merge_enginepy)
   - 4.6 [output_writer.py](#46-output_writerpy)
   - 4.7 [comparison_builder.py](#47-comparison_builderpy)
   - 4.8 [orchestrator.py](#48-orchestratorpy)
   - 4.9 [gui.py](#49-guipy)
5. [Quyết định thiết kế quan trọng](#5-quyết-định-thiết-kế-quan-trọng)
6. [Giới hạn đã biết](#6-giới-hạn-đã-biết)
7. [Luồng dữ liệu đầy đủ](#7-luồng-dữ-liệu-đầy-đủ)

---

## 1. Mục tiêu thiết kế

Legal Merger giải quyết bài toán **hợp nhất văn bản pháp luật tiếng Việt**: tích hợp nội dung từ một hoặc nhiều văn bản sửa đổi vào văn bản gốc, đồng thời ghi lại mọi thay đổi dưới dạng truy vết có thể kiểm tra.

### Yêu cầu cốt lõi

| Yêu cầu | Mô tả |
|---|---|
| **Chính xác** | Sửa đúng node, không sửa nhầm "Khoản 1" ở Điều khác |
| **Có thể truy vết** | Mọi thay đổi đều ghi citation và change log vào node |
| **Không phụ thuộc schema cứng** | Không hard-code số Điều/Khoản; nhận dạng bằng regex |
| **Đầu ra đa dạng** | TXT, DOCX cho văn bản hợp nhất; DOCX + XLSX cho bảng so sánh |
| **Không cần GPU hay mô hình AI** | Xử lý hoàn toàn bằng regex và cây cú pháp |

### Nguyên tắc kiến trúc

- **Pipeline tuyến tính**: mỗi bước nhận đầu ra của bước trước, dễ test độc lập.
- **Immutable source**: văn bản gốc không bị ghi đè; `MergeEngine` hoạt động trên `deepcopy`.
- **Tách biệt parse vs. apply**: `AmendmentParser` và `MergeEngine` là hai giai đoạn riêng, đều có thể thay thế mà không ảnh hưởng nhau.
- **Fail-soft**: khi không tìm thấy node đích, ghi cảnh báo vào `merge_log` và tiếp tục, không crash.

---

## 2. Kiến trúc tổng thể

```
┌─────────────────────────────────────────────────────────────────────┐
│                         orchestrator.py                             │
│  merge_legal_documents()  — điều phối toàn pipeline, gom kết quả   │
└──────────┬────────────────────────────┬────────────────────────────┘
           │ văn bản gốc                │ văn bản sửa đổi (1..N)
           ▼                            ▼
┌──────────────────┐         ┌──────────────────┐
│  page_cleaner    │         │  page_cleaner     │
│  read_file()     │         │  read_file()      │
│  extract_title() │         │  extract_title()  │
└────────┬─────────┘         └────────┬──────────┘
         │ text thuần                  │ text thuần
         ▼                            ▼
┌──────────────────┐         ┌──────────────────────┐
│ DocumentParser   │         │  AmendmentParser      │
│  → cây Node      │         │  → list[Amendment]    │
│  → order_list    │         │  (Mask→Parse→Restore) │
└────────┬─────────┘         └────────┬─────────────┘
         │ articles_dict               │ amendments
         └──────────────┬─────────────┘
                        ▼
              ┌──────────────────┐
              │   MergeEngine    │
              │  deepcopy(tree)  │
              │  apply() × N     │
              │  → merge_log     │
              └────────┬─────────┘
                       │
         ┌─────────────┼─────────────────┐
         ▼             ▼                 ▼
  OutputWriter   OutputWriter    ComparisonTableBuilder
  write_txt()    write_docx()    write_docx() / write_xlsx()
  write_JSON()
```

### Cấu trúc package

```
legal_merger/
├── __init__.py          # Re-export public API (kể cả run_gui)
├── __main__.py          # Điểm vào CLI: python -m legal_merger [--gui]
├── models.py            # Node, Amendment, ComparisonRow, enums, _ids_match
├── patterns.py          # Regex cấu trúc + _ROMAN_PAT
├── page_cleaner.py      # PageCleaner, read_file, extract_title
├── document_parser.py   # DocumentParser
├── amendment_parser.py  # AmendmentParser
├── merge_engine.py      # MergeEngine
├── output_writer.py     # OutputWriter
├── comparison_builder.py# ComparisonTableBuilder
├── orchestrator.py      # merge_legal_documents()
└── gui.py               # LegalMergerApp (PyQt6), MergeWorker, run_gui()
```

---

## 3. Mô hình dữ liệu

### 3.1 Node — cây phân cấp văn bản

```python
@dataclass
class Node:
    node_type  : NodeType      # ARTICLE / CLAUSE / SUB_CLAUSE / POINT / ITEM
    node_id    : str           # "Điều 3", "1", "1.1", "a)", "(ii)"
    label      : str           # dòng đầu của node (tiêu đề)
    body_lines : list[str]     # các dòng nội dung sau label
    children   : list[Node]    # node con (ordered)
    chapter    : str           # Chương/Mục chứa node (context, không phải node)
    source_doc : str           # tên văn bản nguồn
    is_deleted : bool          # đã bị bãi bỏ
    change_log : list[str]     # lịch sử thay đổi có timestamp
    citations  : list[str]     # chú thích nội tuyến, ví dụ "(sửa đổi bởi TT 30)"
```

Cấu trúc phân cấp hỗ trợ:

```
Điều X                    ARTICLE   node_id = "Điều 3"
  └─ 1.                   CLAUSE    node_id = "1"
       └─ 1.1             SUB_CLAUSE node_id = "1.1"
            └─ a)         POINT     node_id = "a)"
                 └─ -     ITEM      node_id = "-"
                 └─ (i)   ITEM      node_id = "(i)"
```

`Node.find(target_id)` tìm đệ quy theo `node_id` dùng `_ids_match` (chuẩn hóa khoảng trắng + lowercase).

### 3.2 Amendment — một lệnh sửa đổi

```python
@dataclass
class Amendment:
    operation     : OperationType  # MODIFY | INSERT | DELETE | REPLACE |
                                   # MODIFY_AND_INSERT | RENAME
    target_id     : str            # node_id của đích (ví dụ: "1", "a)")
    target_scope  : str            # mô tả đầy đủ: "điểm a) khoản 1 Điều 5"
    content       : str            # nội dung mới (MODIFY / INSERT)
    insert_after  : str            # node_id chèn sau (INSERT)
    old_phrase    : str            # cụm từ cũ (REPLACE)
    new_phrase    : str            # cụm từ mới (REPLACE)
    parent_article_id : str        # "Điều 5" — ngữ cảnh tìm node
    parent_clause_id  : str        # "1"      — ngữ cảnh tìm node
    parent_point_id   : str        # "a)"     — ngữ cảnh tìm node
    amending_article  : str        # Điều trong VB sửa đổi, dùng cho citation
    source_doc        : str        # tên VB sửa đổi
    original_content  : str        # nội dung gốc (điền bởi MergeEngine)
    node_title        : str        # nhãn hiển thị (điền bởi MergeEngine)
```

### 3.3 OperationType

| Enum | Ý nghĩa | Hành động trong MergeEngine |
|---|---|---|
| `MODIFY` | Thay toàn bộ nội dung node | `_replace_content()` |
| `MODIFY_AND_INSERT` | Sửa node + thêm node liền kề | `_replace_content()` |
| `INSERT` | Thêm node mới | `_insert_node()` |
| `DELETE` | Đánh dấu `is_deleted = True` | Set flag, giữ node trong cây |
| `REPLACE` | Thay cụm từ trong node và toàn cây con | `_replace_phrase()` đệ quy |
| `RENAME` | Đổi `label` giữ nguyên `node_id` | Cập nhật `node.label` |

---

## 4. Các module chi tiết

### 4.1 patterns.py

Định nghĩa tất cả regex nhận dạng cấu trúc. Dùng chung bởi `DocumentParser` và `AmendmentParser`.

```python
_RE_ARTICLE    # "Điều N" / "ĐIỀU Na" (N chữ số, a chữ cái tùy chọn)
_RE_CLAUSE     # "N. text"  (không phải N.M)
_RE_SUB_CLAUSE # "N.M text"
_RE_POINT      # "a) text" (a-z, đ)
_RE_ITEM       # "- text" | "(i) text" | "i) text"  (i–xx)
_RE_CHAPTER    # "Chương" / "Mục" — chỉ lưu context
_ROMAN_PAT     # hằng số regex số La Mã i–xx (dùng trong _RE_ITEM và AmendmentParser)
```

`_ROMAN_PAT` được xây dựng theo thứ tự **dài → ngắn** để tránh partial match:
`xx|xix|xviii|...|xi|x|ix|...|i` — nếu để ngược `i|...|x|xi|...` thì `"xi"` sẽ match `"i"` trước.

### 4.2 page_cleaner.py

Làm sạch văn bản PDF/DOCX trước khi parse. PDF thường chứa số trang, header/footer xen vào giữa.

**PageCleaner** áp dụng 4 lớp theo thứ tự:

| Lớp | Loại bỏ | Ví dụ |
|---|---|---|
| 1 — Pattern rõ | Số trang có dạng chuẩn | `Trang 3`, `- 3 -`, `(3)`, `3/15` |
| 2 — Số nguyên đứng một mình | Số trang không có nhãn | dòng chỉ chứa `3` |
| 3 — Header/footer lặp lại | Chuỗi xuất hiện ≥ 3 lần | tên cơ quan, tên văn bản lặp |
| 4 — Nối câu bị ngắt | Câu bị cắt bởi số trang | `"...theo quy"` + `"định tại..."` |

Lớp 2 sử dụng ngữ cảnh: nếu dòng số đứng sau dấu kết câu hoặc trước header Điều/Chương thì khả năng cao là số trang.

**`extract_title(text, file_name)`** trích tiêu đề theo 4 cấp dự phòng:
1. `"DocType"` + dòng `Số: N/năm/CODE` → `"Thông tư 15/2024/TT-NHNN"`
2. `DocType` + mô tả liền kề
3. Dòng `THÔNG TƯ về...` trên cùng một dòng
4. Dòng đầu có nội dung (10–200 ký tự)

### 4.3 document_parser.py

Phân tích văn bản gốc thành cây `Node`.

**Thuật toán**: Duyệt từng dòng, dùng **state machine** duy trì con trỏ cho node đang mở ở mỗi cấp. Khi gặp pattern cấp cao hơn, con trỏ cấp thấp được reset về `None`.

```
current_article → current_clause → current_sub → current_point → current_item
```

Ưu tiên kiểm tra từ cao xuống thấp, trừ `_RE_SUB_CLAUSE` được kiểm tra **trước** `_RE_CLAUSE` vì `N.M` là tiền tố của `N`.

Dòng không khớp bất kỳ pattern nào → được thêm vào `body_lines` của node hiện tại sâu nhất (`deepest`).

```python
deepest = current_item or current_point or current_sub or current_clause or current_article
deepest.body_lines.append(stripped)
```

**Đầu ra**: `(articles_dict, order_list)` — dict ánh xạ `node_id → Node` và list giữ thứ tự xuất hiện.

### 4.4 amendment_parser.py

Phân tích văn bản sửa đổi thành `list[Amendment]`. Đây là module phức tạp nhất vì văn bản sửa đổi có cấu trúc tự do hơn.

#### Chiến lược Mask→Parse→Restore

Vấn đề: nội dung cần chèn (sau `như sau:`) thường có cấu trúc giống văn bản gốc (Điều, khoản, điểm) — nếu không bảo vệ, chúng sẽ bị phân tích nhầm như cấu trúc của văn bản sửa đổi.

Giải pháp:
1. **Mask**: thay nội dung cần bảo vệ bằng token `__CONTENT_N__`
2. **Parse**: phân tích cấu trúc lệnh sửa đổi trên văn bản đã mask
3. **Restore**: khôi phục nội dung thực khi tạo đối tượng `Amendment`

Hai loại nội dung được mask:
- **Sau marker**: nội dung sau `như sau:\n`, `sau đây:\n`
- **Ngoặc kép dài**: chuỗi trong `"..."` hoặc `"..."` có ký tự cấu trúc nhúng (`\n1. text`), hoặc dài ≥ 20 ký tự

#### Nhận dạng scope

`_SCOPE_PATTERNS` — 6 pattern độ cụ thể giảm dần:

```
tiết X điểm a) khoản N Điều M        (mức sâu nhất)
điểm a(i),(ii) khoản N Điều M        (nhiều tiết trong điểm)
điểm a) khoản N Điều M
khoản N.M Điều M                     (tiểu khoản)
khoản N Điều M
Điều M                               (mức nông nhất)
```

`_scope_to_ids(scope)` → `(target_id, parent_article_id, parent_clause_id)`

#### Nhận dạng loại thao tác

Ưu tiên kiểm tra từ cụ thể → chung:
1. `RENAME` — "sửa đổi tên Điều N"
2. `MODIFY_AND_INSERT` — "sửa đổi, bổ sung"
3. `REPLACE` — `thay "X" bằng "Y"` (có ngoặc kép)
4. `DELETE` — "bãi bỏ", "hủy bỏ"
5. `INSERT` — "bổ sung", "thêm"
6. `MODIFY` — "sửa đổi"

`_OP_MODIFY` dùng negative lookahead để không match `REPLACE`: `thay thế(?!\s+cụm từ)`.

#### Parse multi-target DELETE

`_parse_multi_delete()` nhận dạng:
- `"bãi bỏ khoản 1, 2, 3 Điều 5"` → 3 Amendment DELETE riêng lẻ
- `"bãi bỏ điểm a, b khoản 1 Điều 5"` → 2 Amendment DELETE riêng lẻ

Chỉ kích hoạt khi có ≥ 2 target; single target fallback về flow đơn thông thường.

#### Luồng parse tổng thể

```
parse(text)
  ├─ _mask_replacement_content()    → masked_text, content_map
  ├─ tách art_blocks theo "\nĐiều N[.:]"
  ├─ [có block Điều] → _parse_article_block_masked()
  │     ├─ [có khoản số] → tách từng khoản → flush_clause()
  │     └─ [không có khoản] → flush_clause() cho toàn block
  │           ├─ [REPLACE_MASKED] → xử lý token
  │           ├─ [POINT_WITH_ITEMS] → nhiều tiết La Mã
  │           ├─ [có điểm a) b)] → tách theo điểm
  │           └─ → _parse_paragraph()  (trả list[Amendment])
  └─ [không có block Điều] → fallback paragraph-by-paragraph
        └─ → _parse_paragraph()
```

`_parse_paragraph()` trả `list[Amendment]` (empty = không nhận dạng được).

### 4.5 merge_engine.py

Áp dụng `list[Amendment]` lên `deepcopy(articles_dict)`.

#### Tìm node có ngữ cảnh

`_find_node_in_context(target_id, parent_article_id, parent_clause_id, parent_point_id)`:

```
Nếu parent_article_id được chỉ định:
  1. Tìm parent_article trực tiếp
  2. Nếu không thấy → thử bỏ suffix chữ cái ("Điều 3a" → "Điều 3")
  3. Trong parent_article:
     a. Tìm trong parent_clause → parent_point → target
     b. Tìm trong parent_clause → target
     c. Tìm trong parent_article → target
     d. Nếu tất cả thất bại → trả None (không fallback toàn cục)
Nếu không có ngữ cảnh → tìm toàn cục _find_node(target_id)
```

Không fallback toàn cục khi có ngữ cảnh là **cố ý**: tránh trường hợp sửa "Khoản 1" sai Điều.

#### REPLACE với negative lookahead

`_replace_phrase(node, old, new)` — thay cụm từ đệ quy trong toàn cây con.

Khi `new.startswith(old)` (ví dụ: old=`"A"`, new=`"A mới"`), dùng lookahead để tránh double-apply:

```python
pattern = re.compile(re.escape(old) + r'(?!' + re.escape(new[len(old):]) + r')')
```

Không dùng pattern này khi `old == new` (vô hại nhưng vô nghĩa).

#### INSERT

`_insert_node()` xử lý 2 trường hợp:
- **Thêm vào Điều đã có**: nếu `target_id` là ARTICLE và đã tồn tại → append vào `children`
- **Thêm Điều mới**: chèn vào `self.order` ngay sau `insert_after`, tạo entry mới trong `self.articles`
- **Thêm node con**: tìm `(parent, idx)` của `insert_after` → `parent.children.insert(idx+1, new_node)`

### 4.6 output_writer.py

Xuất văn bản hợp nhất.

**TXT**: duyệt cây theo DFS, dùng `_INDENT` dict để thụt lề theo `NodeType`. Node bị xóa hiển thị `[BÃI BỎ]` với citation. Citations nội tuyến gắn vào dòng label.

**DOCX**: cùng logic nhưng dùng python-docx. Node bị xóa: gạch ngang màu xám. Citations: xanh dương, italic, cỡ 8.5pt. Điều in đậm 12pt, các cấp con nhỏ dần.

**JSON** (`write_change_report`): toàn bộ `merge_log` + metadata thời gian.

### 4.7 comparison_builder.py

Xây dựng bảng so sánh từ `merge_log`. Bỏ qua entries `action == "CẢNH BÁO"`.

Mỗi entry → một `ComparisonRow`:
- `scope` = `node_title` hoặc `target_scope` từ log
- `highlight_old/new` = cụm từ cụ thể khi REPLACE, dùng để tô màu

**Màu sắc theo loại thao tác:**

| Loại | Màu nền dòng | Màu badge |
|---|---|---|
| Sửa đổi | Vàng nhạt `FFF2CC` | Vàng `F4B942` |
| Bổ sung | Xanh lá nhạt `E2EFDA` | Xanh lá `70AD47` |
| Bãi bỏ | Đỏ nhạt `FCE4D6` | Đỏ `C00000` |
| Thay cụm từ | Xanh dương nhạt `DDEBF7` | Xanh dương `2E75B6` |
| Sửa đổi, bổ sung | Tím nhạt `EAE0F0` | Tím `7030A0` |
| Đổi tên | Xám nhạt `EDEDED` | Xám `595959` |

**DOCX**: khổ A4 ngang (29.7 × 21 cm), 6 cột, dùng raw OOXML (`w:tcW`, `w:shd`) để kiểm soát độ rộng cột chính xác. `_docx_write_highlight()` tách nội dung tại vị trí cụm từ và tô màu phần đó.

**XLSX**: 2 sheet — "Bảng so sánh" (toàn bộ dữ liệu, auto filter, freeze panes) + "Tóm tắt" (thống kê theo loại thao tác với `=SUM()`).

### 4.8 orchestrator.py

`merge_legal_documents()` là điểm vào API duy nhất của pipeline:

1. Đọc và làm sạch văn bản gốc → parse cây
2. Với mỗi file sửa đổi: đọc → parse → collect amendments
3. `MergeEngine.apply_amendments(all_amendments)`
4. `OutputWriter` → văn bản hợp nhất + JSON report
5. `ComparisonTableBuilder` → DOCX + XLSX (nếu bật)
6. Trả `dict` kết quả (đường dẫn file, số liệu thống kê)

### 4.9 gui.py

Giao diện đồ họa PyQt6. Không chứa logic nghiệp vụ — chỉ gọi `merge_legal_documents()` từ `orchestrator.py`.

#### Kiến trúc ba lớp

```
LegalMergerApp (QMainWindow)
    └─ _run_merge()          ← thu thập tham số từ widgets
         └─ MergeWorker (QThread)
               └─ merge_legal_documents(**params)
                    └─ sys.stdout = _OutputStream
                                     └─ text_written signal
                                          └─ _on_log() → QTextEdit.append
```

#### Các lớp

**`_OutputStream(QObject)`** — bridge `sys.stdout → Qt signal`:
```python
def write(self, text): self.text_written.emit(text)   # thread-safe qua Qt signal
def flush(self): pass
```
Redirect `sys.stdout` trước khi gọi `merge_legal_documents()`, restore sau khi xong. Cho phép log real-time từ tất cả `print()` bên trong pipeline mà không cần sửa orchestrator.

**`MergeWorker(QThread)`** — background thread:
- Nhận `params: dict` (đủ kwargs cho `merge_legal_documents`)
- Signals: `log_signal(str)`, `finished_signal(dict)`, `error_signal(str)`
- Trong `run()`: redirect stdout → gọi `merge_legal_documents` → emit kết quả → restore stdout

**`LegalMergerApp(QMainWindow)`** — cửa sổ chính:

| Widget | Vai trò |
|---|---|
| `QLineEdit` + `QFileDialog` | Chọn văn bản gốc, chọn đường dẫn output |
| `QListWidget` + `QFileDialog` | Thêm/xóa danh sách văn bản sửa đổi |
| `QButtonGroup` (`QRadioButton`) | Chọn định dạng TXT / DOCX |
| `QCheckBox` (3 cái) | Bảng so sánh, hiện bãi bỏ, xóa số trang |
| `QPushButton` (run) | Validate → tạo `MergeWorker` → `start()` |
| `QProgressBar` (indeterminate) | Hiển thị khi worker đang chạy |
| `QTextEdit` (read-only) | Nhận log từ `_on_log` slot |
| `QPushButton` (4 cái, ẩn ban đầu) | Mở file kết quả / mở thư mục khi xong |

#### Luồng xử lý

```
_run_merge()
  ├─ validate (base_file tồn tại, amendment_files không rỗng)
  ├─ build params dict từ tất cả widgets
  ├─ disable nút chạy, show QProgressBar
  ├─ khởi MergeWorker(params).start()
  │     [background thread]
  │     run(): redirect stdout → merge_legal_documents() → emit signals
  │
  ├─ _on_log(text)      → QTextEdit.insertPlainText
  ├─ _on_finished(dict) → enable nút, hide progress, show result buttons
  └─ _on_error(msg)     → QMessageBox.critical
```

#### Quyết định thiết kế

- **Thread-safety**: `_OutputStream.write()` emit signal — Qt tự xử lý cross-thread delivery đến main thread (slot `_on_log`). Không cần mutex.
- **Import lazy**: `__init__.py` import `run_gui` trong `try/except ImportError` — CLI không bị phá nếu PyQt6 chưa cài.
- **`--gui` thoát sớm**: `__main__.py` kiểm tra `"--gui" in sys.argv` *trước* `argparse.parse_args()` để tránh conflict với positional argument bắt buộc `base_file`.

---

## 5. Quyết định thiết kế quan trọng

### 5.1 Deepcopy vs. In-place modification

`MergeEngine` làm việc trên `deepcopy(articles)` → văn bản gốc không bao giờ bị ghi đè. Điều này cho phép chạy nhiều lần với cùng `DocumentParser` output mà không cần parse lại.

### 5.2 Không tạo node cho Chương/Mục

`_RE_CHAPTER` chỉ lưu context vào `current_chapter` của node ARTICLE. Quyết định này đơn giản hóa cây và hầu hết các lệnh sửa đổi đều chỉ nhắm đến Điều trở xuống, không nhắm vào Chương. Trade-off: không thể sửa đổi cả một chương như một đơn vị.

### 5.3 MODIFY xóa toàn bộ children

`_replace_content(node, new_content)` reset `children = []`. Đây là hành vi đúng với ngữ nghĩa pháp lý: lệnh "sửa đổi khoản 1 như sau" thay thế toàn bộ khoản 1 bao gồm mọi điểm con. Nếu bản mới có cấu trúc con, chúng sẽ nằm trong `body_lines` chứ không được parse thêm cấp (giữ nguyên text thô là trade-off có chủ ý).

### 5.4 _parse_paragraph trả list thay vì Optional

Cho phép một đoạn văn sinh nhiều `Amendment` (ví dụ: multi-target DELETE). Callers dùng `results.extend(...)` thay vì `if amend: append`.

### 5.5 Fail-soft cho node không tìm thấy

Khi `_find_node_in_context` trả `None`, `MergeEngine` ghi `CẢNH BÁO` vào `merge_log` và tiếp tục. Điều này phù hợp với thực tế: văn bản sửa đổi đôi khi tham chiếu đến node đã bị sửa trước đó (cùng đợt sửa đổi) và node không còn tồn tại với ID cũ.

### 5.6 Citation label từ tiêu đề nội dung

Mọi tham chiếu (`citations`, bảng so sánh, header DOCX) dùng tiêu đề trích từ nội dung (`"Thông tư 15/2024/TT-NHNN"`) thay vì tên file. Điều này đảm bảo khi file đổi tên hoặc chia sẻ qua email, mọi chú thích vẫn có ý nghĩa pháp lý chính xác.

### 5.7 Scope pattern ưu tiên cụ thể nhất

`_SCOPE_PATTERNS` được kiểm tra theo thứ tự giảm dần độ cụ thể. Pattern cụ thể nhất match trước → tránh trường hợp `"điểm a khoản 1 Điều 5"` bị match nhầm bởi pattern `Điều X` (cụ thể cuối).

---

## 6. Giới hạn đã biết

| Giới hạn | Ảnh hưởng | Ghi chú |
|---|---|---|
| Không có `Điều` trong VB gốc | Toàn bộ bị bỏ qua | VB chỉ có khoản/đoạn cần wrapper giả |
| `MODIFY` xóa cấu trúc con | Nội dung mới ở dạng text thô | Đủ cho bài toán hợp nhất cơ bản |
| Tiết La Mã tối đa `xx` (20) | Tiết 21+ không nhận dạng | Hiếm trong văn bản pháp luật |
| Scope `khoản N` không kèm `Điều` | Không nhận dạng được | Cần ngữ cảnh rõ ràng |
| `Phần`, `Tiểu mục` chưa có NodeType | Không parse cấu trúc | Xử lý như body text |
| Preamble trước Điều 1 | Bị bỏ qua khi parse | Không ảnh hưởng hợp nhất |
| Điểm dạng `A.` `B.` (hoa + chấm) | Không nhận dạng | Quyết định/Nghị quyết dạng phụ lục |

---

## 7. Luồng dữ liệu đầy đủ

Ví dụ với `15-ttkdtm.pdf` + `30-suadoi-15.pdf`:

```
read_file("15-ttkdtm.pdf")
  → PageCleaner.clean()           [xóa số trang, nối câu bị ngắt]
  → extract_title()               → "Thông tư 15/2024/TT-NHNN"
  → DocumentParser.parse()        → 23 Điều, ~150 node

read_file("30-suadoi-15.pdf")
  → PageCleaner.clean()
  → extract_title()               → "Thông tư 30/2025/TT-NHNN"
  → AmendmentParser.parse()
      _mask_replacement_content() → masked_text, content_map {__CONTENT_0__: ..., ...}
      art_blocks = split by "\nĐiều N[.:]"
      for block in art_blocks:
          _parse_article_block_masked()
              flush_clause() × 21 clauses
              → _parse_paragraph() × N        → list[Amendment]
      → 21 Amendment objects

MergeEngine(articles, order)
  .apply_amendments(21 amendments)
      for amend in amendments:
          _find_node_in_context(target, parent_art, parent_clause, parent_point)
          apply: _replace_content | _replace_phrase | _insert_node | flag is_deleted
          node.add_citation("(sửa đổi bởi khoản 1 Điều 2 Thông tư 30/2025/TT-NHNN)")
          merge_log.append({action, original_content, new_content, ...})

OutputWriter.write_txt(final_articles, "ket_qua.txt", meta)
OutputWriter.write_change_report(merge_log, "ket_qua_change_report.json")

ComparisonTableBuilder(merge_log, meta)
  .write_docx("ket_qua_bang_so_sanh.docx")   [A4 ngang, 6 cột, tô màu theo loại]
  .write_xlsx("ket_qua_bang_so_sanh.xlsx")   [2 sheet: chi tiết + tóm tắt]
```
