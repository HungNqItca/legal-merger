"""
patterns.py — Regex nhận dạng cấu trúc văn bản gốc.

Dùng chung cho DocumentParser và bất kỳ module nào cần nhận dạng
các cấp phân cấp trong văn bản pháp luật Việt Nam.
"""

import re

# Điều 1 / Điều 1a / ĐIỀU 1.
_RE_ARTICLE = re.compile(
    r'^((?:DIEU|ĐIỀU|Điều|dieu)\s+(\d+[a-zđ]?))[\.:\s]',
    re.IGNORECASE | re.UNICODE
)

# 1.   2.   10.   — khoản (KHÔNG phải 1.1)
_RE_CLAUSE = re.compile(r'^(\d+)\.\s+\S')

# 1.1  2.3  10.2  — tiểu khoản
_RE_SUB_CLAUSE = re.compile(r'^(\d+\.\d+)\s+\S')

# a)  b)  c)  đ)
_RE_POINT = re.compile(r'^([a-zđ])\)\s', re.UNICODE)

# -  (gạch đầu dòng)  hoặc  i)  ii)  iii)...  hoặc  (i)  (ii)  (iii)...
_RE_ITEM = re.compile(
    r'^(?:-\s'
    r'|\((?:i{1,3}|iv|vi{0,3}|ix|x)\)\s'   # dạng (i)  (ii) ...
    r'|(?:i{1,3}|iv|vi{0,3}|ix|x)\)\s'      # dạng i)   ii) ...
    r')',
    re.IGNORECASE
)

# Chương / Mục — chỉ lưu context, không tạo node
_RE_CHAPTER = re.compile(r'^(Chương|CHƯƠNG|Mục|MỤC)\s+', re.IGNORECASE)
