Chạy merge nhanh với bộ tài liệu mẫu (TT-15 + TT-30) để kiểm tra sau khi sửa code.

Run:

```
python -m legal_merger docs/input/TT-15-2024-TT-NHNN.pdf -a docs/input/TT-30-2025-TT-NHNN.pdf -o docs/output/ket_qua_test.txt --format docx --cmp-format xlsx
```

Wait for it to complete, then report:
- Whether the command succeeded or failed
- Any warnings or errors printed to stdout/stderr
- The list of output files generated in `docs/output/`
