"""
Main application window for Translator.
Assembles the modular cards, header, and control bars in a frameless high-performance split layout.
"""
from typing import Optional
import os
import json
import logging

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QMessageBox,
    QFrame,
)
from PyQt6.QtCore import Qt

from anti_gravity.config import (
    APP_NAME,
    APP_SUBTITLE,
    DEFAULT_MODEL_ID,
    DEFAULT_BATCH_SIZE,
    DEFAULT_MAX_NEW_TOKENS,
    DEFAULT_TEMPERATURE,
    SYSTEM_INSTRUCTION,
)
from anti_gravity.styles import APPLICATION_STYLESHEET
from anti_gravity.system_monitor import SystemMonitor, SystemMetrics, get_gpu_display_name
from anti_gravity.translator_engine import TranslationEngine
from anti_gravity.worker import TranslationWorker
from anti_gravity.ui.header_bar import HeaderBar
from anti_gravity.ui.file_queue_widget import FileQueueWidget
from anti_gravity.ui.resource_monitor_widget import ResourceMonitorWidget
from anti_gravity.ui.live_preview_widget import LivePreviewWidget
from anti_gravity.ui.bottom_bar import BottomBar
from anti_gravity.ui.settings_dialog import SettingsDialog
from anti_gravity.ui.installer_wizard import InstallerWizardDialog


from anti_gravity.spoken_converter import score_translation_quality

logger = logging.getLogger("anti_gravity.main_window")

SETTINGS_FILE = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "SinhalaSubtitleTranslator",
    "settings.json",
)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} - {APP_SUBTITLE}")
        self.resize(1300, 850)
        self.setMinimumSize(1000, 650)

        # Frameless window configuration
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowSystemMenuHint)

        # Settings state
        self.settings = {
            "model_id": DEFAULT_MODEL_ID,
            "device": "cuda",
            "batch_size": DEFAULT_BATCH_SIZE,
            "temperature": DEFAULT_TEMPERATURE,
            "max_new_tokens": DEFAULT_MAX_NEW_TOKENS,
            "use_sdpa": True,
            "use_compile": False,
            "system_prompt": SYSTEM_INSTRUCTION,
            "hf_token": os.environ.get("HF_TOKEN", ""),
        }

        # Initialize AI Engine & Monitor
        try:
            self.engine = TranslationEngine(
                model_id=self.settings["model_id"],
                device=self.settings["device"],
                hf_token=self.settings["hf_token"]
            )
        except Exception as e:
            logger.error(f"Failed to initialize TranslationEngine: {e}")
            self.engine = TranslationEngine(
                model_id=DEFAULT_MODEL_ID,
                device="cpu",
                hf_token=""
            )
        self.engine.batch_size = self.settings["batch_size"]
        self.engine.temperature = self.settings["temperature"]
        self.engine.max_new_tokens = self.settings["max_new_tokens"]
        self.engine.system_prompt = self.settings["system_prompt"]

        self.monitor = SystemMonitor(interval_ms=1000)
        self.worker: Optional[TranslationWorker] = None

        self._load_settings()
        self._init_ui()
        self._connect_signals()

        # Start hardware monitoring
        self.monitor.start()

    def _load_settings(self):
        """Load persisted settings from disk, merging with defaults."""
        if os.path.isfile(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                for key in self.settings:
                    if key in saved:
                        self.settings[key] = saved[key]
                logger.info(f"Loaded settings from {SETTINGS_FILE}")
            except Exception as e:
                logger.warning(f"Could not load settings: {e}")
        # Apply loaded settings to engine
        self.engine.model_id = self.settings["model_id"]
        self.engine.set_device(self.settings["device"])
        self.engine.batch_size = self.settings["batch_size"]
        self.engine.temperature = self.settings["temperature"]
        self.engine.max_new_tokens = self.settings["max_new_tokens"]
        self.engine.system_prompt = self.settings["system_prompt"]
        self.engine.hf_token = self.settings.get("hf_token", "")

    def _save_settings(self):
        """Persist current settings to disk."""
        try:
            os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
            logger.info(f"Settings saved to {SETTINGS_FILE}")
        except Exception as e:
            logger.warning(f"Could not save settings: {e}")

    def _init_ui(self):
        self.setStyleSheet(APPLICATION_STYLESHEET)

        # Main Frameless Outer Container
        self.outer_frame = QFrame()
        self.outer_frame.setObjectName("mainFrame")
        self.setCentralWidget(self.outer_frame)

        root_layout = QVBoxLayout(self.outer_frame)
        root_layout.setContentsMargins(1, 1, 1, 1)
        root_layout.setSpacing(0)

        # 1. Header Bar with integrated window controls
        self.header_bar = HeaderBar()
        root_layout.addWidget(self.header_bar)

        # 2. Main Dashboard Split-Pane
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setHandleWidth(8)
        main_splitter.setStyleSheet("QSplitter::handle { background-color: #0E1015; }")

        # Left Modular Card: File Queue & Drag-and-Drop
        self.queue_widget = FileQueueWidget()
        main_splitter.addWidget(self.queue_widget)

        # Right Modular Container: Top (Resource Monitor) and Bottom (Preview Console)
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(8, 0, 16, 0)
        right_layout.setSpacing(12)

        self.resource_widget = ResourceMonitorWidget()
        right_layout.addWidget(self.resource_widget)

        self.preview_widget = LivePreviewWidget()
        right_layout.addWidget(self.preview_widget, 1)

        main_splitter.addWidget(right_container)

        # Set initial splitter proportions (55% Left, 45% Right)
        main_splitter.setSizes([680, 580])
        root_layout.addWidget(main_splitter, 1)

        # 3. Bottom Control Bar
        self.bottom_bar = BottomBar()
        root_layout.addWidget(self.bottom_bar)

    def _connect_signals(self):
        # Frameless Window Controls
        self.header_bar.minimize_requested.connect(self.showMinimized)
        self.header_bar.maximize_requested.connect(self._toggle_maximize)
        self.header_bar.close_requested.connect(self.close)

        # Hardware monitor updates
        self.monitor.metrics_updated.connect(self._on_metrics_updated)

        # Header bar actions
        self.header_bar.open_settings_requested.connect(self.open_settings)
        self.header_bar.open_wizard_requested.connect(self.open_wizard)

        # Bottom bar actions
        self.bottom_bar.start_queue_requested.connect(self.start_queue)
        self.bottom_bar.abort_current_requested.connect(self.abort_current_file)
        self.bottom_bar.abort_queue_requested.connect(self.abort_entire_queue)
        self.bottom_bar.output_dir_changed.connect(self.queue_widget.set_custom_output_dir)
        self.bottom_bar.model_changed.connect(self.change_model)
        self.bottom_bar.device_changed.connect(self.change_device)

    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
            self.header_bar.update_max_restore_button(False)
        else:
            self.showMaximized()
            self.header_bar.update_max_restore_button(True)

    def _on_metrics_updated(self, metrics: SystemMetrics):
        self.resource_widget.update_metrics(metrics)
        summary = self.monitor.get_hardware_summary()
        self.header_bar.set_hardware_info(summary, is_gpu=metrics.gpu_available)

    def open_settings(self):
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "Settings Locked", "Settings cannot be modified while translation is in progress.")
            return
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec():
            self.settings = dialog.get_settings()
            new_model = self.settings["model_id"]
            if new_model != self.engine.model_id:
                self.change_model(new_model)
            self.engine.batch_size = self.settings["batch_size"]
            self.engine.temperature = self.settings["temperature"]
            self.engine.max_new_tokens = self.settings["max_new_tokens"]
            self.engine.system_prompt = self.settings["system_prompt"]
            self.engine.hf_token = self.settings.get("hf_token", "")
            self._save_settings()
            self.preview_widget.append_info_message("Applied updated settings.")

    def open_wizard(self):
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "Setup Wizard Locked", "Setup wizard cannot be opened while translation is in progress.")
            return
        wizard = InstallerWizardDialog(
            target_model_id=self.settings["model_id"],
            hf_token=self.settings.get("hf_token", ""),
            parent=self
        )
        wizard.exec()

    def change_device(self, device: str):
        is_compat, compat_msg = self.engine.check_device_compatibility(self.settings["model_id"], device)
        if not is_compat:
            QMessageBox.warning(self, "Compute Device Incompatibility", compat_msg)
            # Revert device combo to previous working setting
            prev_idx = self.bottom_bar.device_combo.findData(self.settings["device"])
            if prev_idx >= 0:
                self.bottom_bar.device_combo.blockSignals(True)
                self.bottom_bar.device_combo.setCurrentIndex(prev_idx)
                self.bottom_bar.device_combo.blockSignals(False)
            return

        self.settings["device"] = device
        self.engine.set_device(device)
        self.preview_widget.append_info_message(
            f"Compute device set to: {'⚡ GPU (' + get_gpu_display_name() + ')' if device == 'cuda' else '🖥 CPU (System)'}"
        )
        if self.engine.is_loaded:
            self.engine.unload_model()

    def change_model(self, model_id: str):
        if model_id == self.engine.model_id and self.engine.is_loaded:
            return

        # Check compatibility with current device
        is_compat, compat_msg = self.engine.check_device_compatibility(model_id, self.settings["device"])
        if not is_compat:
            QMessageBox.warning(self, "Compute Device Incompatibility", compat_msg)
            # Automatically switch device back to GPU if available
            if self.settings["device"] == "cpu":
                self.settings["device"] = "cuda"
                self.engine.set_device("cuda")
                idx = self.bottom_bar.device_combo.findData("cuda")
                if idx >= 0:
                    self.bottom_bar.device_combo.blockSignals(True)
                    self.bottom_bar.device_combo.setCurrentIndex(idx)
                    self.bottom_bar.device_combo.blockSignals(False)
                self.preview_widget.append_info_message("Switched compute device to GPU to support 4-bit quantization.")

        self.settings["model_id"] = model_id
        self.preview_widget.append_info_message(f"AI Model switched to: {model_id}. Releasing previous VRAM cache...")
        self.engine.unload_model()
        self.engine.model_id = model_id

    def start_queue(self):
        # Validation 1: Files in queue
        if not self.queue_widget.queue_items:
            QMessageBox.information(
                self,
                "Queue Empty",
                "Please add at least one English .srt subtitle file to the queue."
            )
            return

        # Validation 2: Device compatibility
        is_compat, compat_msg = self.engine.check_device_compatibility(self.settings["model_id"], self.settings["device"])
        if not is_compat:
            QMessageBox.warning(self, "Compute Device Incompatibility", compat_msg)
            return

        # Validation 3: Pre-flight dependency check
        wizard = InstallerWizardDialog(
            target_model_id=self.settings["model_id"],
            hf_token=self.settings.get("hf_token", ""),
            auto_check=False,
            parent=self
        )
        if not wizard.run_checks():
            wizard.exec()
            if not wizard.run_checks():
                QMessageBox.warning(
                    self,
                    "Missing Dependencies",
                    "Please install the required dependencies before running translation."
                )
                return

        # Reset item states that are not completed
        for idx, item in enumerate(self.queue_widget.queue_items):
            if item.status != "Completed":
                item.status = "Queued"
                self.queue_widget.update_file_status(idx, "Queued")

        # Immediately update button label and state
        self.bottom_bar.set_running_state(True, "⏳ Loading Model...")
        self.header_bar.set_running_state(True)
        self.preview_widget.append_info_message("Starting queue processing...")

        # Spawn Worker
        self.worker = TranslationWorker(
            queue_items=self.queue_widget.queue_items,
            engine=self.engine,
            batch_size=self.settings["batch_size"],
            parent=self
        )

        self.worker.model_loading_progress.connect(
            lambda msg, pct: self.bottom_bar.set_running_state(True, f"⏳ {pct}% Loading...")
        )
        self.worker.file_status_changed.connect(self.queue_widget.update_file_status)
        self.worker.file_progress.connect(self.queue_widget.update_file_progress)
        self.worker.queue_progress.connect(self._on_queue_progress)
        self.worker.line_translated.connect(self._on_line_translated)
        self.worker.log_message.connect(self.preview_widget.append_info_message)
        self.worker.queue_finished.connect(self._on_queue_finished)

        self.worker.start()

    def _on_line_translated(self, file_name: str, line_no: int, en_text: str, si_text: str):
        self.bottom_bar.set_running_state(True, "⏳ Translating Queue...")
        score, issues = score_translation_quality(en_text, si_text)
        self.preview_widget.append_translation_pair(file_name, line_no, en_text, si_text, score=score, issues=issues)

    def _on_queue_progress(self, done: int, total: int, pct: float):
        self.bottom_bar.update_queue_progress(done, total, pct, f"Processing {done}/{total} lines")

    def _on_queue_finished(self, success: bool, msg: str):
        # Reset button text and state
        self.bottom_bar.set_running_state(False)
        self.header_bar.set_running_state(False)
        self.bottom_bar.update_queue_progress(
            sum(i.completed_lines for i in self.queue_widget.queue_items),
            sum(i.total_lines for i in self.queue_widget.queue_items),
            100.0 if success else self.bottom_bar.queue_bar.value(),
            "Finished" if success else "Stopped"
        )
        if success:
            QMessageBox.information(self, "Completed", "All subtitle files translated successfully!")
        else:
            self.preview_widget.append_info_message(f"Queue ended: {msg}")

    def abort_current_file(self):
        if self.worker and self.worker.isRunning():
            self.worker.abort_current()

    def abort_entire_queue(self):
        if self.worker and self.worker.isRunning():
            self.worker.abort_all()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Translation in Progress",
                "A translation task is currently running. Do you want to abort and exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.worker.abort_all()
                self.worker.wait(3000)
            else:
                event.ignore()
                return

        self.monitor.stop()
        self.engine.unload_model()
        event.accept()
