"""
page_cleaner.py — Làm sạch số trang / header / footer, đọc file và trích tiêu đề.
"""

import re
import os
import sys
from pathlib import Path

from .patterns import _RE_ARTICLE


class PageCleaner:
    """
    Loại bỏ số trang và header/footer lặp lại ra khỏi văn bản.

    Áp dụng 4 lớp lọc theo thứ tự:
      Lớp 1 — Xoá pattern số trang rõ ràng  ("Trang X", "- X -", "X/Y"...)
      Lớp 2 — Xoá số nguyên đứng một mình trên dòng
      Lớp 3 — Xoá header/footer lặp lại (xuất hiện >= ngưỡng)
      Lớp 4 — Nối câu bị ngắt bởi số trang
    """

    # ── Lớp 1: Pattern rõ ràng ────────────────────────────
    _RE_TRANG   = re.compile(r'^\s*[Tt][Rr][Aa][Nn][Gg]\s+\d+\s*$')
    _RE_DASH    = re.compile(r'^\s*[-–—]+\s*\d+\s*[-–—]+\s*$')
    _RE_PAREN   = re.compile(r'^\s*[\(\[]\s*\d+\s*[\)\]]\s*$')
    _RE_FRAC    = re.compile(r'^\s*(?:[Tt]rang\s*)?\d+\s*/\s*\d+\s*$')
    _RE_PAGE_EN = re.compile(r'^\s*[Pp](?:age|\.)\s*\d+\s*$')
    _L1_PATTERNS = [_RE_TRANG, _RE_DASH, _RE_PAREN, _RE_FRAC, _RE_PAGE_EN]

    # ── Lớp 2: Số nguyên đứng một mình ───────────────────
    _RE_BARE_NUM = re.compile(r'^\s*\d{1,4}\s*$')

    # ── Lớp 4: Nhận dạng câu bị ngắt ─────────────────────
    _RE_SENTENCE_END = re.compile(r'[.!?;:»")\]]\s*$')
    _RE_LOWER_START  = re.compile(r'^\s*[a-zđăâêôơưàáảãạ]', re.UNICODE)

    def __init__(self, repeat_threshold: int = 3, remove_ambiguous: bool = True):
        self.repeat_threshold = repeat_threshold
        self.remove_ambiguous = remove_ambiguous

    def clean(self, text: str) -> tuple:
        """
        Trả về (cleaned_text, report).
        report = dict với các khoá:
            removed_explicit, removed_bare_num, removed_repeated,
            joined_broken, suspicious_lines
        """
        report = {
            "removed_explicit": 0,
            "removed_bare_num": 0,
            "removed_repeated": 0,
            "joined_broken"   : 0,
            "suspicious_lines": [],
        }
        lines    = text.splitlines()
        repeated = self._find_repeated_lines(lines)

        cleaned_lines = []
        i = 0
        while i < len(lines):
            line     = lines[i]
            stripped = line.strip()

            if self._is_explicit_page_num(stripped):
                report["removed_explicit"] += 1
                i += 1
                continue

            if stripped in repeated and stripped:
                report["removed_repeated"] += 1
                i += 1
                continue

            if self._RE_BARE_NUM.match(stripped):
                if self._is_page_number_by_context(lines, i):
                    report["removed_bare_num"] += 1
                    if cleaned_lines and i + 1 < len(lines):
                        prev      = cleaned_lines[-1].rstrip()
                        next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
                        if (not self._RE_SENTENCE_END.search(prev)
                                and self._RE_LOWER_START.match(next_line)):
                            report["joined_broken"] += 1
                    i += 1
                    continue
                elif self.remove_ambiguous:
                    report["removed_bare_num"] += 1
                    i += 1
                    continue
                else:
                    report["suspicious_lines"].append((i + 1, stripped))

            cleaned_lines.append(line)
            i += 1

        cleaned_lines = self._join_broken_sentences(cleaned_lines, report)
        return '\n'.join(cleaned_lines), report

    # ── Lớp 1 ─────────────────────────────────────────────

    def _is_explicit_page_num(self, stripped: str) -> bool:
        return any(pat.match(stripped) for pat in self._L1_PATTERNS)

    # ── Lớp 2 ─────────────────────────────────────────────

    def _is_page_number_by_context(self, lines: list, idx: int) -> bool:
        prev_line = lines[idx - 1].strip() if idx > 0 else ""
        next_line = lines[idx + 1].strip() if idx + 1 < len(lines) else ""

        strong_signals = 0
        if not prev_line or not next_line:
            strong_signals += 1
        if prev_line and self._RE_SENTENCE_END.search(prev_line):
            strong_signals += 1
        if re.match(r'^(?:Điều|ĐIỀU|Chương|CHƯƠNG|Mục|MỤC)\s+', next_line,
                    re.IGNORECASE):
            strong_signals += 2
        if re.match(r'^\d+\.\s+\S', next_line):
            strong_signals += 1
        return strong_signals >= 1

    # ── Lớp 3 ─────────────────────────────────────────────

    def _find_repeated_lines(self, lines: list) -> set:
        from collections import Counter
        counts = Counter()
        for line in lines:
            s = line.strip()
            if not s or len(s) < 5:
                continue
            if re.match(r'^(?:Điều|ĐIỀU|Khoản|khoản|\d+\.)\s', s, re.IGNORECASE):
                continue
            counts[s] += 1
        return {line for line, cnt in counts.items()
                if cnt >= self.repeat_threshold}

    # ── Lớp 4 ─────────────────────────────────────────────

    def _join_broken_sentences(self, lines: list, report: dict) -> list:
        MAX_LINE_LEN = 60
        if len(lines) < 2:
            return lines
        result = [lines[0]]
        for i in range(1, len(lines)):
            curr   = lines[i]
            prev   = result[-1]
            prev_s = prev.rstrip()
            curr_s = curr.strip()
            should_join = (
                prev_s and curr_s
                and not self._RE_SENTENCE_END.search(prev_s)
                and self._RE_LOWER_START.match(curr_s)
                and len(prev_s) <= MAX_LINE_LEN
                and not re.match(
                    r'^(?:Điều|ĐIỀU|\d+\.\s|[a-zđ]\)\s|-\s)',
                    curr_s, re.IGNORECASE)
            )
            if should_join:
                result[-1] = prev_s + ' ' + curr_s
                report["joined_broken"] += 1
            else:
                result.append(curr)
        return result


# ─────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────

def clean_page_artifacts(text: str,
                         repeat_threshold: int = 3,
                         remove_ambiguous: bool = True,
                         verbose: bool = False) -> str:
    """Làm sạch số trang và header/footer khỏi text thô."""
    cleaner = PageCleaner(repeat_threshold=repeat_threshold,
                          remove_ambiguous=remove_ambiguous)
    cleaned, report = cleaner.clean(text)

    if verbose:
        total = (report["removed_explicit"] + report["removed_bare_num"]
                 + report["removed_repeated"])
        if total or report["joined_broken"]:
            print(f"   🧹 Làm sạch số trang: xoá {total} dòng"
                  f" | nối {report['joined_broken']} câu bị ngắt")
            if report["removed_explicit"]:
                print(f"      ↳ Số đứng một mình: {report['removed_bare_num']}")
            if report["removed_repeated"]:
                print(f"      ↳ Header/footer lặp lại: {report['removed_repeated']}")
        if report["suspicious_lines"]:
            print(f"   ⚠️  {len(report['suspicious_lines'])} dòng số nghi vấn (đã giữ): "
                  + ", ".join(f"dòng {l}" for l, _ in report["suspicious_lines"][:5]))
    return cleaned


def read_file(filepath: str,
              clean_pages: bool = True,
              verbose: bool = False) -> str:
    """
    Đọc văn bản từ .txt / .docx / .pdf.
    Nếu clean_pages=True, tự động loại bỏ số trang và header/footer.
    """
    ext = os.path.splitext(filepath)[1].lower()

    if ext == '.txt':
        with open(filepath, 'r', encoding='utf-8') as f:
            raw = f.read()

    elif ext == '.docx':
        try:
            from docx import Document
            raw = '\n'.join(p.text for p in Document(filepath).paragraphs)
        except ImportError:
            sys.exit("❌ Cần cài: pip install python-docx")

    elif ext == '.pdf':
        try:
            import pdfplumber
            raw = ""
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        raw += t + '\n'
        except ImportError:
            sys.exit("❌ Cần cài: pip install pdfplumber")

    else:
        raise ValueError(f"Định dạng không hỗ trợ: {ext}")

    if clean_pages:
        raw = clean_page_artifacts(raw, verbose=verbose)
    return raw


# ─────────────────────────────────────────────────────────
# Trích tiêu đề văn bản
# ─────────────────────────────────────────────────────────

_DOC_TYPE_PATTERN = re.compile(
    r'^(THÔNG TƯ|NGHỊ ĐỊNH|QUYẾT ĐỊNH|LUẬT|PHÁP LỆNH|CHỈ THỊ|HIẾN PHÁP|BỘ LUẬT|VĂN BẢN)$',
    re.IGNORECASE,
)
_SO_PATTERN = re.compile(r'^Số\s*:\s*(.+?)(?:\t|\s{3,}|$)', re.IGNORECASE)
_TITLE_INLINE_PATTERN = re.compile(
    r'^(THÔNG TƯ|NGHỊ ĐỊNH|QUYẾT ĐỊNH|LUẬT|PHÁP LỆNH|CHỈ THỊ|HIẾN PHÁP|BỘ LUẬT|VĂN BẢN)\s+.+',
    re.IGNORECASE,
)


def extract_title(text: str, file_name: str) -> str:
    """Trích tiêu đề văn bản từ nội dung.

    Ưu tiên: "{DocType} {number}"  →  "Thông tư 15/2024/TT-NHNN"
    Dự phòng: dòng loại-văn-bản có kèm mô tả, rồi tên file.
    """
    lines = text.split('\n')
    doc_type = None
    doc_number = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if doc_number is None:
            m = _SO_PATTERN.match(stripped)
            if m:
                raw_cap = m.group(1).strip()
                # Mã số có dạng: "15 /2024/TT-NHNN Hà Nội, ..."
                # Dùng \S+ cho phần code để dừng tại dấu cách đầu tiên sau code
                num_m = re.match(r'(\d[\d ]*/\s*\d{4}\s*/\s*\S+)', raw_cap)
                doc_number = re.sub(r'\s+', '', num_m.group(1)) if num_m else re.sub(r'\s+', '', raw_cap)

        if doc_type is None:
            m = _DOC_TYPE_PATTERN.match(stripped)
            if m:
                raw = m.group(1)
                doc_type = raw[0].upper() + raw[1:].lower()  # "Thông tư"

        if doc_type and doc_number:
            break

    if doc_type and doc_number:
        return f"{doc_type} {doc_number}"

    # Dự phòng: tìm dòng mô tả ngay sau dòng loại văn bản
    if doc_type:
        found_type = False
        desc_parts = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                if found_type and desc_parts:
                    break
                continue
            if not found_type:
                if _DOC_TYPE_PATTERN.match(stripped):
                    found_type = True
                continue
            if re.match(r'^[_\-=]{3,}$', stripped):
                if desc_parts:
                    break
                continue
            if re.match(r'^(Căn cứ|Theo đề nghị|Xét đề nghị)', stripped, re.IGNORECASE):
                break
            desc_parts.append(stripped)
        if desc_parts:
            return f"{doc_type} - {' '.join(desc_parts)}"

    # Dự phòng: dòng "THÔNG TƯ ..." trên cùng một dòng
    for line in lines[:10]:
        line = line.strip()
        if _TITLE_INLINE_PATTERN.match(line):
            return line

    # Dự phòng: dòng đầu có nội dung (không phải tiêu đề Điều)
    for line in lines[:5]:
        line = line.strip()
        if line and 10 < len(line) < 200 and not _RE_ARTICLE.search(line):
            return line

    return Path(file_name).stem
