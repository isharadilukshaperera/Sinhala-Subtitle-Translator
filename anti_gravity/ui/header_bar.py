"""
Header bar widget for Translator.
Displays brand identity, active hardware status badge, settings toggle,
and custom frameless window control buttons (Minimize, Maximize, Close).
"""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt6.QtCore import pyqtSignal, Qt, QPoint
from PyQt6.QtGui import QMouseEvent

from anti_gravity.config import (
    APP_NAME,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_ACCENT,
    COLOR_SUCCESS,
)


class HeaderBar(QWidget):
    open_settings_requested = pyqtSignal()
    open_wizard_requested = pyqtSignal()
    minimize_requested = pyqtSignal()
    maximize_requested = pyqtSignal()
    close_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("headerBar")
        self._drag_pos = QPoint()
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 10, 10, 10)
        layout.setSpacing(14)

        # Title and Subtitle Block
        title_block = QWidget()
        tb_layout = QHBoxLayout(title_block)
        tb_layout.setContentsMargins(0, 0, 0, 0)
        tb_layout.setSpacing(10)

        # Accent icon
        icon_label = QLabel("🎬")
        icon_label.setStyleSheet("font-size: 22px;")
        tb_layout.addWidget(icon_label)

        text_container = QWidget()
        tc_layout = QHBoxLayout(text_container)
        tc_layout.setContentsMargins(0, 0, 0, 0)
        tc_layout.setSpacing(8)

        self.app_title = QLabel(APP_NAME)
        self.app_title.setStyleSheet(f"""
            font-size: 19px;
            font-weight: 800;
            color: {COLOR_TEXT_PRIMARY};
            letter-spacing: 0.5px;
        """)
        tc_layout.addWidget(self.app_title)

        badge_sub = QLabel("SINHALA AI")
        badge_sub.setStyleSheet(f"""
            background-color: rgba(255, 107, 0, 0.15);
            color: {COLOR_ACCENT};
            border: 1px solid rgba(255, 107, 0, 0.4);
            border-radius: 6px;
            padding: 2px 6px;
            font-size: 10px;
            font-weight: 700;
        """)
        tc_layout.addWidget(badge_sub)
        tb_layout.addWidget(text_container)

        layout.addWidget(title_block)
        layout.addStretch()

        # Hardware Status Badge
        self.hw_badge = QFrame()
        self.hw_badge.setProperty("class", "hardware-badge")
        hw_layout = QHBoxLayout(self.hw_badge)
        hw_layout.setContentsMargins(12, 5, 12, 5)
        hw_layout.setSpacing(8)

        self.hw_indicator = QLabel("●")
        self.hw_indicator.setStyleSheet(f"color: {COLOR_SUCCESS}; font-size: 13px;")
        hw_layout.addWidget(self.hw_indicator)

        self.hw_label = QLabel("Detecting Hardware...")
        self.hw_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 12px; font-weight: 600;")
        hw_layout.addWidget(self.hw_label)

        layout.addWidget(self.hw_badge)

        # Dependency Wizard / Health Button
        self.btn_wizard = QPushButton("🛠 Setup & Health")
        self.btn_wizard.setStyleSheet("""
            background-color: #171B24;
            border: 1px solid #2B3342;
            border-radius: 8px;
            padding: 5px 12px;
            font-size: 12px;
        """)
        self.btn_wizard.clicked.connect(self.open_wizard_requested.emit)
        layout.addWidget(self.btn_wizard)

        # Settings Button
        self.btn_settings = QPushButton("⚙ Settings")
        self.btn_settings.setStyleSheet("""
            background-color: #171B24;
            border: 1px solid #2B3342;
            border-radius: 8px;
            padding: 5px 12px;
            font-size: 12px;
        """)
        self.btn_settings.clicked.connect(self.open_settings_requested.emit)
        layout.addWidget(self.btn_settings)

        # Separator line before window controls
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setStyleSheet("color: #262D3D; max-height: 18px; margin: 0 4px;")
        layout.addWidget(sep)

        # Custom Frameless Window Controls (Minimize, Maximize/Restore, Close)
        win_ctrls = QWidget()
        wc_layout = QHBoxLayout(win_ctrls)
        wc_layout.setContentsMargins(0, 0, 0, 0)
        wc_layout.setSpacing(4)

        self.btn_min = QPushButton("—")
        self.btn_min.setProperty("class", "btn-win-ctrl")
        self.btn_min.setToolTip("Minimize")
        self.btn_min.clicked.connect(self.minimize_requested.emit)
        wc_layout.addWidget(self.btn_min)

        self.btn_max = QPushButton("□")
        self.btn_max.setProperty("class", "btn-win-ctrl")
        self.btn_max.setToolTip("Maximize / Restore")
        self.btn_max.clicked.connect(self.maximize_requested.emit)
        wc_layout.addWidget(self.btn_max)

        self.btn_close = QPushButton("✕")
        self.btn_close.setProperty("class", "btn-win-ctrl btn-win-close")
        self.btn_close.setToolTip("Close")
        self.btn_close.clicked.connect(self.close_requested.emit)
        wc_layout.addWidget(self.btn_close)

        layout.addWidget(win_ctrls)

    def set_hardware_info(self, text: str, is_gpu: bool = True):
        self.hw_label.setText(text)
        color = COLOR_SUCCESS if is_gpu else "#F59E0B"
        self.hw_indicator.setStyleSheet(f"color: {color}; font-size: 13px;")

    def set_running_state(self, is_running: bool):
        """Disable settings and health wizard buttons while translating."""
        self.btn_settings.setEnabled(not is_running)
        self.btn_wizard.setEnabled(not is_running)

    def update_max_restore_button(self, is_maximized: bool):
        self.btn_max.setText("❐" if is_maximized else "□")

    # Draggable Frameless Header Support
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            win = self.window()
            if win:
                self._drag_pos = event.globalPosition().toPoint() - win.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton and not self._drag_pos.isNull():
            win = self.window()
            if win and not win.isMaximized():
                win.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.maximize_requested.emit()
        super().mouseDoubleClickEvent(event)
