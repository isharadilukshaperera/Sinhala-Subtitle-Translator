"""
Live translation preview console widget for Anti Gravity.
Displays streaming dialog pairs (English -> Sinhala) as GPU batches finish.
"""
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
    QCheckBox,
    QFrame,
    QFileDialog,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor
import html as html_module

from anti_gravity.config import (
    COLOR_ACCENT,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
)

# Maximum number of translation blocks to keep in the preview console
MAX_PREVIEW_BLOCKS = 500


class LivePreviewWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "dashboard-card")
        self._block_count = 0
        self._full_log: list[str] = []  # stores every block for export
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Live Translation Preview Console")
        title.setProperty("class", "card-title")
        header_layout.addWidget(title)

        header_layout.addStretch()

        self.auto_scroll_cb = QCheckBox("Auto-Scroll")
        self.auto_scroll_cb.setChecked(True)
        self.auto_scroll_cb.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
        header_layout.addWidget(self.auto_scroll_cb)

        btn_export = QPushButton("Export")
        btn_export.setProperty("class", "btn-action-sm")
        btn_export.setToolTip("Export full translation log to a text file")
        btn_export.clicked.connect(self._export_log)
        header_layout.addWidget(btn_export)

        btn_clear = QPushButton("Clear")
        btn_clear.setProperty("class", "btn-action-sm")
        btn_clear.clicked.connect(self.clear_console)
        header_layout.addWidget(btn_clear)

        layout.addLayout(header_layout)

        # Console Text Display
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("""
            QTextEdit {
                background-color: #0A0C10;
                border: 1px solid #1F2432;
                border-radius: 10px;
                padding: 10px;
                font-family: 'Consolas', 'Cascadia Code', 'Segoe UI', monospace;
                font-size: 12px;
                line-height: 1.5;
            }
        """)
        layout.addWidget(self.console)

        # Set initial welcome placeholder
        self.append_info_message("System ready. Subtitle translations will stream here in real-time dialog-by-dialog.")

    def clear_console(self):
        self.console.clear()
        self._block_count = 0
        self._full_log.clear()

    def _trim_oldest_blocks(self):
        """Remove the oldest blocks when the console exceeds MAX_PREVIEW_BLOCKS.

        Uses QTextEdit's block-based document model to remove leading content
        efficiently, avoiding expensive full-document re-renders.
        """
        doc = self.console.document()
        # Each translation pair / info message is roughly 1 top-level block
        # Remove ~20% of blocks at a time to avoid frequent trimming
        blocks_to_remove = max(1, MAX_PREVIEW_BLOCKS // 5)
        cursor = QTextCursor(doc)
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        # Select the first N blocks worth of content
        for _ in range(blocks_to_remove):
            if not cursor.movePosition(QTextCursor.MoveOperation.NextBlock, QTextCursor.MoveMode.KeepAnchor):
                break
        cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        # Also remove any leading whitespace / empty lines left over
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        cursor.movePosition(QTextCursor.MoveOperation.NextBlock, QTextCursor.MoveMode.KeepAnchor)
        if cursor.selectedText().strip() == "":
            cursor.removeSelectedText()
        self._block_count -= blocks_to_remove

    def append_info_message(self, text: str):
        html = f'<div style="color: {COLOR_TEXT_MUTED}; font-style: italic; margin-bottom: 8px;">ℹ {text}</div>'
        self._full_log.append(f"[INFO] {text}")
        self._block_count += 1
        if self._block_count > MAX_PREVIEW_BLOCKS:
            self._trim_oldest_blocks()
        self.console.append(html)
        if self.auto_scroll_cb.isChecked():
            self.console.moveCursor(QTextCursor.MoveOperation.End)

    def append_translation_pair(self, file_name: str, line_no: int, en_text: str, si_text: str, score: float = 1.0, issues: list = None):
        """Append an English-Sinhala dialog translation block with quality badge."""
        # Escape HTML to prevent SRT formatting tags (<i>, <b>, <font>) from rendering as markup
        en_text_safe = html_module.escape(en_text)
        si_text_safe = html_module.escape(si_text)
        if score >= 0.85:
            badge_html = '<span style="background-color: rgba(16, 185, 129, 0.2); color: #10B981; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: bold;">🟢 Spoken</span>'
        elif score >= 0.6:
            badge_html = '<span style="background-color: rgba(245, 158, 11, 0.2); color: #F59E0B; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: bold;">🟡 Check</span>'
        else:
            badge_html = '<span style="background-color: rgba(239, 68, 68, 0.2); color: #EF4444; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: bold;">🔴 Review</span>'

        issue_notes = ""
        if issues:
            issue_notes = f'<div style="color: #F59E0B; font-size: 10px; margin-top: 2px;">⚠ {"; ".join(issues[:2])}</div>'

        html = f"""
        <div style="margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid #161A24;">
            <div style="display: flex; justify-content: space-between; color: #64748B; font-size: 10px; font-weight: 600; margin-bottom: 2px;">
                <span>#{line_no} • {file_name}</span> &nbsp;&nbsp; {badge_html}
            </div>
            <div style="color: #94A3B8; font-size: 12px; margin-bottom: 3px;">
                <span style="color: #64748B; font-weight: bold;">EN:</span> {en_text_safe}
            </div>
            <div style="color: #FFFFFF; font-size: 13px; font-weight: 500;">
                <span style="color: {COLOR_ACCENT}; font-weight: bold;">SI:</span> {si_text_safe}
            </div>
            {issue_notes}
        </div>
        """
        # Store in full log for export
        issue_str = f" [{'; '.join(issues[:2])}]" if issues else ""
        self._full_log.append(f"#{line_no} [{file_name}] score={score:.2f}{issue_str}\n  EN: {en_text}\n  SI: {si_text}")

        self._block_count += 1
        if self._block_count > MAX_PREVIEW_BLOCKS:
            self._trim_oldest_blocks()
        self.console.append(html)
        if self.auto_scroll_cb.isChecked():
            self.console.moveCursor(QTextCursor.MoveOperation.End)

    def _export_log(self):
        """Save the full (un-trimmed) translation log to a user-chosen text file."""
        if not self._full_log:
            self.append_info_message("Nothing to export — the log is empty.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Translation Log", "translation_log.txt",
            "Text Files (*.txt);;All Files (*)",
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write("\n\n".join(self._full_log))
                self.append_info_message(f"Log exported to: {path}")
            except Exception as e:
                self.append_info_message(f"Export failed: {e}")

