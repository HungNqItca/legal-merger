"""
legal_merger.py — Shim tương thích ngược.

Cho phép chạy:
    python legal_merger.py goc.pdf -a suadoi.pdf -o ket_qua.txt

Thay vì lệnh mới:
    python -m legal_merger goc.pdf -a suadoi.pdf -o ket_qua.txt
"""

from legal_merger.__main__ import main

if __name__ == "__main__":
    main()
