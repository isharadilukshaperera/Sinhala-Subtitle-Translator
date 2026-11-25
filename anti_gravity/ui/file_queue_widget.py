"""
File queue widget for Anti Gravity.
Supports drag-and-drop, multi-file browsing, reordering (Up/Down),
row removal, and live progress indicators.
"""
from typing import List, Optional
import os

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFileDialog,
    QFrame,
    QAbstractItemView,
)
from PyQt6.QtCore import pyqtSignal, Qt, QUrl
from PyQt6.QtGui import QDragEnterEvent, QDropEvent

from anti_gravity.config import (
    COLOR_ACCENT,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
    DEFAULT_OUTPUT_SUFFIX,
)
from anti_gravity.styles import get_status_badge_html
from anti_gravity.worker import QueueItem
from anti_gravity.subtitle_parser import SubtitleFile


class FileQueueWidget(QFrame):
    queue_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "dashboard-card")
        self.setAcceptDrops(True)
        self.queue_items: List[QueueItem] = []
        self.custom_output_dir: Optional[str] = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # Header Title and Total Count
        header_layout = QHBoxLayout()
        title = QLabel("Subtitle Queue")
        title.setProperty("class", "card-title")
        header_layout.addWidget(title)

        header_layout.addStretch()

        self.queue_summary_label = QLabel("0 files (0 lines)")
        self.queue_summary_label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 12px; font-weight: 600;")
        header_layout.addWidget(self.queue_summary_label)

        layout.addLayout(header_layout)

        # Drop Zone Banner
        self.drop_banner = QFrame()
        self.drop_banner.setProperty("class", "drop-zone")
        banner_layout = QHBoxLayout(self.drop_banner)
        banner_layout.setContentsMargins(12, 10, 12, 10)
        
        banner_icon = QLabel("📥")
        banner_icon.setStyleSheet("font-size: 18px;")
        banner_layout.addWidget(banner_icon)

        banner_text = QLabel("Drag & Drop English .srt files here, or use the buttons below")
        banner_text.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px; font-weight: 500;")
        banner_layout.addWidget(banner_text)
        banner_layout.addStretch()

        layout.addWidget(self.drop_banner)

        # Queue Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["#", "File Name", "Lines", "Progress", "Status", "Actions"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)

        # Header sizing
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)   # #
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) # File Name
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)   # Lines
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)   # Progress
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)   # Status
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)   # Actions

        self.table.setColumnWidth(0, 42)
        self.table.setColumnWidth(2, 70)
        self.table.setColumnWidth(3, 130)
        self.table.setColumnWidth(4, 165)
        self.table.setColumnWidth(5, 125)

        # Set default row height to avoid cropped status badges
        self.table.verticalHeader().setDefaultSectionSize(54)

        layout.addWidget(self.table)

        # Button Controls Bar
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(10)

        self.btn_add_files = QPushButton("+ Add Files")
        self.btn_add_files.clicked.connect(self.browse_files)
        btn_bar.addWidget(self.btn_add_files)

        self.btn_add_folder = QPushButton("📁 Add Folder")
        self.btn_add_folder.clicked.connect(self.browse_folder)
        btn_bar.addWidget(self.btn_add_folder)

        btn_bar.addStretch()

        self.btn_clear = QPushButton("🗑 Clear All")
        self.btn_clear.clicked.connect(self.clear_queue)
        btn_bar.addWidget(self.btn_clear)

        layout.addLayout(btn_bar)

    def set_custom_output_dir(self, directory: Optional[str]):
        self.custom_output_dir = directory
        # Re-compute output paths for all items
        for item in self.queue_items:
            item.output_path = self._compute_output_path(item.file_path)

    def _compute_output_path(self, file_path: str) -> str:
        base_dir = self.custom_output_dir if self.custom_output_dir else os.path.dirname(file_path)
        base_name, _ = os.path.splitext(os.path.basename(file_path))
        out_name = f"{base_name}{DEFAULT_OUTPUT_SUFFIX}"
        return os.path.join(base_dir, out_name)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.drop_banner.setProperty("class", "drop-zone-active")
            self.drop_banner.style().unpolish(self.drop_banner)
            self.drop_banner.style().polish(self.drop_banner)

    def dragLeaveEvent(self, event):
        self.drop_banner.setProperty("class", "drop-zone")
        self.drop_banner.style().unpolish(self.drop_banner)
        self.drop_banner.style().polish(self.drop_banner)

    def dropEvent(self, event: QDropEvent):
        self.drop_banner.setProperty("class", "drop-zone")
        self.drop_banner.style().unpolish(self.drop_banner)
        self.drop_banner.style().polish(self.drop_banner)

        paths = []
        for url in event.mimeData().urls():
            local_path = url.toLocalFile()
            if os.path.isdir(local_path):
                for root, _, files in os.walk(local_path):
                    for file in files:
                        if file.lower().endswith(".srt"):
                            paths.append(os.path.join(root, file))
            elif local_path.lower().endswith(".srt"):
                paths.append(local_path)

        if paths:
            self.add_files(paths)
        event.acceptProposedAction()

    def browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select English Subtitle Files",
            "",
            "SubRip Subtitles (*.srt)"
        )
        if files:
            self.add_files(files)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder Containing Subtitles")
        if folder:
            paths = []
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith(".srt"):
                        paths.append(os.path.join(root, file))
            if paths:
                self.add_files(paths)

    def add_files(self, paths: List[str]):
        """Add unique SRT files to queue."""
        existing_paths = {item.file_path for item in self.queue_items}
        for path in paths:
            abs_path = os.path.abspath(path)
            if abs_path in existing_paths or not os.path.isfile(abs_path):
                continue

            try:
                sub = SubtitleFile(abs_path)
                total_lines = sub.total_lines
            except Exception:
                total_lines = 0

            item = QueueItem(
                file_path=abs_path,
                output_path=self._compute_output_path(abs_path),
                file_name=os.path.basename(abs_path),
                total_lines=total_lines,
                status="Queued",
                completed_lines=0
            )
            self.queue_items.append(item)
            existing_paths.add(abs_path)

        self.refresh_table()
        self.queue_changed.emit()

    def move_up(self, index: int):
        if index > 0 and index < len(self.queue_items):
            self.queue_items[index - 1], self.queue_items[index] = (
                self.queue_items[index],
                self.queue_items[index - 1],
            )
            self.refresh_table()
            self.queue_changed.emit()

    def move_down(self, index: int):
        if index >= 0 and index < len(self.queue_items) - 1:
            self.queue_items[index], self.queue_items[index + 1] = (
                self.queue_items[index + 1],
                self.queue_items[index],
            )
            self.refresh_table()
            self.queue_changed.emit()

    def remove_item(self, index: int):
        if 0 <= index < len(self.queue_items):
            self.queue_items.pop(index)
            self.refresh_table()
            self.queue_changed.emit()

    def clear_queue(self):
        self.queue_items.clear()
        self.refresh_table()
        self.queue_changed.emit()

    def update_file_status(self, index: int, status: str):
        if 0 <= index < len(self.queue_items):
            self.queue_items[index].status = status
            cell_widget = self.table.cellWidget(index, 4)
            if cell_widget:
                lbl = cell_widget.findChild(QLabel)
                if lbl:
                    lbl.setText(get_status_badge_html(status))
            self.table.setRowHeight(index, 54)

    def update_file_progress(self, index: int, done: int, total: int):
        if 0 <= index < len(self.queue_items):
            self.queue_items[index].completed_lines = done
            self.queue_items[index].total_lines = total
            item = self.table.item(index, 3)
            if item:
                pct = int((done / total * 100)) if total > 0 else 0
                item.setText(f"{done}/{total} ({pct}%)")

    def refresh_table(self):
        self.table.setRowCount(len(self.queue_items))
        total_lines = 0

        for row, item in enumerate(self.queue_items):
            total_lines += item.total_lines
            self.table.setRowHeight(row, 54)

            # 0: Index
            num_item = QTableWidgetItem(str(row + 1))
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, num_item)

            # 1: File Name
            name_item = QTableWidgetItem(item.file_name)
            name_item.setToolTip(item.file_path)
            self.table.setItem(row, 1, name_item)

            # 2: Total Lines
            lines_item = QTableWidgetItem(str(item.total_lines))
            lines_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, lines_item)

            # 3: Progress
            pct = int((item.completed_lines / item.total_lines * 100)) if item.total_lines > 0 else 0
            prog_item = QTableWidgetItem(f"{item.completed_lines}/{item.total_lines} ({pct}%)")
            prog_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, prog_item)

            # 4: Status (HTML Badge)
            badge_widget = QWidget()
            bw_layout = QHBoxLayout(badge_widget)
            bw_layout.setContentsMargins(6, 6, 6, 6)
            bw_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge_label = QLabel()
            badge_label.setText(get_status_badge_html(item.status))
            badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            bw_layout.addWidget(badge_label)
            self.table.setCellWidget(row, 4, badge_widget)

            # 5: Actions Widget (Up, Down, Remove)
            actions_widget = QWidget()
            act_layout = QHBoxLayout(actions_widget)
            act_layout.setContentsMargins(4, 4, 4, 4)
            act_layout.setSpacing(6)
            act_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            btn_up = QPushButton("▲")
            btn_up.setProperty("class", "btn-action-sm")
            btn_up.setToolTip("Move Up")
            btn_up.setEnabled(row > 0)
            btn_up.clicked.connect(lambda _, r=row: self.move_up(r))
            act_layout.addWidget(btn_up)

            btn_down = QPushButton("▼")
            btn_down.setProperty("class", "btn-action-sm")
            btn_down.setToolTip("Move Down")
            btn_down.setEnabled(row < len(self.queue_items) - 1)
            btn_down.clicked.connect(lambda _, r=row: self.move_down(r))
            act_layout.addWidget(btn_down)

            btn_rem = QPushButton("✕")
            btn_rem.setProperty("class", "btn-action-sm")
            btn_rem.setToolTip("Remove")
            btn_rem.setStyleSheet("QPushButton:hover { color: #EF4444; border: 1px solid #EF4444; }")
            btn_rem.clicked.connect(lambda _, r=row: self.remove_item(r))
            act_layout.addWidget(btn_rem)

            self.table.setCellWidget(row, 5, actions_widget)

        self.queue_summary_label.setText(f"{len(self.queue_items)} files ({total_lines:,} lines)")

