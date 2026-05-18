# Legal Merger — Công cụ hợp nhất văn bản pháp lý

**Phiên bản:** v5.2
**Ngôn ngữ:** Python 3.7+
**Hỗ trợ đầu vào:** `.txt` · `.docx` · `.pdf`
**Hỗ trợ đầu ra:** `.txt` · `.docx` · `.xlsx` + báo cáo thay đổi `.json`

---

## Mục lục

1. [Tổng quan](#1-tổng-quan)
2. [Cài đặt](#2-cài-đặt)
3. [Cấu trúc văn bản được hỗ trợ](#3-cấu-trúc-văn-bản-được-hỗ-trợ)
4. [Định dạng văn bản sửa đổi](#4-định-dạng-văn-bản-sửa-đổi)
5. [Tham chiếu trong văn bản hợp nhất](#5-tham-chiếu-trong-văn-bản-hợp-nhất)
6. [Bảng so sánh nội dung cũ / mới](#6-bảng-so-sánh-nội-dung-cũ--mới)
7. [Sử dụng dòng lệnh (CLI)](#7-sử-dụng-dòng-lệnh-cli)
8. [Sử dụng giao diện đồ họa (GUI)](#8-sử-dụng-giao-diện-đồ-họa-gui)
9. [Sử dụng như thư viện Python](#9-sử-dụng-như-thư-viện-python)
10. [Tệp kết quả đầu ra](#10-tệp-kết-quả-đầu-ra)
11. [Kiến trúc kỹ thuật](#11-kiến-trúc-kỹ-thuật)
12. [Câu hỏi thường gặp](#12-câu-hỏi-thường-gặp)
13. [Lịch sử phiên bản](#13-lịch-sử-phiên-bản)

---

## 1. Tổng quan

**Legal Merger** tự động hợp nhất văn bản pháp lý gốc với một hoặc nhiều văn bản sửa đổi, bổ sung theo đúng quy trình kỹ thuật soạn thảo văn bản pháp luật Việt Nam. Công cụ:

- Phân tích cấu trúc phân cấp **5 cấp** của văn bản pháp lý Việt Nam
- Nhận dạng **6 loại thao tác**: Sửa đổi · Sửa đổi bổ sung · Bổ sung · Bãi bỏ · Thay cụm từ · Đổi tên
- Trích **tiêu đề chính thức** từ nội dung văn bản (VD: `Thông tư 15/2024/TT-NHNN`) — dùng làm tham chiếu thay cho tên file
- Tìm kiếm node **có ngữ cảnh cha** — đảm bảo "khoản 10 Điều 3" được tìm đúng, không nhầm sang Điều khác
- Tự động bỏ qua thao tác bãi bỏ thuộc **văn bản khác** (VD: "Bãi bỏ khoản 2 Điều 17 Thông tư số 41/2024/TT-NHNN")
- Nhận dạng scope dạng **tiết trong điểm** (VD: `điểm b(i), (ii) khoản 2 Điều 14`)
- Tự động tạo **bảng so sánh nội dung cũ/mới** đính kèm (DOCX + Excel)
- Xuất văn bản hợp nhất kèm **báo cáo thay đổi JSON**

### Ví dụ kết quả — Văn bản hợp nhất

```
Điều 3. Giải thích từ ngữ
  ...
  10. Giấy tờ tùy thân bao gồm:  (sửa đổi, bổ sung bởi Điều 1 Thông tư 30/2025/TT-NHNN)
      a) Đối với cá nhân là công dân Việt Nam: thẻ căn cước công dân...
      b) Đối với cá nhân là người gốc Việt Nam chưa xác định quốc tịch...
      c) Đối với người nước ngoài cư trú tại Việt Nam: hộ chiếu hoặc...
  11. "Giao dịch thanh toán điện tử" là...   ← không thay đổi, giữ nguyên

[BÃI BỎ] Điều 6. Hồ sơ mua sắm  (bãi bỏ bởi khoản 3 Điều 1 Thông tư 30/2025/TT-NHNN)

Điều 7a. Quản lý tài sản số  (bổ sung bởi khoản 2 Điều 1 Thông tư 30/2025/TT-NHNN)
```

---

## 2. Cài đặt

### Yêu cầu

- Python **3.7** trở lên

### Cài thư viện

```bash
pip install python-docx pdfplumber openpyxl
```

| Thư viện | Mục đích | Bắt buộc? |
|----------|----------|-----------|
| `python-docx` | Đọc / xuất file `.docx` | Khi dùng đầu vào/ra `.docx` |
| `pdfplumber` | Trích xuất văn bản từ `.pdf` | Khi dùng đầu vào `.pdf` |
| `openpyxl` | Tạo bảng so sánh `.xlsx` | Khi dùng `--cmp-format xlsx` |
| `PyQt6` | Giao diện đồ họa (GUI) | Khi dùng `--gui` hoặc `gui_app.py` |

> **Lưu ý:** Nếu chỉ làm việc với file `.txt` và không cần bảng Excel hay GUI, không cần cài thêm thư viện nào.

### Kiểm tra cài đặt

```bash
python -m legal_merger --help
```

---

## 3. Cấu trúc văn bản được hỗ trợ

Công cụ nhận dạng đầy đủ **5 cấp phân cấp** của văn bản pháp lý Việt Nam:

```
Điều X. Tên điều
  1. Khoản y
  1.1 Tiểu khoản y.z          ← tuỳ chọn, không phải lúc nào cũng có
      a) Điểm
         - Tiết (gạch đầu dòng)
         (i) Tiết (số La Mã thường: i ii iii iv v vi vii viii ix x)
```

### Quy tắc nhận dạng từng cấp

| Cấp | Ký hiệu | Ví dụ | Ghi chú |
|-----|---------|-------|---------|
| **Điều** | `Điều X.` hoặc `ĐIỀU X.` | `Điều 5. Điều kiện mua sắm` | X là số nguyên, có hậu tố chữ: `5a`, `7b` |
| **Khoản** | `Y.` (số + dấu chấm) | `1. Cơ quan nhà nước...` | Chỉ một số, KHÔNG phải `1.1` |
| **Tiểu khoản** | `Y.Z` (số.số) | `1.1 Tài sản phải có...` | Phân biệt với Khoản bằng dấu chấm giữa hai số |
| **Điểm** | `a)` `b)` ... `đ)` | `a) Lập đề xuất...` | Chữ cái thường tiếng Việt + dấu ngoặc đơn |
| **Tiết** | `-` hoặc `(i)` `(ii)` ... | `(i) Quy định rõ...` | Gạch đầu dòng hoặc số La Mã thường trong ngoặc |

### Các phần được nhận dạng nhưng không parse sâu

- **Chương:** `Chương I.` `CHƯƠNG II.` — lưu làm ngữ cảnh cho Điều nằm trong chương đó
- **Mục:** `Mục 1.` — tương tự Chương

---

## 4. Định dạng văn bản sửa đổi

### Cấu trúc chuẩn của văn bản sửa đổi

```
Điều 1. Sửa đổi, bổ sung một số điều của [Tên luật/NĐ/TT gốc]

1. Sửa đổi Điều X như sau:
[Toàn bộ nội dung mới của Điều X]

2. Sửa đổi, bổ sung khoản Y Điều Z
"Y. Nội dung mới thay thế toàn bộ khoản Y..."

3. Bổ sung Điều Xa sau Điều X như sau:
[Nội dung Điều Xa mới]

4. Bãi bỏ Điều W.

5. Tại khoản 2 Điều 3, thay cụm từ "cụm từ cũ" bằng "cụm từ mới".

Điều 2. Hiệu lực thi hành
...
```

### 6 loại thao tác được hỗ trợ

#### 4.1 Sửa đổi — thay thế toàn bộ nội dung một đơn vị

**Từ khoá nhận dạng:** `sửa đổi`, `được sửa đổi`, `sửa lại`, `thay thế`

```
1. Sửa đổi Điều 4 như sau:
Điều 4. Thẩm quyền quyết định mua sắm tài sản
1. Thủ tướng Chính phủ quyết định từ 300 tỷ đồng trở lên.

2. Sửa đổi khoản 3 Điều 5 như sau:
3. Các trường hợp miễn trừ đấu thầu bao gồm...
```

#### 4.2 Sửa đổi, bổ sung — thay thế toàn bộ, tích hợp cả sửa lẫn bổ sung

**Từ khoá nhận dạng:** `sửa đổi, bổ sung` · `sửa đổi và bổ sung` · `bổ sung, sửa đổi`

Nội dung thay thế thường đặt trong **dấu ngoặc kép** ngay dưới dòng lệnh:

```
Điều 1. Sửa đổi, bổ sung khoản 10 Điều 3
"10. Giấy tờ tùy thân bao gồm:
a) Đối với cá nhân là công dân Việt Nam: thẻ căn cước công dân;
b) Đối với cá nhân là người gốc Việt Nam chưa xác định quốc tịch: giấy chứng nhận căn cước;
c) Đối với người nước ngoài cư trú tại Việt Nam: hộ chiếu..."
```

#### 4.3 Bổ sung — thêm nội dung mới chưa có trong văn bản gốc

**Từ khoá nhận dạng:** `bổ sung`, `thêm mới`, `thêm vào`

```
2. Bổ sung Điều 7a sau Điều 7 như sau:
Điều 7a. Quản lý tài sản số
1. Tài sản số bao gồm phần mềm, cơ sở dữ liệu.
```

#### 4.4 Bãi bỏ — vô hiệu hoá điều khoản

**Từ khoá nhận dạng:** `bãi bỏ`, `hủy bỏ`, `xóa bỏ`, `không còn hiệu lực`

```
3. Bãi bỏ Điều 6 về hồ sơ mua sắm tài sản.
4. Bãi bỏ khoản 2 Điều 8.
```

> **Lưu ý quan trọng:** Nếu câu "Bãi bỏ" có kèm tên văn bản khác — VD: `"Bãi bỏ khoản 2 Điều 17 Thông tư số 41/2024/TT-NHNN"` — thao tác đó được **bỏ qua hoàn toàn**, không tác động lên văn bản gốc đang hợp nhất.

> Điều khoản bị bãi bỏ vẫn giữ trong văn bản hợp nhất với nhãn `[BÃI BỎ]` kèm tham chiếu, trừ khi dùng `--no-deleted`.

#### 4.5 Thay cụm từ — tìm và thay thế trong nội dung

**Từ khoá nhận dạng:** `thay cụm từ`, `thay từ`, `được thay bằng`

```
4. Tại Điều 5, thay cụm từ "tiêu chuẩn, định mức" bằng "tiêu chuẩn kỹ thuật và định mức kinh tế".
```

> Cụm từ cần đặt trong dấu ngoặc kép `"..."`. Công cụ cũng nhận dạng dấu ngoặc kép typographic `"..."`.
> Cơ chế **negative lookahead** ngăn double-apply khi cụm từ mới là prefix của cụm từ cũ.

#### 4.6 Đổi tên — thay đổi tiêu đề của Điều

**Từ khoá nhận dạng:** `sửa đổi tên Điều`, `bổ sung tên Điều`

```
5. Sửa đổi tên Điều 19 như sau: "Điều 19. Hoạt động cung ứng dịch vụ trung gian thanh toán"
```

### Hai dạng trình bày nội dung thay thế

| Dạng | Cấu trúc | Phổ biến với |
|------|----------|-------------|
| **Marker** | `... như sau:\n[nội dung]` | Sửa đổi toàn Điều, Bổ sung Điều/khoản mới |
| **Ngoặc kép** | `\n"[nội dung]"` | Sửa đổi, bổ sung một khoản/điểm cụ thể |

### Dạng scope đặc biệt: tiết trong điểm

Khi văn bản sửa đổi chỉ định nhiều tiết trong cùng một điểm:

```
1. Sửa đổi, bổ sung điểm b(i), (ii) khoản 2 Điều 14 như sau:
```

Parser tạo **hai Amendment riêng biệt**:
- `điểm b(i) khoản 2 Điều 14` → target `(i)`
- `điểm b(ii) khoản 2 Điều 14` → target `(ii)`

Cả hai đều có `parent_clause_id = "2"` và `parent_article_id = "Điều 14"`.

---

## 5. Tham chiếu trong văn bản hợp nhất

Tham chiếu sử dụng **tiêu đề trích từ nội dung** (VD: `Thông tư 30/2025/TT-NHNN`) thay cho tên file. Mỗi nội dung bị thay đổi được gắn tham chiếu **inline**:

```
(loại thao tác bởi [điểm X] [khoản Y] [Điều Z] Thông tư 30/2025/TT-NHNN)
```

### Ví dụ các dạng tham chiếu

| Tình huống | Tham chiếu được tạo |
|------------|---------------------|
| Khoản 1 Điều 1 sửa đổi toàn bộ Điều 4 | `(sửa đổi bởi khoản 1 Điều 1 Thông tư 30/2025/TT-NHNN)` |
| Điều 1 sửa đổi, bổ sung khoản 10 Điều 3 | `(sửa đổi, bổ sung bởi Điều 1 Thông tư 30/2025/TT-NHNN)` |
| Khoản 2 Điều 1 bổ sung Điều 7a mới | `(bổ sung bởi khoản 2 Điều 1 Thông tư 30/2025/TT-NHNN)` |
| Khoản 3 Điều 1 bãi bỏ Điều 6 | `(bãi bỏ bởi khoản 3 Điều 1 Thông tư 30/2025/TT-NHNN)` |
| Khoản 4 Điều 1 thay cụm từ tại Điều 5 | `(thay cụm từ bởi khoản 4 Điều 1 Thông tư 30/2025/TT-NHNN)` |

### Vị trí hiển thị tham chiếu

- **Trong file `.txt`:** In ngay trên cùng dòng, cách bởi hai khoảng trắng
- **Trong file `.docx`:** In cùng dòng, màu xanh dương `#4472C4`, cỡ chữ 8.5pt, in nghiêng

---

## 6. Bảng so sánh nội dung cũ / mới

Được tạo **tự động** sau mỗi lần hợp nhất, gồm 6 cột:

| Cột | Nội dung |
|-----|---------|
| **STT** | Số thứ tự thay đổi |
| **Loại thao tác** | Badge màu theo loại |
| **Phạm vi tác động** | Scope đầy đủ: `khoản 10 Điều 3 — "Giấy tờ tùy thân"...` |
| **Nội dung cũ** | Snapshot chính xác từ văn bản gốc |
| **Nội dung mới** | Nội dung sau khi thay đổi |
| **Tham chiếu** | Vị trí trong văn bản sửa đổi |

### Màu sắc theo loại thao tác

| Loại | Màu nền hàng | Màu badge |
|------|-------------|-----------|
| Sửa đổi | Vàng nhạt `#FFF2CC` | Vàng đậm |
| **Sửa đổi, bổ sung** | **Tím nhạt `#EAE0F0`** | **Tím `#7030A0`** |
| Bổ sung | Xanh lá nhạt `#E2EFDA` | Xanh lá |
| Bãi bỏ | Đỏ cam nhạt `#FCE4D6` | Đỏ đậm |
| Thay cụm từ | Xanh dương nhạt `#DDEBF7` | Xanh dương |

### Highlight cụm từ (thao tác "Thay cụm từ")

- Cột **"Nội dung cũ"**: cụm từ cũ in **đậm, màu đỏ** `#C00000`
- Cột **"Nội dung mới"**: cụm từ mới in **đậm, màu xanh lá** `#375623`

### Định dạng đầu ra bảng so sánh

**DOCX** — A4 nằm ngang, header navy, màu hàng theo loại thao tác.

**XLSX** — 2 sheet:
- `Bảng so sánh`: dữ liệu đầy đủ, freeze panes, auto filter
- `Tóm tắt`: thống kê số lượng từng loại thao tác

---

## 7. Sử dụng dòng lệnh (CLI)

### Cú pháp

```bash
# Dùng package (khuyến nghị)
python -m legal_merger <van_ban_goc> -a <file_sua_doi...> [tuỳ chọn]

# Hoặc dùng file shim (tương thích ngược)
python legal_merger.py <van_ban_goc> -a <file_sua_doi...> [tuỳ chọn]
```

### Các tham số

| Tham số | Viết tắt | Mô tả | Mặc định |
|---------|----------|-------|----------|
| `van_ban_goc` | — | Đường dẫn văn bản gốc `.txt/.docx/.pdf` (bắt buộc) | — |
| `--amendments` | `-a` | Một hoặc nhiều file văn bản sửa đổi (bắt buộc) | — |
| `--output` | `-o` | Đường dẫn file kết quả | `van_ban_hop_nhat.txt` |
| `--format` | `-f` | Định dạng xuất: `txt` hoặc `docx` | `txt` |
| `--no-deleted` | — | Ẩn các điều khoản đã bị bãi bỏ trong output | Giữ lại |
| `--no-comparison` | — | Không tạo bảng so sánh | Tạo bảng |
| `--cmp-format` | — | `docx` `xlsx` hoặc cả hai | `docx xlsx` |
| `--no-clean-pages` | — | Tắt tính năng xoá số trang/header/footer | Bật |

### Ví dụ sử dụng

**Trường hợp điển hình — PDF, bảng so sánh đầy đủ:**
```bash
python -m legal_merger docs/input/15-ttkdtm.pdf \
    -a docs/input/30-suadoi-15.pdf \
    -o docs/output/van_ban_hop_nhat.txt \
    --cmp-format xlsx
```

**Xuất Word, chỉ lấy bảng Excel:**
```bash
python -m legal_merger luat_goc.docx \
    -a nghi_dinh_45.pdf \
    -o ket_qua.docx --format docx \
    --cmp-format xlsx
```

**Nhiều văn bản sửa đổi cùng lúc:**
```bash
python -m legal_merger luat_goc.txt \
    -a sua_doi_lan_1.pdf sua_doi_lan_2.docx bo_sung_2024.txt \
    -o hop_nhat_day_du.txt
```

**Không hiển thị điều khoản bị bãi bỏ, không tạo bảng so sánh:**
```bash
python -m legal_merger luat_goc.docx \
    -a nghi_dinh.pdf \
    -o sach.docx --format docx \
    --no-deleted --no-comparison
```

---

## 8. Sử dụng giao diện đồ họa (GUI)

### Cài đặt PyQt6

```bash
pip install PyQt6
```

### Khởi chạy GUI

```bash
# Cách 1 — qua flag --gui của CLI
python -m legal_merger --gui

# Cách 2 — chạy script riêng ở thư mục gốc
python gui_app.py
```

### Giao diện

```
┌─────────────────────────────────────────────────────────────┐
│ Legal Merger — Hợp nhất văn bản pháp luật                  │
├─────────────────────────────────────────────────────────────┤
│ [Văn bản đầu vào]                                           │
│   Văn bản gốc:     [________________________] [Chọn…]       │
│   Văn bản sửa đổi:                            [Thêm file…] │
│   ┌────────────────────────────────────────────────────┐    │
│   │  30-suadoi-15.pdf                                  │    │
│   └────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│ [Kết quả đầu ra]                                            │
│   File kết quả:    [________________________] [Lưu tại…]   │
│   Định dạng:       (●) TXT   ( ) DOCX                       │
├─────────────────────────────────────────────────────────────┤
│ [Tùy chọn]                                                  │
│   [✓] Tạo bảng so sánh  →  [✓] DOCX  [✓] XLSX             │
│   [✓] Hiện điều khoản đã bãi bỏ                             │
│   [✓] Xóa số trang / header / footer                        │
├─────────────────────────────────────────────────────────────┤
│             [ ▶  HỢP NHẤT VĂN BẢN ]                        │
├─────────────────────────────────────────────────────────────┤
│ [Nhật ký xử lý]                                             │
│   ══════════════════════════════════════════════════        │
│     HỢP NHẤT VĂN BẢN PHÁP LÝ  v3.0                        │
│   ✅ 23 Điều — 156 node tổng cộng                           │
│   ✅ Hoàn tất!                                               │
├─────────────────────────────────────────────────────────────┤
│ [Kết quả] [Mở văn bản hợp nhất] [Mở bảng DOCX] [Mở XLSX]  │
│           [Mở thư mục]                                      │
└─────────────────────────────────────────────────────────────┘
```

### Tính năng GUI

| Tính năng | Mô tả |
|-----------|-------|
| **File picker** | Chọn file PDF / DOCX / TXT qua hộp thoại hệ thống |
| **Danh sách sửa đổi** | Thêm nhiều file, click chọn rồi nhấn "Xóa chọn" để loại bỏ |
| **Định dạng đầu ra** | Radio button TXT / DOCX, tự động cập nhật phần mở rộng file |
| **Bảng so sánh** | Bật/tắt; chọn riêng DOCX hoặc XLSX hoặc cả hai |
| **Xử lý nền** | Merge chạy trên luồng riêng — GUI không bị đóng băng |
| **Nhật ký real-time** | Toàn bộ output từ quá trình merge hiện trong vùng log |
| **Mở kết quả** | Nút mở trực tiếp từng file đầu ra hoặc mở thư mục chứa |

> **Lưu ý:** GUI cung cấp đầy đủ các tùy chọn tương đương CLI. Không có tính năng nào bị giới hạn so với dòng lệnh.

---

## 9. Sử dụng như thư viện Python

### Hàm chính

```python
from legal_merger import merge_legal_documents

result = merge_legal_documents(
    base_file          = "15-ttkdtm.pdf",
    amendment_files    = ["30-suadoi-15.pdf"],
    output_file        = "van_ban_hop_nhat.txt",
    output_format      = "txt",            # "txt" hoặc "docx"
    keep_deleted       = True,             # False để ẩn điều bị bãi bỏ
    comparison         = True,             # False để tắt bảng so sánh
    comparison_formats = ["docx", "xlsx"], # định dạng bảng so sánh
)
```

### Trích tiêu đề văn bản

```python
from legal_merger import read_file, extract_title

text  = read_file("15-ttkdtm.pdf")
title = extract_title(text, "15-ttkdtm.pdf")
# → "Thông tư 15/2024/TT-NHNN"
```

`extract_title` ưu tiên theo thứ tự:
1. `{DocType} {số}` từ dòng `Số:` (VD: `"Thông tư 15/2024/TT-NHNN"`)
2. `{DocType} - {dòng mô tả}` nếu tìm thấy loại nhưng không có số
3. Dòng đầu tiên khớp pattern từ khoá có mô tả
4. Fallback về tên file (không có phần mở rộng)

### Sử dụng từng module riêng lẻ

```python
from legal_merger import (
    read_file, extract_title,
    DocumentParser, AmendmentParser,
    MergeEngine, OutputWriter, ComparisonTableBuilder,
)

# 1. Đọc và trích tiêu đề
base_text  = read_file("15-ttkdtm.pdf")
base_title = extract_title(base_text, "15-ttkdtm.pdf")
# → "Thông tư 15/2024/TT-NHNN"

# 2. Parse văn bản gốc → cây Node
articles, order = DocumentParser().parse(base_text, source_name=base_title)

# 3. Parse văn bản sửa đổi → list[Amendment]
amend_text  = read_file("30-suadoi-15.pdf")
amend_title = extract_title(amend_text, "30-suadoi-15.pdf")
amends = AmendmentParser().parse(amend_text, source_name=amend_title)

# In kết quả nhận dạng — kiểm tra trước khi merge
for a in amends:
    print(f"[{a.operation.name}]  scope='{a.target_scope}'"
          f"  parent='{a.parent_article_id}'")
# [MODIFY_AND_INSERT]  scope='khoản 10 Điều 3'  parent='Điều 3'

# 4. Hợp nhất
engine = MergeEngine(articles, order)
engine.apply_amendments(amends)

# 5. Xuất văn bản hợp nhất
meta = {
    "base_doc"      : base_title,
    "amendment_docs": [amend_title],
    "date"          : "18/03/2026",
}
OutputWriter().write_txt(engine.get_ordered_articles(), "output.txt", meta)
OutputWriter().write_change_report(engine.merge_log, "change_report.json")

# 6. Tạo bảng so sánh
builder = ComparisonTableBuilder(engine.merge_log, meta)
builder.write_docx("bang_so_sanh.docx")
builder.write_xlsx("bang_so_sanh.xlsx")
```

---

## 10. Tệp kết quả đầu ra

Mỗi lần chạy tạo ra **tối đa 4 file** (dựa trên tên file output `ket_qua.txt`):

| File | Mô tả |
|------|-------|
| `ket_qua.txt` | Văn bản hợp nhất với tham chiếu inline |
| `ket_qua_change_report.json` | Nhật ký thay đổi đầy đủ |
| `ket_qua_bang_so_sanh.docx` | Bảng so sánh Word, khổ A4 ngang |
| `ket_qua_bang_so_sanh.xlsx` | Bảng so sánh Excel, 2 sheet |

### Cấu trúc báo cáo thay đổi JSON

```json
{
  "generated_at": "2026-03-18T10:30:00",
  "total_changes": 2,
  "warnings": 0,
  "changes": [
    {
      "action"          : "SỬA ĐỔI, BỔ SUNG",
      "target_scope"    : "khoản 10 Điều 3",
      "source"          : "Thông tư 30/2025/TT-NHNN",
      "citation"        : "(sửa đổi, bổ sung bởi Điều 1 Thông tư 30/2025/TT-NHNN)",
      "original_content": "10. \"Giấy tờ tùy thân\" bao gồm chứng minh nhân dân...",
      "new_content"     : "10. Giấy tờ tùy thân bao gồm:\na) Đối với cá nhân...",
      "node_title"      : "khoản 10 Điều 3 — ..."
    }
  ]
}
```

---

## 11. Kiến trúc kỹ thuật

### Cấu trúc package

```
legal_merger/
├── __init__.py          # Re-export public API
├── __main__.py          # CLI: python -m legal_merger [--gui]
├── models.py            # Node, Amendment, ComparisonRow, NodeType, OperationType
├── patterns.py          # Regex cấu trúc (_RE_ARTICLE, _RE_CLAUSE, ...)
├── page_cleaner.py      # PageCleaner, read_file, clean_page_artifacts, extract_title
├── document_parser.py   # DocumentParser → cây Node
├── amendment_parser.py  # AmendmentParser → list[Amendment]  (Mask→Parse→Restore)
├── merge_engine.py      # MergeEngine → áp dụng Amendment vào cây
├── output_writer.py     # OutputWriter → TXT / DOCX / JSON
├── comparison_builder.py# ComparisonTableBuilder → DOCX + XLSX bảng so sánh
├── orchestrator.py      # merge_legal_documents() — điều phối toàn pipeline
└── gui.py               # LegalMergerApp (PyQt6) + run_gui()
```

`legal_merger.py` ở thư mục gốc là **shim tương thích ngược** — chỉ gọi vào package.
`gui_app.py` ở thư mục gốc là **shim khởi chạy GUI** — gọi `run_gui()` từ package.

### Pipeline xử lý

```
Đầu vào PDF/DOCX/TXT
    → PageCleaner          (xoá số trang, header, footer, nối câu bị ngắt)
    → extract_title        (trích "Thông tư 15/2024/TT-NHNN" từ nội dung)
    → DocumentParser       (cây phân cấp: Điều→Khoản→Tiểu khoản→Điểm→Tiết)
    → AmendmentParser      (Mask→Parse→Restore → list[Amendment])
    → MergeEngine          (áp dụng sửa đổi với tìm kiếm node theo ngữ cảnh)
    → OutputWriter         (văn bản hợp nhất với tham chiếu inline)
    → ComparisonTableBuilder (bảng so sánh DOCX/XLSX)
```

### Tìm kiếm có ngữ cảnh cha

Vấn đề: nhiều Điều cùng có khoản 1, 2, 3... Tìm "khoản 10" toàn cây có thể trả về sai.

```
scope "khoản 10 Điều 3"
    → target_id         = "10"
    → parent_article_id = "Điều 3"

_find_node_in_context("10", "Điều 3"):
    1. Tìm Node "Điều 3" trong cây     → ✅ found
    2. Tìm Node "10" trong Điều 3      → ✅ đúng node, không nhầm Điều khác
```

### Chiến lược Mask → Parse → Restore

Ngăn nội dung thay thế bị nhầm là lệnh khi tách cấu trúc văn bản sửa đổi.

**Dạng marker `"như sau:"`:**
```
1. Sửa đổi Điều 4 như sau:    →    1. Sửa đổi Điều 4 như sau:
Điều 4. [nội dung mới...]              __CONTENT_0__
2. Bổ sung Điều 7a...                  2. Bổ sung Điều 7a...   ← tách đúng
```

**Dạng ngoặc kép:**
```
Điều 1. Sửa đổi, bổ sung khoản 10 Điều 3   →   Điều 1. Sửa đổi, bổ sung khoản 10 Điều 3
"10. Giấy tờ tùy thân bao gồm:                  __CONTENT_0__
a) ... b) ... c) ..."
```

### Bộ lọc tham chiếu văn bản ngoài

Khi văn bản sửa đổi có điều khoản thi hành kiểu:

```
3. Bãi bỏ khoản 2 Điều 17 Thông tư số 41/2024/TT-NHNN ngày...
```

Parser phát hiện pattern `Điều N {DocType} số M` và **bỏ qua hoàn toàn** — không tạo DELETE operation trên văn bản gốc đang hợp nhất.

---

## 12. Câu hỏi thường gặp

**Q: "Sửa đổi, bổ sung" khác gì "Sửa đổi" đơn thuần?**
A: Về xử lý kỹ thuật, cả hai đều thay toàn bộ nội dung. Điểm khác: "Sửa đổi, bổ sung" hiển thị nhãn màu tím riêng trong bảng so sánh, phản ánh đúng bản chất pháp lý.

**Q: Nội dung trong ngoặc kép có cần thêm marker "như sau:" không?**
A: Không. Công cụ nhận dạng trực tiếp khối nội dung trong `"..."` hoặc `"..."` (typographic).

**Q: Tại sao dùng tiêu đề trích từ nội dung thay vì tên file?**
A: Tên file thường là tên rút gọn nội bộ (VD: `30-suadoi-15.pdf`). Tiêu đề trích từ nội dung (VD: `Thông tư 30/2025/TT-NHNN`) là tên chính thức theo quy định pháp lý, phù hợp để đưa vào văn bản hợp nhất.

**Q: Công cụ đảm bảo tìm đúng "khoản 10 Điều 3" thế nào khi có nhiều khoản 10?**
A: Trích `parent_article_id = "Điều 3"` từ scope và tìm khoản 10 chỉ trong phạm vi Điều 3. Nếu không tìm thấy, báo cảnh báo và bỏ qua, không tác động sai vào Điều khác.

**Q: Thao tác "Bãi bỏ" trong điều khoản thi hành có bị áp dụng nhầm không?**
A: Không. Khi câu "Bãi bỏ" chứa tên văn bản cụ thể (VD: "Thông tư số 41/2024/TT-NHNN"), parser tự động nhận biết đây là bãi bỏ thuộc văn bản khác và bỏ qua.

**Q: "điểm b(i), (ii)" được xử lý thế nào?**
A: Parser tạo hai Amendment riêng cho từng tiết `(i)` và `(ii)`, đều có ngữ cảnh cha là điểm b, khoản 2, Điều tương ứng. Mỗi tiết được merge và hiển thị trong bảng so sánh như một hàng độc lập.

**Q: Công cụ có nhận dạng được văn bản scan (PDF ảnh) không?**
A: Không. `pdfplumber` chỉ trích xuất được văn bản từ PDF có lớp text. Với PDF scan, cần qua bước OCR trước (VD: `pytesseract`).

**Q: Nếu cùng một khoản bị sửa đổi bởi nhiều văn bản?**
A: Áp dụng theo thứ tự truyền vào `-a`. Mỗi lần thay đổi được ghi vào `citations` của Node và xuất hiện như một hàng riêng trong bảng so sánh.

**Q: Điều khoản bị bãi bỏ có còn trong file kết quả không?**
A: Mặc định có, được đánh dấu `[BÃI BỎ]` kèm tham chiếu. Dùng `--no-deleted` để ẩn hoàn toàn.

**Q: Khi nào công cụ báo cảnh báo?**
A: Khi văn bản sửa đổi chỉ định tác động lên điều/khoản không tồn tại trong văn bản gốc. Thao tác đó bị bỏ qua, cảnh báo được ghi vào JSON lẫn console.

**Q: Thay cụm từ có phân biệt hoa/thường không?**
A: Có. Tìm và thay chính xác chuỗi ký tự được chỉ định, phân biệt hoa/thường.

**Q: Có hỗ trợ văn bản tiếng Anh không?**
A: Công cụ được thiết kế cho văn bản pháp lý tiếng Việt. Từ khoá nhận dạng là tiếng Việt. Cần tùy chỉnh regex trong `patterns.py` và `amendment_parser.py` nếu muốn dùng cho ngôn ngữ khác.

---

## 13. Lịch sử phiên bản

| Phiên bản | Thay đổi chính |
|-----------|----------------|
| **v5.2** | Thêm giao diện đồ họa PyQt6 (`gui.py`): file picker, danh sách văn bản sửa đổi, log real-time, mở kết quả; khởi chạy qua `--gui` hoặc `python gui_app.py` |
| **v5.1** | Cải thiện độ ổn định; sửa lỗi xuất DOCX |
| **v5.0** | Tái cấu trúc thành package (`legal_merger/` với 10 module); `python -m legal_merger` CLI; trích tiêu đề chính thức từ nội dung (`extract_title`); nhận dạng tiết trong điểm `điểm b(i),(ii)`; bộ lọc bãi bỏ thuộc văn bản ngoài; sửa double-replacement bằng negative lookahead |
| **v4.0** | Thêm `MODIFY_AND_INSERT`; tìm kiếm có ngữ cảnh cha (`parent_article_id`, `parent_clause_id`); nhận dạng nội dung thay thế trong ngoặc kép; xử lý Điều một lệnh không có khoản số |
| **v3.0** | Bảng so sánh nội dung cũ/mới (DOCX + Excel); snapshot `original_content`; màu sắc theo loại thao tác; `--no-comparison`, `--cmp-format` |
| **v2.0** | Cấu trúc dữ liệu Node cây 5 cấp; tham chiếu inline; chiến lược Mask → Parse → Restore |
| **v1.0** | Parse văn bản gốc; 4 thao tác cơ bản; xuất txt/docx + JSON |

---

## Giấy phép

Sử dụng nội bộ. Vui lòng liên hệ tác giả trước khi phân phối lại.
