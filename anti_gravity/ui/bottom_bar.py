"""
Bottom control bar widget for Translator.
Hosts output folder selector, model dropdown, compute device selector (GPU / CPU),
queue progress bar, and execution action buttons.
"""
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QComboBox,
    QProgressBar,
    QFileDialog,
)
from PyQt6.QtCore import pyqtSignal, Qt

from anti_gravity.config import (
    COLOR_ACCENT,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    SUPPORTED_MODELS,
    DEFAULT_MODEL_ID,
)
from anti_gravity.system_monitor import get_gpu_display_name


class BottomBar(QWidget):
    start_queue_requested = pyqtSignal()
    abort_current_requested = pyqtSignal()
    abort_queue_requested = pyqtSignal()
    output_dir_changed = pyqtSignal(str)
    model_changed = pyqtSignal(str)
    device_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 10, 18, 14)
        layout.setSpacing(12)

        # Upper row: Output Folder, Model Selector & Compute Device
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        # 1. Output Folder Picker
        out_box = QHBoxLayout()
        out_box.setSpacing(6)
        out_label = QLabel("Output:")
        out_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-weight: 600; font-size: 12px;")
        out_box.addWidget(out_label)

        self.out_path_edit = QLineEdit()
        self.out_path_edit.setPlaceholderText("Default: Same as input SRT (_sinhala_clean.srt)")
        self.out_path_edit.setReadOnly(True)
        out_box.addWidget(self.out_path_edit, 1)

        btn_browse_out = QPushButton("Browse...")
        btn_browse_out.clicked.connect(self._browse_output_dir)
        out_box.addWidget(btn_browse_out)

        btn_reset_out = QPushButton("Reset")
        btn_reset_out.setProperty("class", "btn-action-sm")
        btn_reset_out.setToolTip("Reset to source folder")
        btn_reset_out.clicked.connect(self._reset_output_dir)
        out_box.addWidget(btn_reset_out)

        top_row.addLayout(out_box, 5)

        # 2. AI Model Selector Dropdown
        model_box = QHBoxLayout()
        model_box.setSpacing(6)
        model_label = QLabel("AI Model:")
        model_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-weight: 600; font-size: 12px;")
        model_box.addWidget(model_label)

        self.model_combo = QComboBox()
        for model_id, info in SUPPORTED_MODELS.items():
            self.model_combo.addItem(info["name"], model_id)
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)
        model_box.addWidget(self.model_combo, 1)

        top_row.addLayout(model_box, 4)

        # 3. Compute Device Selector (GPU vs CPU)
        device_box = QHBoxLayout()
        device_box.setSpacing(6)
        dev_label = QLabel("Device:")
        dev_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-weight: 600; font-size: 12px;")
        device_box.addWidget(dev_label)

        self.device_combo = QComboBox()
        _gpu_label = get_gpu_display_name()
        self.device_combo.addItem(f"⚡ GPU ({_gpu_label})", "cuda")
        self.device_combo.addItem("🖥 CPU (System)", "cpu")
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)
        device_box.addWidget(self.device_combo)

        top_row.addLayout(device_box, 3)

        layout.addLayout(top_row)

        # Lower row: Overall Progress Bar + Master Action Buttons
        bot_row = QHBoxLayout()
        bot_row.setSpacing(14)

        # Queue Progress with status caption
        prog_container = QVBoxLayout()
        prog_container.setSpacing(4)

        prog_caption_row = QHBoxLayout()
        self.status_caption = QLabel("Queue Status: Idle")
        self.status_caption.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px; font-weight: 600;")
        self.prog_detail_label = QLabel("0 / 0 lines (0%)")
        self.prog_detail_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 11px; font-weight: 600;")

        prog_caption_row.addWidget(self.status_caption)
        prog_caption_row.addStretch()
        prog_caption_row.addWidget(self.prog_detail_label)
        prog_container.addLayout(prog_caption_row)

        self.queue_bar = QProgressBar()
        self.queue_bar.setRange(0, 100)
        self.queue_bar.setValue(0)
        self.queue_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #12151D;
                border: 1px solid #232938;
                border-radius: 6px;
                min-height: 14px;
                max-height: 14px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {COLOR_ACCENT};
                border-radius: 5px;
            }}
        """)
        prog_container.addWidget(self.queue_bar)
        bot_row.addLayout(prog_container, 6)

        # Action Buttons
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        self.btn_abort_file = QPushButton("Abort File")
        self.btn_abort_file.setProperty("class", "btn-danger")
        self.btn_abort_file.setEnabled(False)
        self.btn_abort_file.clicked.connect(self.abort_current_requested.emit)
        btn_box.addWidget(self.btn_abort_file)

        self.btn_abort_all = QPushButton("Abort All")
        self.btn_abort_all.setProperty("class", "btn-danger")
        self.btn_abort_all.setEnabled(False)
        self.btn_abort_all.clicked.connect(self.abort_queue_requested.emit)
        btn_box.addWidget(self.btn_abort_all)

        # Start Queue Button
        self.btn_start = QPushButton("⚡ Start Queue")
        self.btn_start.setProperty("class", "btn-primary")
        self.btn_start.setMinimumWidth(160)
        self._apply_start_button_idle_style()
        self.btn_start.clicked.connect(self.start_queue_requested.emit)
        btn_box.addWidget(self.btn_start)

        bot_row.addLayout(btn_box, 4)
        layout.addLayout(bot_row)

    def _apply_start_button_idle_style(self):
        self.btn_start.setText("⚡ Start Queue")
        self.btn_start.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLOR_ACCENT};
                border: 1px solid {COLOR_ACCENT};
                border-radius: 8px;
                color: #0E1015;
                font-size: 14px;
                font-weight: 800;
                padding: 10px 18px;
            }}
            QPushButton:hover {{
                background-color: #FF8533;
                border: 1px solid #FF8533;
            }}
            QPushButton:disabled {{
                background-color: #382012;
                border: 1px solid #5C3218;
                color: #8C6246;
            }}
        """)

    def _browse_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if folder:
            self.out_path_edit.setText(folder)
            self.output_dir_changed.emit(folder)

    def _reset_output_dir(self):
        self.out_path_edit.clear()
        self.output_dir_changed.emit("")

    def _on_model_changed(self, idx: int):
        model_id = self.model_combo.itemData(idx)
        if model_id:
            self.model_changed.emit(model_id)

    def _on_device_changed(self, idx: int):
        device = self.device_combo.itemData(idx)
        if device:
            self.device_changed.emit(device)

    def set_running_state(self, is_running: bool, status_text: str = ""):
        """Toggles controls and changes Start Queue button text and styling."""
        self.btn_start.setEnabled(not is_running)
        self.btn_abort_file.setEnabled(is_running)
        self.btn_abort_all.setEnabled(is_running)
        self.model_combo.setEnabled(not is_running)
        self.device_combo.setEnabled(not is_running)

        if is_running:
            label = status_text if status_text else "⏳ Processing Queue..."
            self.btn_start.setText(label)
            self.btn_start.setStyleSheet("""
                QPushButton {
                    background-color: #2D2115;
                    border: 1px solid #854817;
                    border-radius: 8px;
                    color: #FFAE66;
                    font-size: 13px;
                    font-weight: 700;
                    padding: 10px 18px;
                }
            """)
        else:
            self._apply_start_button_idle_style()

    def update_queue_progress(self, done: int, total: int, pct: float, status_msg: str = ""):
        self.queue_bar.setValue(int(pct))
        self.prog_detail_label.setText(f"{done:,} / {total:,} lines ({pct:.1f}%)")
        if status_msg:
            self.status_caption.setText(f"Queue Status: {status_msg}")
