"""
gui.py — Giao diện đồ họa PyQt6 cho Legal Merger.

Khởi chạy:
    python -m legal_merger --gui
    python gui_app.py
"""

import os
import sys
import traceback

from PyQt6.QtCore import QThread, pyqtSignal, QUrl, Qt
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QLineEdit, QPushButton, QListWidget,
    QRadioButton, QButtonGroup, QCheckBox, QTextEdit,
    QProgressBar, QFileDialog, QMessageBox, QSizePolicy, QSplitter, QMenu,
)
from PyQt6.QtGui import QDesktopServices

from .orchestrator import merge_legal_documents


# ---------------------------------------------------------------------------
# Stdout → Qt signal bridge (plain Python class, no QObject — avoids
# cross-thread signal delivery issues in PyQt6)
# ---------------------------------------------------------------------------

class _OutputStream:
    def __init__(self, emit_fn):
        self._emit = emit_fn

    def write(self, text: str):
        if text:
            self._emit(text)

    def flush(self):
        pass


# ---------------------------------------------------------------------------
# Background worker thread
# ---------------------------------------------------------------------------

class MergeWorker(QThread):
    log_signal      = pyqtSignal(str)
    finished_signal = pyqtSignal(dict)
    error_signal    = pyqtSignal(str)

    def __init__(self, params: dict):
        super().__init__()
        self.params = params

    def run(self):
        stream = _OutputStream(self.log_signal.emit)
        old_stdout = sys.stdout
        sys.stdout = stream
        try:
            result = merge_legal_documents(**self.params)
            self.finished_signal.emit(result)
        except BaseException:
            self.error_signal.emit(traceback.format_exc())
        finally:
            sys.stdout = old_stdout


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

_FILE_FILTER = "Văn bản pháp lý (*.pdf *.docx *.txt);;Tất cả (*)"

_INPUT_DIR  = os.path.abspath("docs/input")
_OUTPUT_DIR = os.path.abspath("docs/output")
_DEFAULT_OUTPUT = os.path.join(_OUTPUT_DIR, "van_ban_hop_nhat.txt")


class LegalMergerApp(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Legal Merger — Hợp nhất văn bản pháp luật")
        self.setMinimumWidth(680)
        self._worker: MergeWorker | None = None
        self._result: dict = {}

        self._build_menubar()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(6)
        root.setContentsMargins(12, 12, 12, 12)

        root.addWidget(self._build_input_group())
        root.addWidget(self._build_output_group())
        root.addWidget(self._build_options_group())
        root.addWidget(self._build_log_group(), stretch=1)

    # ------------------------------------------------------------------
    # UI builders
    # ------------------------------------------------------------------

    def _build_input_group(self) -> QGroupBox:
        box = QGroupBox("Văn bản đầu vào")
        layout = QVBoxLayout(box)

        # Base file row
        base_row = QHBoxLayout()
        base_row.addWidget(QLabel("Văn bản gốc:"))
        self._base_edit = QLineEdit()
        self._base_edit.setPlaceholderText("Chọn file PDF / DOCX / TXT …")
        base_row.addWidget(self._base_edit, 1)
        btn_base = QPushButton("Chọn…")
        btn_base.setFixedWidth(72)
        btn_base.clicked.connect(self._pick_base_file)
        base_row.addWidget(btn_base)
        layout.addLayout(base_row)

        # Amendment files
        amend_header = QHBoxLayout()
        amend_header.addWidget(QLabel("Văn bản sửa đổi:"))
        amend_header.addStretch()
        btn_add = QPushButton("Thêm file…")
        btn_add.clicked.connect(self._add_amendment_files)
        amend_header.addWidget(btn_add)
        btn_remove = QPushButton("Xóa chọn")
        btn_remove.clicked.connect(self._remove_selected_amendment)
        amend_header.addWidget(btn_remove)
        layout.addLayout(amend_header)

        self._amend_list = QListWidget()
        self._amend_list.setFixedHeight(52)
        self._amend_list.setToolTip("Chọn item rồi nhấn 'Xóa chọn' để loại bỏ")
        layout.addWidget(self._amend_list)

        box.setFixedHeight(148)
        return box

    def _build_output_group(self) -> QGroupBox:
        box = QGroupBox("Kết quả đầu ra")
        layout = QVBoxLayout(box)

        # Output path row
        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("File kết quả:"))
        self._out_edit = QLineEdit(_DEFAULT_OUTPUT)
        out_row.addWidget(self._out_edit, 1)
        btn_save = QPushButton("Lưu tại…")
        btn_save.setFixedWidth(72)
        btn_save.clicked.connect(self._pick_output_file)
        out_row.addWidget(btn_save)
        layout.addLayout(out_row)

        # Format radio buttons
        fmt_row = QHBoxLayout()
        fmt_row.addWidget(QLabel("Định dạng:"))
        self._fmt_group = QButtonGroup(self)
        self._fmt_txt  = QRadioButton("TXT")
        self._fmt_docx = QRadioButton("DOCX")
        self._fmt_txt.setChecked(True)
        self._fmt_group.addButton(self._fmt_txt,  0)
        self._fmt_group.addButton(self._fmt_docx, 1)
        self._fmt_txt.toggled.connect(self._sync_output_ext)
        fmt_row.addWidget(self._fmt_txt)
        fmt_row.addWidget(self._fmt_docx)
        fmt_row.addStretch()
        layout.addLayout(fmt_row)

        box.setFixedHeight(88)
        return box

    def _build_options_group(self) -> QGroupBox:
        box = QGroupBox("Tùy chọn")
        layout = QVBoxLayout(box)
        layout.setSpacing(6)

        # Single options row + run button
        row = QHBoxLayout()

        self._chk_cmp = QCheckBox("Bảng so sánh")
        self._chk_cmp.setChecked(True)
        self._chk_cmp.toggled.connect(self._toggle_comparison_formats)
        self._chk_cmp_docx = QCheckBox("DOCX")
        self._chk_cmp_docx.setChecked(True)
        self._chk_cmp_xlsx = QCheckBox("XLSX")
        self._chk_cmp_xlsx.setChecked(True)

        self._chk_deleted = QCheckBox("Hiện điều bãi bỏ")
        self._chk_deleted.setChecked(True)
        self._chk_clean = QCheckBox("Xóa số trang/header")
        self._chk_clean.setChecked(True)

        row.addWidget(self._chk_cmp)
        row.addWidget(self._chk_cmp_docx)
        row.addWidget(self._chk_cmp_xlsx)
        row.addSpacing(16)
        row.addWidget(self._chk_deleted)
        row.addWidget(self._chk_clean)
        row.addStretch()

        self._run_btn = QPushButton("▶  HỢP NHẤT VĂN BẢN")
        self._run_btn.setFixedHeight(32)
        font = self._run_btn.font()
        font.setPointSize(10)
        font.setBold(True)
        self._run_btn.setFont(font)
        self._run_btn.clicked.connect(self._run_merge)
        row.addWidget(self._run_btn)

        layout.addLayout(row)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setFixedHeight(4)
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        box.setFixedHeight(70)
        return box

    def _build_log_group(self) -> QGroupBox:
        box = QGroupBox("Nhật ký xử lý")
        layout = QVBoxLayout(box)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMinimumHeight(80)
        self._log.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._log.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        font = QFont("Consolas", 9)
        self._log.setFont(font)
        self._log.setStyleSheet(
            "QTextEdit { background: #1e1e1e; color: #d4d4d4; border: none; }"
        )
        layout.addWidget(self._log)

        return box

    def _build_menubar(self):
        mb = self.menuBar()
        menu = mb.addMenu("Mở file kết quả")

        self._action_open_main     = menu.addAction("Mở văn bản hợp nhất")
        self._action_open_cmp_docx = menu.addAction("Mở bảng so sánh DOCX")
        self._action_open_cmp_xlsx = menu.addAction("Mở bảng so sánh XLSX")
        menu.addSeparator()
        self._action_open_folder   = menu.addAction("Mở thư mục chứa kết quả")

        for act in (self._action_open_main, self._action_open_cmp_docx,
                    self._action_open_cmp_xlsx, self._action_open_folder):
            act.setEnabled(False)

        self._action_open_main.triggered.connect(
            lambda: self._open_file(self._result.get("output_file", ""))
        )
        self._action_open_cmp_docx.triggered.connect(
            lambda: self._open_file(
                (self._result.get("comparison_files") or {}).get("docx", "")
            )
        )
        self._action_open_cmp_xlsx.triggered.connect(
            lambda: self._open_file(
                (self._result.get("comparison_files") or {}).get("xlsx", "")
            )
        )
        self._action_open_folder.triggered.connect(
            lambda: self._open_folder(self._result.get("output_file", ""))
        )

    # ------------------------------------------------------------------
    # Slots — file pickers
    # ------------------------------------------------------------------

    def _pick_base_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn văn bản gốc", _INPUT_DIR, _FILE_FILTER
        )
        if path:
            self._base_edit.setText(path)
            self._reset()

    def _reset(self):
        self._amend_list.clear()
        self._log.clear()
        self._result = {}
        for act in (self._action_open_main, self._action_open_cmp_docx,
                    self._action_open_cmp_xlsx, self._action_open_folder):
            act.setEnabled(False)

    def _add_amendment_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Chọn văn bản sửa đổi", _INPUT_DIR, _FILE_FILTER
        )
        existing = {
            self._amend_list.item(i).text()
            for i in range(self._amend_list.count())
        }
        for p in paths:
            if p not in existing:
                self._amend_list.addItem(p)

    def _remove_selected_amendment(self):
        for item in self._amend_list.selectedItems():
            self._amend_list.takeItem(self._amend_list.row(item))

    def _pick_output_file(self):
        ext = "txt" if self._fmt_txt.isChecked() else "docx"
        filter_str = (
            "Text files (*.txt)" if ext == "txt"
            else "Word documents (*.docx)"
        )
        default = os.path.join(_OUTPUT_DIR, f"van_ban_hop_nhat.{ext}")
        path, _ = QFileDialog.getSaveFileName(
            self, "Lưu file kết quả", default, filter_str
        )
        if path:
            self._out_edit.setText(path)

    # ------------------------------------------------------------------
    # Slots — options
    # ------------------------------------------------------------------

    def _sync_output_ext(self, txt_checked: bool):
        path = self._out_edit.text()
        if not path:
            return
        base, _ = os.path.splitext(path)
        self._out_edit.setText(base + (".txt" if txt_checked else ".docx"))

    def _toggle_comparison_formats(self, checked: bool):
        self._chk_cmp_docx.setEnabled(checked)
        self._chk_cmp_xlsx.setEnabled(checked)

    # ------------------------------------------------------------------
    # Slots — run merge
    # ------------------------------------------------------------------

    def _run_merge(self):
        base_file = self._base_edit.text().strip()
        if not base_file:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng chọn văn bản gốc.")
            return
        if not os.path.isfile(base_file):
            QMessageBox.warning(self, "Không tìm thấy file",
                                f"Văn bản gốc không tồn tại:\n{base_file}")
            return

        amendment_files = [
            self._amend_list.item(i).text()
            for i in range(self._amend_list.count())
        ]
        if not amendment_files:
            QMessageBox.warning(self, "Thiếu thông tin",
                                "Vui lòng thêm ít nhất một văn bản sửa đổi.")
            return

        output_file = self._out_edit.text().strip() or "van_ban_hop_nhat.txt"

        cmp_formats = []
        if self._chk_cmp.isChecked():
            if self._chk_cmp_docx.isChecked():
                cmp_formats.append("docx")
            if self._chk_cmp_xlsx.isChecked():
                cmp_formats.append("xlsx")

        params = dict(
            base_file          = base_file,
            amendment_files    = amendment_files,
            output_file        = output_file,
            output_format      = "txt" if self._fmt_txt.isChecked() else "docx",
            keep_deleted       = self._chk_deleted.isChecked(),
            comparison         = self._chk_cmp.isChecked(),
            comparison_formats = cmp_formats or ["docx", "xlsx"],
            clean_pages        = self._chk_clean.isChecked(),
        )

        self._log.clear()
        self._run_btn.setEnabled(False)
        self._progress.setVisible(True)

        self._worker = MergeWorker(params)
        self._worker.log_signal.connect(self._on_log, Qt.ConnectionType.QueuedConnection)
        self._worker.finished_signal.connect(self._on_finished, Qt.ConnectionType.QueuedConnection)
        self._worker.error_signal.connect(self._on_error, Qt.ConnectionType.QueuedConnection)
        self._worker.start()

    # ------------------------------------------------------------------
    # Slots — worker callbacks
    # ------------------------------------------------------------------

    def _on_log(self, text: str):
        self._log.insertPlainText(text)
        self._log.ensureCursorVisible()

    def _on_finished(self, result: dict):
        self._result = result
        self._run_btn.setEnabled(True)
        self._progress.setVisible(False)

        cmp_files = result.get("comparison_files") or {}
        self._action_open_main.setEnabled(True)
        self._action_open_cmp_docx.setEnabled(bool(cmp_files.get("docx")))
        self._action_open_cmp_xlsx.setEnabled(bool(cmp_files.get("xlsx")))
        self._action_open_folder.setEnabled(True)

    def _on_error(self, msg: str):
        self._run_btn.setEnabled(True)
        self._progress.setVisible(False)
        self._log.insertPlainText("\n[LỖI]\n" + msg)
        self._log.ensureCursorVisible()
        QMessageBox.critical(self, "Lỗi khi xử lý", msg.splitlines()[-1])

    # ------------------------------------------------------------------
    # Helpers — open files/folder
    # ------------------------------------------------------------------

    def _open_file(self, path: str):
        if path and os.path.isfile(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(path)))
        else:
            QMessageBox.information(self, "Không tìm thấy", f"File không tồn tại:\n{path}")

    def _open_folder(self, path: str):
        folder = os.path.dirname(os.path.abspath(path)) if path else ""
        if folder and os.path.isdir(folder):
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _exception_hook(exc_type, exc_value, exc_tb):
    """Prevent PyQt6 from silently swallowing or crashing on slot exceptions."""
    if issubclass(exc_type, (SystemExit, KeyboardInterrupt)):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    traceback.print_exception(exc_type, exc_value, exc_tb)


def run_gui():
    sys.excepthook = _exception_hook
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Legal Merger")
    window = LegalMergerApp()
    window.resize(720, 900)
    window.showMaximized()
    sys.exit(app.exec())
