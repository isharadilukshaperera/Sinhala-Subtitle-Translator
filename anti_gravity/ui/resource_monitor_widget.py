"""
Resource monitor widget for Anti Gravity.
Displays real-time CPU, RAM, GPU VRAM allocation, and GPU utilization metrics.
"""
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QFrame,
    QGridLayout,
)
from PyQt6.QtCore import Qt

from anti_gravity.config import (
    COLOR_ACCENT,
    COLOR_CARD_BG,
    COLOR_CARD_BORDER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
    COLOR_SUCCESS,
)
from anti_gravity.system_monitor import SystemMetrics, get_gpu_display_name


class ResourceMonitorWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "dashboard-card")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel(f"Hardware Monitor ({get_gpu_display_name()})")
        title.setProperty("class", "card-title")
        header_layout.addWidget(title)

        header_layout.addStretch()

        self.temp_badge = QLabel("-- °C")
        self.temp_badge.setStyleSheet(f"""
            background-color: #1A1F2B;
            border: 1px solid #283042;
            border-radius: 6px;
            color: {COLOR_TEXT_SECONDARY};
            font-size: 11px;
            font-weight: 600;
            padding: 2px 8px;
        """)
        header_layout.addWidget(self.temp_badge)
        layout.addLayout(header_layout)

        # Metrics Grid
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)

        # 1. GPU VRAM (Primary Metric)
        vram_title_box = QHBoxLayout()
        vram_label = QLabel("GPU VRAM Allocation")
        vram_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-weight: 600; font-size: 12px;")
        self.vram_val = QLabel("0 MB / 12288 MB (0%)")
        self.vram_val.setStyleSheet(f"color: {COLOR_ACCENT}; font-weight: 700; font-size: 12px;")
        vram_title_box.addWidget(vram_label)
        vram_title_box.addStretch()
        vram_title_box.addWidget(self.vram_val)

        self.vram_bar = QProgressBar()
        self.vram_bar.setRange(0, 100)
        self.vram_bar.setValue(0)
        self.vram_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #12151D;
                border: 1px solid #232938;
                border-radius: 5px;
                min-height: 10px;
                max-height: 10px;
            }}
            QProgressBar::chunk {{
                background-color: {COLOR_ACCENT};
                border-radius: 4px;
            }}
        """)

        # 2. GPU Core Utilization
        gpu_title_box = QHBoxLayout()
        gpu_label = QLabel("GPU Core Compute")
        gpu_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-weight: 600; font-size: 12px;")
        self.gpu_val = QLabel("0%")
        self.gpu_val.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-weight: 700; font-size: 12px;")
        gpu_title_box.addWidget(gpu_label)
        gpu_title_box.addStretch()
        gpu_title_box.addWidget(self.gpu_val)

        self.gpu_bar = QProgressBar()
        self.gpu_bar.setRange(0, 100)
        self.gpu_bar.setValue(0)
        self.gpu_bar.setStyleSheet("""
            QProgressBar {
                background-color: #12151D;
                border: 1px solid #232938;
                border-radius: 5px;
                min-height: 10px;
                max-height: 10px;
            }
            QProgressBar::chunk {
                background-color: #38BDF8;
                border-radius: 4px;
            }
        """)

        # 3. CPU Usage
        cpu_title_box = QHBoxLayout()
        cpu_label = QLabel("CPU Load")
        cpu_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-weight: 600; font-size: 12px;")
        self.cpu_val = QLabel("0%")
        self.cpu_val.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-weight: 700; font-size: 12px;")
        cpu_title_box.addWidget(cpu_label)
        cpu_title_box.addStretch()
        cpu_title_box.addWidget(self.cpu_val)

        self.cpu_bar = QProgressBar()
        self.cpu_bar.setRange(0, 100)
        self.cpu_bar.setValue(0)
        self.cpu_bar.setStyleSheet("""
            QProgressBar {
                background-color: #12151D;
                border: 1px solid #232938;
                border-radius: 5px;
                min-height: 10px;
                max-height: 10px;
            }
            QProgressBar::chunk {
                background-color: #10B981;
                border-radius: 4px;
            }
        """)

        # 4. System RAM
        ram_title_box = QHBoxLayout()
        ram_label = QLabel("System RAM")
        ram_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-weight: 600; font-size: 12px;")
        self.ram_val = QLabel("0 GB / 0 GB (0%)")
        self.ram_val.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-weight: 700; font-size: 12px;")
        ram_title_box.addWidget(ram_label)
        ram_title_box.addStretch()
        ram_title_box.addWidget(self.ram_val)

        self.ram_bar = QProgressBar()
        self.ram_bar.setRange(0, 100)
        self.ram_bar.setValue(0)
        self.ram_bar.setStyleSheet("""
            QProgressBar {
                background-color: #12151D;
                border: 1px solid #232938;
                border-radius: 5px;
                min-height: 10px;
                max-height: 10px;
            }
            QProgressBar::chunk {
                background-color: #8B5CF6;
                border-radius: 4px;
            }
        """)

        # Add to Grid (2 columns)
        grid.addLayout(vram_title_box, 0, 0)
        grid.addWidget(self.vram_bar, 1, 0)

        grid.addLayout(gpu_title_box, 0, 1)
        grid.addWidget(self.gpu_bar, 1, 1)

        grid.addLayout(cpu_title_box, 2, 0)
        grid.addWidget(self.cpu_bar, 3, 0)

        grid.addLayout(ram_title_box, 2, 1)
        grid.addWidget(self.ram_bar, 3, 1)

        layout.addLayout(grid)

    def update_metrics(self, m: SystemMetrics):
        # VRAM
        self.vram_val.setText(f"{m.vram_used_mb} MB / {m.vram_total_mb} MB ({m.vram_percent}%)")
        self.vram_bar.setValue(int(m.vram_percent))

        # GPU Compute
        self.gpu_val.setText(f"{int(m.gpu_util_percent)}%")
        self.gpu_bar.setValue(int(m.gpu_util_percent))

        # Temperature
        if m.gpu_temp_c > 0:
            self.temp_badge.setText(f"GPU: {m.gpu_temp_c}°C")
            if m.gpu_temp_c > 75:
                self.temp_badge.setStyleSheet("background-color: #3B1B1B; border: 1px solid #EF4444; color: #F87171; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 6px;")
            else:
                self.temp_badge.setStyleSheet("background-color: #1A1F2B; border: 1px solid #283042; color: #94A3B8; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 6px;")
        else:
            self.temp_badge.setText(f"{get_gpu_display_name()} Active")

        # CPU
        self.cpu_val.setText(f"{int(m.cpu_percent)}%")
        self.cpu_bar.setValue(int(m.cpu_percent))

        # RAM
        self.ram_val.setText(f"{m.ram_used_gb} GB / {m.ram_total_gb} GB ({int(m.ram_percent)}%)")
        self.ram_bar.setValue(int(m.ram_percent))

