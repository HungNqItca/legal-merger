"""
amendment_parser.py — Phân tích văn bản sửa đổi, trích xuất danh sách Amendment.

Chiến lược xử lý:
  1. MASK nội dung thay thế bằng token __CONTENT_N__
  2. Tách cấu trúc Điều → khoản → điểm trên văn bản đã mask
  3. Khôi phục nội dung khi tạo đối tượng Amendment
"""

import re
from typing import Optional

from .models import Amendment, OperationType
from .document_parser import _norm_article_id
from .patterns import _ROMAN_PAT


class AmendmentParser:

    # Regex nhận dạng "điểm b(i), (ii) khoản N Điều M" — tiết trong điểm
    _RE_POINT_WITH_ITEMS = re.compile(
        rf'điểm\s+([a-zđ])\s*'
        rf'\((?P<first>{_ROMAN_PAT})\)'
        rf'(?P<rest>(?:\s*,\s*\({_ROMAN_PAT}\))*)'
        rf'\s+khoản\s+(\d+(?:\.\d+)?)\s+(?:Điều|ĐIỀU)\s+(\d+[a-zđ]?)',
        re.IGNORECASE,
    )

    # ── Patterns nhận dạng scope (độ cụ thể giảm dần) ────
    _SCOPE_PATTERNS = [
        # tiết ... điểm ... khoản ... Điều ...
        re.compile(
            r'tiết\s+\S+\s+điểm\s+[a-zđ]\)?\s+khoản\s+\d+(?:\.\d+)?\s+(?:Điều|ĐIỀU)\s+\d+[a-zđ]?',
            re.IGNORECASE),
        # điểm b(i), (ii) khoản N Điều M  — tiết trong điểm
        re.compile(
            rf'điểm\s+[a-zđ]\s*\({_ROMAN_PAT}\)'
            rf'(?:\s*,\s*\({_ROMAN_PAT}\))*'
            r'\s+khoản\s+\d+(?:\.\d+)?\s+(?:Điều|ĐIỀU)\s+\d+[a-zđ]?',
            re.IGNORECASE),
        # điểm ... khoản ... Điều ...  (dấu ) là tuỳ chọn)
        re.compile(
            r'điểm\s+[a-zđ]\)?\s+khoản\s+\d+(?:\.\d+)?\s+(?:Điều|ĐIỀU)\s+\d+[a-zđ]?',
            re.IGNORECASE),
        # tiểu khoản y.z Điều X
        re.compile(
            r'khoản\s+\d+\.\d+\s+(?:Điều|ĐIỀU)\s+\d+[a-zđ]?',
            re.IGNORECASE),
        # khoản y Điều X
        re.compile(
            r'khoản\s+\d+\s+(?:Điều|ĐIỀU)\s+\d+[a-zđ]?',
            re.IGNORECASE),
        # Điều X
        re.compile(
            r'(?:Điều|ĐIỀU)\s+\d+[a-zđ]?',
            re.IGNORECASE),
    ]

    # ── Patterns nhận dạng loại thao tác ──────────────────
    _OP_MODIFY = re.compile(
        r'(?:sửa đổi|được sửa(?:\s+đổi)?|sửa lại'
        r'|thay thế(?!\s+cụm từ)(?!\s+__CONTENT))\b',
        re.IGNORECASE)
    _OP_INSERT = re.compile(
        r'(?:bổ sung|thêm(?:\s+mới)?|thêm vào)\b',
        re.IGNORECASE)
    _OP_DELETE = re.compile(
        r'(?:bãi bỏ|hủy bỏ|xóa bỏ|không còn hiệu lực)\b',
        re.IGNORECASE)
    _OP_REPLACE = re.compile(
        r'thay\s+(?:cụm từ|từ|các từ)?\s*["\u201c]([^"\u201d]+)["\u201d]\s+bằng\s+["\u201c]([^"\u201d]+)["\u201d]',
        re.IGNORECASE)
    _OP_REPLACE_MASKED = re.compile(
        r'thay\s+(?:thế\s+)?(?:cụm từ|từ|các từ)?\s*(__CONTENT_\d+__)'
        r'(?:\s*,\s*__CONTENT_\d+__)*'
        r'\s+bằng\s+(?:cụm từ\s+)?(__CONTENT_\d+__)',
        re.IGNORECASE)
    _OP_MODIFY_AND_INSERT = re.compile(
        r'(?:sửa\s+đổi\s*[,và]\s*bổ\s+sung|bổ\s+sung\s*[,và]\s*sửa\s+đổi)',
        re.IGNORECASE)
    _OP_RENAME = re.compile(
        r'(?:sửa\s+đổi|bổ\s+sung|sửa\s+đổi\s*,\s*bổ\s+sung)\s+tên\s+(?:Điều|ĐIỀU)\s+\d+',
        re.IGNORECASE)
    # Phát hiện bãi bỏ thuộc VB khác: "Điều N Thông tư|Nghị định|... số M/..."
    _RE_EXT_DOC_CITATION = re.compile(
        r'(?:Điều|ĐIỀU)\s+\d+[a-zđ]?\s+'
        r'(?:Thông tư|Nghị định|Quyết định|Luật|Pháp lệnh|Chỉ thị)\s+'
        r'(?:số\s+)?\d+',
        re.IGNORECASE)
    _INSERT_AFTER = re.compile(
        r'sau\s+((?:Điều|ĐIỀU|khoản|điểm)\s+\S+(?:\s+(?:Điều|ĐIỀU)\s+\d+[a-zđ]?)?)',
        re.IGNORECASE)

    # ─────────────────────────────────────────────────────
    # API chính
    # ─────────────────────────────────────────────────────

    def parse(self, text: str, source_name: str = "", effective_date: str = "") -> list:
        amendments = []
        masked_text, content_map = self._mask_replacement_content(text)

        art_blocks = re.split(
            r'\n(?=(?:Điều|ĐIỀU)\s+\d+[a-zđ]?[\.:][ \t])',
            masked_text, flags=re.IGNORECASE
        )

        amending_articles_found = False
        for block in art_blocks:
            block = block.strip()
            if not block:
                continue
            hdr = re.match(r'^((?:Điều|ĐIỀU)\s+\d+[a-zđ]?)[\.:][ \t]*', block, re.IGNORECASE)
            if not hdr:
                continue

            has_operative_clause = bool(re.search(r'\n\d+\.\s+\S', block))
            first_line    = block.splitlines()[0]
            is_meta_header = bool(re.search(
                r'(?:một số|một số điều|một số điểm|một số khoản)',
                first_line, re.IGNORECASE))
            has_operative_header = (not is_meta_header) and bool(
                self._OP_RENAME.search(first_line) or
                self._OP_MODIFY_AND_INSERT.search(first_line) or
                self._OP_MODIFY.search(first_line) or
                self._OP_INSERT.search(first_line) or
                self._OP_DELETE.search(first_line)
            )
            if not has_operative_clause and not has_operative_header:
                continue

            amending_articles_found = True
            art_label = _norm_article_id(hdr.group(1))
            amends = self._parse_article_block_masked(
                block, art_label, content_map, source_name, effective_date
            )
            amendments.extend(amends)

        if not amending_articles_found:
            paragraphs = re.split(r'\n(?=\d+\.\s)', masked_text)
            if len(paragraphs) <= 1:
                paragraphs = re.split(r'\n\s*\n', masked_text)
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                restored = self._restore_content(para, content_map)
                amendments.extend(
                    self._parse_paragraph(restored, source_name, effective_date)
                )

        # Lọc bỏ amendment nhầm target chính VB sửa đổi
        amendments = [
            a for a in amendments
            if not (
                a.operation == OperationType.INSERT
                and a.target_id == a.amending_article
                and not a.content
            )
        ]
        return amendments

    # ─────────────────────────────────────────────────────
    # MASK / RESTORE
    # ─────────────────────────────────────────────────────

    def _mask_replacement_content(self, text: str) -> tuple:
        content_map = {}
        counter = [0]

        _MARKER = re.compile(
            r'((?:như sau|sau đây|nội dung sau|nội dung)\s*:[ \t]*\n)'
            r'(.*?)'
            r'(?=\n\d+\.\s|\n(?:Điều|ĐIỀU)\s+\d+[a-zđ]?\.\s|\Z)',
            re.DOTALL | re.IGNORECASE
        )

        def replace_marker(m):
            token = f"__CONTENT_{counter[0]}__"
            content_map[token] = m.group(2).strip()
            counter[0] += 1
            return m.group(1) + token + "\n"

        masked = _MARKER.sub(replace_marker, text)

        _QUOTED = re.compile(
            r'["\u201c]'
            r'((?:.|\n)+?)'
            r'["\u201d]',
        )

        def replace_quoted(m):
            content = m.group(1).strip()
            # Chỉ mask khi nội dung dài HOẶC chứa ký tự cấu trúc nhúng (khoản/điều/điểm)
            # Chuỗi ngắn inline (dùng trong REPLACE) giữ nguyên để _OP_REPLACE nhận dạng được
            has_structure = bool(re.search(
                r'\n\s*\d+\.\s|\n\s*[a-zđ]\)\s|\n\s*(?:Điều|ĐIỀU)\s+\d+',
                content))
            if not has_structure and len(content) < 20:
                return m.group(0)
            token = f"__CONTENT_{counter[0]}__"
            content_map[token] = content
            counter[0] += 1
            return token

        masked = _QUOTED.sub(replace_quoted, masked)
        return masked, content_map

    def _restore_content(self, text: str, content_map: dict) -> str:
        for token, content in content_map.items():
            text = text.replace(token, content)
        return text

    def _extract_content_for_token(self, text: str, content_map: dict) -> str:
        for token, content in content_map.items():
            if token in text:
                return content
        return ""

    # ─────────────────────────────────────────────────────
    # PARSE ARTICLE BLOCK (trên văn bản đã mask)
    # ─────────────────────────────────────────────────────

    def _parse_article_block_masked(self, masked_block: str, art_label: str,
                                     content_map: dict,
                                     source: str, date: str) -> list:
        amendments = []
        lines = masked_block.splitlines()

        current_clause = ""
        current_lines  = []
        has_clause_numbers = any(
            re.match(r'^\d+\.\s+\S', l.strip()) for l in lines
        )

        def flush_clause(c_label, c_lines):
            if not c_lines:
                return []
            block_text = '\n'.join(c_lines).strip()

            # Ưu tiên: nhận dạng REPLACE từ masked text
            replace_m = self._OP_REPLACE_MASKED.search(block_text)
            if replace_m:
                old_tokens = re.findall(r'__CONTENT_\d+__', block_text)
                if len(old_tokens) >= 2:
                    new_token  = old_tokens[-1]
                    old_tokens = old_tokens[:-1]
                    new_phrase = (content_map.get(new_token, "")
                                  .strip().strip('""\u201c\u201d').strip()
                                  .replace('\n', ' '))
                    results  = []
                    restored = self._restore_content(block_text, content_map)
                    multi_scopes = self._extract_all_replace_scopes(restored)
                    if not multi_scopes:
                        scope, target, par_art, par_clause = self._extract_scope_full(restored)
                        multi_scopes = [dict(
                            target_id=target or par_art or "",
                            target_scope=scope,
                            parent_article_id=par_art,
                            parent_clause_id=par_clause,
                        )]
                    for ot in old_tokens:
                        old_phrase = (content_map.get(ot, "")
                                      .strip().strip('""\u201c\u201d').strip()
                                      .replace('\n', ' '))
                        if not old_phrase or not new_phrase:
                            continue
                        for s in multi_scopes:
                            results.append(Amendment(
                                operation=OperationType.REPLACE,
                                target_id=s['target_id'],
                                target_scope=s['target_scope'],
                                old_phrase=old_phrase,
                                new_phrase=new_phrase,
                                parent_article_id=s['parent_article_id'],
                                parent_clause_id=s['parent_clause_id'],
                                source_doc=source,
                                effective_date=date,
                                amending_article=art_label,
                                amending_clause=c_label,
                                amending_point="",
                            ))
                    if results:
                        return results

            # Xử lý "điểm b(i), (ii) khoản N Điều M" — nhiều tiết cùng lúc
            pwi_m = self._RE_POINT_WITH_ITEMS.search(block_text)
            if pwi_m:
                point_letter = pwi_m.group(1)
                point_id     = point_letter + ")"
                khoan        = pwi_m.group(4)
                dieu         = pwi_m.group(5)
                parent_art   = f"Điều {dieu}"
                # Thu thập tất cả item IDs từ scope
                first_item = pwi_m.group('first').lower()
                rest_items = re.findall(rf'\(({_ROMAN_PAT})\)',
                                        pwi_m.group('rest'), re.IGNORECASE)
                all_items  = [f"({first_item})"] + [f"({r.lower()})" for r in rest_items]
                # Lấy nội dung và tách theo từng tiết
                raw_content = self._extract_content_for_token(block_text, content_map)
                item_contents = self._split_content_by_roman_items(raw_content, all_items)
                # Xác định loại thao tác
                restored_instr = self._restore_content(block_text, content_map)
                if self._OP_MODIFY_AND_INSERT.search(restored_instr):
                    op = OperationType.MODIFY_AND_INSERT
                elif self._OP_MODIFY.search(restored_instr):
                    op = OperationType.MODIFY
                else:
                    op = OperationType.MODIFY_AND_INSERT
                results = []
                for item_id, item_content in zip(all_items, item_contents):
                    scope = (f"điểm {point_letter}({item_id.strip('()')}) "
                             f"khoản {khoan} Điều {dieu}")
                    results.append(Amendment(
                        operation         = op,
                        target_id         = item_id,
                        target_scope      = scope,
                        content           = item_content,
                        parent_article_id = parent_art,
                        parent_clause_id  = khoan,
                        parent_point_id   = point_id,
                        source_doc        = source,
                        effective_date    = date,
                        amending_article  = art_label,
                        amending_clause   = c_label,
                        amending_point    = point_id,
                    ))
                return results

            # Tách theo điểm a) b) c) trong instruction
            point_splits = re.split(r'\n(?=[a-zđ]\)\s)', block_text)
            results = []

            if len(point_splits) > 1:
                for pb in point_splits[1:]:
                    pb  = pb.strip()
                    pm  = re.match(r'^([a-zđ])\)\s', pb)
                    point = (pm.group(1) + ")") if pm else ""
                    restored_pb = self._restore_content(pb, content_map)
                    new_content = self._extract_content_for_token(pb, content_map)
                    for a in self._parse_paragraph(
                        restored_pb, source, date,
                        amending_article=art_label,
                        amending_clause=c_label,
                        amending_point=point,
                    ):
                        if not a.content:
                            a.content = new_content
                        results.append(a)
            else:
                restored    = self._restore_content(block_text, content_map)
                new_content = self._extract_content_for_token(block_text, content_map)
                for a in self._parse_paragraph(
                    restored, source, date,
                    amending_article=art_label,
                    amending_clause=c_label,
                    amending_point="",
                ):
                    if not a.content:
                        a.content = new_content
                    results.append(a)
            return results

        # Cấu trúc B: không có khoản số → strip "Điều N." rồi xử lý toàn block
        if not has_clause_numbers:
            cleaned = []
            for l in lines:
                m = re.match(r'^(?:Điều|ĐIỀU)\s+\d+[a-zđ]?[\.:][ \t]*(.*)', l.strip(),
                             re.IGNORECASE | re.DOTALL)
                cleaned.append(m.group(1) if m else l)
            return flush_clause("", cleaned)

        # Cấu trúc A: có khoản số → tách từng khoản
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if re.match(r'^(?:Điều|ĐIỀU)\s+\d+[a-zđ]?[\.:]', stripped, re.IGNORECASE):
                continue
            cm = re.match(r'^(\d+)\.\s+\S', stripped)
            if cm:
                if current_lines:
                    amendments.extend(flush_clause(current_clause, current_lines))
                current_clause = cm.group(1)
                current_lines  = [stripped]
            else:
                current_lines.append(stripped)

        if current_lines:
            amendments.extend(flush_clause(current_clause, current_lines))

        return amendments

    # ─────────────────────────────────────────────────────
    # PARSE PARAGRAPH
    # ─────────────────────────────────────────────────────

    def _parse_paragraph(self, text: str, source: str, date: str,
                          amending_article: str = "",
                          amending_clause:  str = "",
                          amending_point:   str = "") -> list:
        """Nhận dạng loại thao tác và đích của một đoạn văn. Trả về list Amendment."""
        base_kwargs = dict(
            source_doc=source, effective_date=date,
            amending_article=amending_article,
            amending_clause=amending_clause,
            amending_point=amending_point,
        )

        # -1. RENAME (kiểm tra trước MODIFY_AND_INSERT)
        if self._OP_RENAME.search(text):
            scope, target, parent_art, parent_clause = self._extract_scope_full(text)
            new_name = self._extract_new_content(text)
            if target:
                return [Amendment(
                    operation=OperationType.RENAME,
                    target_id=target, target_scope=scope,
                    content=new_name,
                    parent_article_id=parent_art,
                    parent_clause_id=parent_clause,
                    **base_kwargs)]

        # 0. MODIFY_AND_INSERT (kiểm tra trước MODIFY đơn thuần)
        if self._OP_MODIFY_AND_INSERT.search(text):
            scope, target, parent_art, parent_clause = self._extract_scope_full(text)
            content = self._extract_new_content(text)
            if target:
                return [Amendment(
                    operation=OperationType.MODIFY_AND_INSERT,
                    target_id=target, target_scope=scope,
                    content=content,
                    parent_article_id=parent_art,
                    parent_clause_id=parent_clause,
                    **base_kwargs)]

        # 1. Thay cụm từ
        m = self._OP_REPLACE.search(text)
        if m:
            old_ph, new_ph = m.group(1), m.group(2)
            multi_scopes = self._extract_all_replace_scopes(text)
            if multi_scopes:
                return [Amendment(
                    operation=OperationType.REPLACE,
                    target_id=s['target_id'], target_scope=s['target_scope'],
                    old_phrase=old_ph, new_phrase=new_ph,
                    parent_article_id=s['parent_article_id'],
                    parent_clause_id=s['parent_clause_id'],
                    **base_kwargs,
                ) for s in multi_scopes]
            scope, target, parent_art, parent_clause = self._extract_scope_full(text)
            if target:
                return [Amendment(
                    operation=OperationType.REPLACE,
                    target_id=target, target_scope=scope,
                    old_phrase=old_ph, new_phrase=new_ph,
                    parent_article_id=parent_art,
                    parent_clause_id=parent_clause,
                    **base_kwargs)]

        # 2. Bãi bỏ
        if self._OP_DELETE.search(text):
            # Bỏ qua nếu là bãi bỏ thuộc VB khác ("Điều N Thông tư số X/...")
            if self._RE_EXT_DOC_CITATION.search(text):
                return []
            # Thử tìm nhiều target cùng lúc ("bãi bỏ khoản 1, 2, 3 Điều 5")
            multi = self._parse_multi_delete(text, base_kwargs)
            if multi:
                return multi
            scope, target, parent_art, parent_clause = self._extract_scope_full(text)
            if target:
                return [Amendment(
                    operation=OperationType.DELETE,
                    target_id=target, target_scope=scope,
                    parent_article_id=parent_art,
                    parent_clause_id=parent_clause,
                    **base_kwargs)]

        # 3. Bổ sung
        if self._OP_INSERT.search(text):
            scope, target, parent_art, parent_clause = self._extract_scope_full(text)
            after   = self._extract_insert_after(text)
            content = self._extract_new_content(text)
            if target:
                return [Amendment(
                    operation=OperationType.INSERT,
                    target_id=target, target_scope=scope,
                    content=content, insert_after=after,
                    parent_article_id=parent_art,
                    parent_clause_id=parent_clause,
                    **base_kwargs)]

        # 4. Sửa đổi đơn thuần
        if self._OP_MODIFY.search(text):
            scope, target, parent_art, parent_clause = self._extract_scope_full(text)
            content = self._extract_new_content(text)
            if target:
                return [Amendment(
                    operation=OperationType.MODIFY,
                    target_id=target, target_scope=scope,
                    content=content,
                    parent_article_id=parent_art,
                    parent_clause_id=parent_clause,
                    **base_kwargs)]

        return []

    def _extract_all_replace_scopes(self, text: str) -> list:
        """
        Trích tất cả scope đích từ mệnh đề "tại ..." trong lệnh REPLACE nhiều vị trí.
        Ví dụ: "tại câu mũ khoản 2, điểm b, điểm đ khoản 2 Điều 7"
               → 3 scope dict: khoản 2, điểm b), điểm đ)

        Trả về list[dict(target_id, target_scope, parent_article_id, parent_clause_id)].
        Trả về [] nếu chỉ có 1 scope (để caller dùng flow đơn bình thường).
        """
        tai_m = re.search(
            r'tại\s+(?:câu\s+mũ\s+|tiêu\s+đề\s+)?(.+?)(?:\s*\.|$)',
            text, re.IGNORECASE | re.DOTALL,
        )
        if not tai_m:
            return []

        scope_str = tai_m.group(1).strip()

        # Anchor: Điều cuối cùng trong mệnh đề
        art_m = re.search(r'(?:Điều|ĐIỀU)\s+(\d+[a-zđ]?)', scope_str, re.IGNORECASE)
        if not art_m:
            return []
        parent_art = f"Điều {art_m.group(1)}"

        # Khoản cuối cùng — fallback cho điểm không khai rõ khoản
        khoan_m = re.search(r'khoản\s+(\d+(?:\.\d+)?)', scope_str, re.IGNORECASE)
        parent_clause_default = khoan_m.group(1) if khoan_m else ""

        scopes = []

        # "câu mũ khoản Y" → body của khoản Y chính nó (không phải node con)
        for m in re.finditer(r'câu\s+mũ\s+khoản\s+(\d+(?:\.\d+)?)', scope_str, re.IGNORECASE):
            k = m.group(1)
            scopes.append(dict(
                target_id=k,
                target_scope=f"khoản {k} {parent_art}",
                parent_article_id=parent_art,
                parent_clause_id="",
            ))

        # "điểm X [khoản Y [Điều Z]]"
        for m in re.finditer(
            r'điểm\s+([a-zđ])\)?\s*'
            r'(?:khoản\s+(\d+(?:\.\d+)?)\s*'
            r'(?:(?:Điều|ĐIỀU)\s+(\d+[a-zđ]?))?)?',
            scope_str, re.IGNORECASE,
        ):
            point = m.group(1).lower() + ")"
            k = m.group(2) or parent_clause_default
            a = f"Điều {m.group(3)}" if m.group(3) else parent_art
            scopes.append(dict(
                target_id=point,
                target_scope=(f"điểm {point} khoản {k} {a}" if k
                              else f"điểm {point} {a}"),
                parent_article_id=a,
                parent_clause_id=k,
            ))

        # Loại bỏ trùng lặp, giữ thứ tự
        seen, unique = set(), []
        for s in scopes:
            key = (s['target_id'], s['parent_article_id'], s['parent_clause_id'])
            if key not in seen:
                seen.add(key)
                unique.append(s)

        return unique if len(unique) > 1 else []

    def _parse_multi_delete(self, text: str, base_kwargs: dict) -> list:
        """
        Tách lệnh bãi bỏ nhiều target trên cùng một dòng.
        Ví dụ: "bãi bỏ khoản 1, 2, 3 Điều 5"  → 3 Amendment DELETE
               "bãi bỏ điểm a, b khoản 1 Điều 5" → 2 Amendment DELETE
        Trả về [] nếu chỉ có 1 target (để caller tiếp tục xử lý đơn).
        """
        art_m = re.search(r'(?:Điều|ĐIỀU)\s+(\d+[a-zđ]?)', text, re.IGNORECASE)
        if not art_m:
            return []
        parent_art = f"Điều {art_m.group(1)}"

        # "bãi bỏ khoản 1, 2, 3 Điều N" hoặc "khoản 1 và 2 Điều N"
        mc_m = re.search(
            r'khoản\s+([\d.,\s]*(?:[và]\s*[\d.,\s]*)?)(?:Điều|ĐIỀU)',
            text, re.IGNORECASE,
        )
        if mc_m:
            ids = re.findall(r'\d+(?:\.\d+)?', mc_m.group(1))
            if len(ids) > 1:
                return [Amendment(
                    operation=OperationType.DELETE,
                    target_id=cid,
                    target_scope=f"khoản {cid} {parent_art}",
                    parent_article_id=parent_art,
                    parent_clause_id="",
                    **base_kwargs,
                ) for cid in ids]

        # "bãi bỏ điểm a, b, c khoản N Điều M"
        mp_m = re.search(
            r'điểm\s+([a-zđ](?:\s*[,và]\s*[a-zđ])+)\s+khoản\s+(\d+(?:\.\d+)?)\s+(?:Điều|ĐIỀU)',
            text, re.IGNORECASE,
        )
        if mp_m:
            letters = re.findall(r'[a-zđ]', mp_m.group(1), re.IGNORECASE)
            khoan = mp_m.group(2)
            if len(letters) > 1:
                return [Amendment(
                    operation=OperationType.DELETE,
                    target_id=lt.lower() + ")",
                    target_scope=f"điểm {lt.lower()}) khoản {khoan} {parent_art}",
                    parent_article_id=parent_art,
                    parent_clause_id=khoan,
                    **base_kwargs,
                ) for lt in letters]

        return []

    # ─────────────────────────────────────────────────────
    # Trích xuất scope
    # ─────────────────────────────────────────────────────

    def _extract_scope_full(self, text: str):
        """Trả về (scope_text, target_id, parent_article_id, parent_clause_id)."""
        for pat in self._SCOPE_PATTERNS:
            m = pat.search(text)
            if m:
                scope = m.group(0).strip()
                target, parent_art, parent_clause = self._scope_to_ids(scope)
                return scope, target, parent_art, parent_clause
        return "", "", "", ""

    def _scope_to_ids(self, scope: str) -> tuple:
        """Phân tích scope → (target_id, parent_article_id, parent_clause_id)."""
        sl = scope.lower()

        art_m = re.search(r'điều\s+(\d+[a-zđ]?)', sl)
        parent_art    = f"Điều {art_m.group(1)}" if art_m else ""
        parent_clause = ""

        m = re.search(r'tiết\s+(\S+)', sl)
        if m:
            km = re.search(r'khoản\s+(\d+(?:\.\d+)?)', sl)
            if km:
                parent_clause = km.group(1)
            return m.group(1), parent_art, parent_clause

        # điểm b(i) — tiết trong điểm: trả về tiết đầu tiên
        m = re.search(rf'điểm\s+([a-zđ])\s*\(({_ROMAN_PAT})\)', sl, re.IGNORECASE)
        if m:
            point_id  = m.group(1) + ")"
            item_code = m.group(2)
            km = re.search(r'khoản\s+(\d+(?:\.\d+)?)', sl)
            if km:
                parent_clause = km.group(1)
            return f"({item_code})", parent_art, parent_clause

        # điểm — hỗ trợ "điểm a)" và "điểm a " (không ngoặc)
        m = re.search(r'điểm\s+([a-zđ])(?:\)|[\s,]|$)', sl)
        if m:
            km = re.search(r'khoản\s+(\d+(?:\.\d+)?)', sl)
            if km:
                parent_clause = km.group(1)
            return m.group(1) + ")", parent_art, parent_clause

        # tiểu khoản x.y (không kèm Điều)
        m = re.search(r'khoản\s+(\d+\.\d+)', sl)
        if m:
            return m.group(1), parent_art, ""

        m = re.search(r'khoản\s+(\d+)\b', sl)
        if m:
            return m.group(1), parent_art, ""

        if parent_art:
            return parent_art, "", ""

        return "", "", ""

    def _extract_insert_after(self, text: str) -> str:
        m = self._INSERT_AFTER.search(text)
        if not m:
            return ""
        tid, _, _ = self._scope_to_ids(m.group(1))
        return tid

    def _extract_new_content(self, text: str) -> str:
        _, content = self._split_instruction_and_content(text)
        if content:
            return content
        return self._extract_quoted_content(text)

    def _extract_quoted_content(self, text: str) -> str:
        m = re.search(r'\u201c(.+?)\u201d', text, re.DOTALL)
        if m:
            return m.group(1).strip()
        m = re.search(r'"(.{20,}?)"', text, re.DOTALL)
        if m:
            return m.group(1).strip()
        return ""

    def _split_content_by_roman_items(self, content: str, item_ids: list) -> list:
        """
        Tách nội dung thành từng phần theo dấu tiết La Mã.
        Ví dụ: "(i) text...\n(ii) text..." → ["(i) text...", "(ii) text..."]
        """
        if not content:
            return [""] * len(item_ids)

        _roman_boundary = re.compile(
            rf'(?=\({_ROMAN_PAT}\))',
            re.IGNORECASE,
        )
        raw_parts = _roman_boundary.split(content.strip())
        parts_map = {}
        for part in raw_parts:
            part = part.strip()
            if not part:
                continue
            m = re.match(rf'^(\({_ROMAN_PAT}\))', part, re.IGNORECASE)
            if m:
                parts_map[m.group(1).lower()] = part

        return [parts_map.get(iid.lower(), "") for iid in item_ids]

    def _split_instruction_and_content(self, text: str):
        for marker in ['như sau:\n', 'như sau:', 'sau đây:\n', 'sau đây:',
                       'nội dung sau:', 'nội dung:\n']:
            idx = text.lower().find(marker.lower())
            if idx != -1:
                instruction = text[:idx + len(marker)].strip()
                new_content = text[idx + len(marker):].strip()
                return instruction, new_content
        return text, ""
