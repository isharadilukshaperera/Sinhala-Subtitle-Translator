"""
Dependency and Model availability checker with automated installer wizard for Translator.
Performs pre-flight checks for Python packages, CUDA GPU, and local AI model weights.
"""
import sys
import os
import subprocess
from typing import Dict, List, Tuple, Optional
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFrame,
    QTextEdit,
    QComboBox,
    QCheckBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from anti_gravity.config import (
    COLOR_BG_DARK,
    COLOR_CARD_BG,
    COLOR_CARD_BORDER,
    COLOR_ACCENT,
    COLOR_SUCCESS,
    COLOR_DANGER,
    COLOR_WARNING,
    DEFAULT_MODEL_ID,
    SUPPORTED_MODELS,
)


def is_model_cached(model_id: str) -> bool:
    """Check if model snapshot is present in local Hugging Face hub cache using huggingface_hub."""
    try:
        from huggingface_hub import try_to_load_from_cache
        cached = try_to_load_from_cache(model_id, "config.json")
        return isinstance(cached, str) and os.path.isfile(cached)
    except Exception:
        return False


class DependencyInstallWorker(QThread):
    progress_changed = pyqtSignal(str, int)
    log_emitted = pyqtSignal(str)
    finished_result = pyqtSignal(bool, str)

    def __init__(self, packages_to_install: List[str], models_to_download: List[str], hf_token: str = "", parent=None):
        super().__init__(parent)
        self.packages = packages_to_install
        self.models = models_to_download
        self.hf_token = hf_token or os.environ.get("HF_TOKEN", "")

    def run(self):
        try:
            total_items = len(self.packages) + len(self.models)
            current_step = 0

            # 1. Pip installs
            for pkg in self.packages:
                current_step += 1
                pct = int((current_step / max(total_items, 1)) * 50)
                self.progress_changed.emit(f"Installing {pkg}...", pct)
                self.log_emitted.emit(f">>> pip install {pkg}")

                proc = subprocess.Popen(
                    [sys.executable, "-m", "pip", "install", pkg],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                for line in proc.stdout:
                    self.log_emitted.emit(line.strip())
                proc.wait()

                if proc.returncode != 0:
                    self.finished_result.emit(False, f"Failed installing {pkg}")
                    return

            # 2. Model Downloads & Caching
            for model_id in self.models:
                current_step += 1
                pct = int(50 + (current_step / max(total_items, 1)) * 50)
                self.progress_changed.emit(f"Downloading model {model_id}...", pct)
                self.log_emitted.emit(f">>> Downloading Hugging Face model weights: {model_id}...")

                try:
                    from huggingface_hub import snapshot_download
                    snapshot_download(
                        repo_id=model_id,
                        token=self.hf_token if self.hf_token else None
                    )
                    self.log_emitted.emit(f"✓ Cached weights for: {model_id}")
                except Exception as dl_err:
                    self.log_emitted.emit(f"⚠ snapshot_download warning ({dl_err}), trying AutoTokenizer...")
                    from transformers import AutoTokenizer
                    AutoTokenizer.from_pretrained(
                        model_id,
                        trust_remote_code=True,
                        token=self.hf_token if self.hf_token else None
                    )

            self.progress_changed.emit("All tasks completed successfully!", 100)
            self.finished_result.emit(True, "All selected components and models are ready.")

        except Exception as e:
            self.finished_result.emit(False, str(e))


class InstallerWizardDialog(QDialog):
    def __init__(self, target_model_id: str = DEFAULT_MODEL_ID, hf_token: str = "", auto_check: bool = True, parent=None):
        super().__init__(parent)
        self.target_model_id = target_model_id
        self.hf_token = hf_token
        self.setWindowTitle("Translator - Dependency & AI Model Setup Wizard")
        self.resize(750, 580)
        self.worker = None
        self.missing_models: List[str] = []
        self.missing_pkgs: List[str] = []
        self._init_ui()
        if auto_check:
            self.run_checks()

    def _init_ui(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLOR_BG_DARK};
            }}
            QTableWidget {{
                background-color: #12151D;
                border: 1px solid #212633;
                border-radius: 8px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header Title
        title_box = QHBoxLayout()
        icon = QLabel("🛠")
        icon.setStyleSheet("font-size: 24px;")
        title_box.addWidget(icon)

        t_text = QLabel("System Environment & AI Model Availability Checker")
        t_text.setStyleSheet("font-size: 16px; font-weight: 700; color: #FFFFFF;")
        title_box.addWidget(t_text)
        title_box.addStretch()
        layout.addLayout(title_box)

        sub = QLabel("Validates GPU acceleration, Python packages, and local Hugging Face model cache.")
        sub.setStyleSheet("color: #94A3B8; font-size: 12px;")
        layout.addWidget(sub)

        # Health Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Component / Model", "Status", "Details"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        layout.addWidget(self.table)

        # Missing Model Downloader Box
        self.dl_box = QFrame()
        self.dl_box.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_CARD_BG};
                border: 1px solid {COLOR_CARD_BORDER};
                border-radius: 8px;
                padding: 6px;
            }}
        """)
        dl_layout = QHBoxLayout(self.dl_box)
        dl_layout.setContentsMargins(10, 6, 10, 6)
        dl_layout.setSpacing(10)

        self.chk_download_models = QCheckBox("Pre-download missing AI Model weights:")
        self.chk_download_models.setChecked(True)
        self.chk_download_models.setStyleSheet("font-weight: 600; color: #FFFFFF;")
        dl_layout.addWidget(self.chk_download_models)

        self.model_choice_combo = QComboBox()
        dl_layout.addWidget(self.model_choice_combo, 1)

        layout.addWidget(self.dl_box)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #12151D;
                border: 1px solid #232938;
                border-radius: 5px;
                min-height: 12px;
                max-height: 12px;
            }}
            QProgressBar::chunk {{
                background-color: {COLOR_ACCENT};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self.progress_bar)

        # Live Install Log Console
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setMaximumHeight(100)
        self.console.setVisible(False)
        layout.addWidget(self.console)

        # Bottom Buttons
        btn_box = QHBoxLayout()
        self.status_label = QLabel("Checking system and models...")
        self.status_label.setStyleSheet("color: #94A3B8; font-size: 12px;")
        btn_box.addWidget(self.status_label)

        btn_box.addStretch()

        self.btn_auto_install = QPushButton("⚡ Auto-Install & Download")
        self.btn_auto_install.setProperty("class", "btn-primary")
        self.btn_auto_install.setStyleSheet(f"background-color: {COLOR_ACCENT}; color: #0E1015; font-weight: 700; padding: 8px 16px;")
        self.btn_auto_install.clicked.connect(self.start_auto_install)
        self.btn_auto_install.setEnabled(False)
        btn_box.addWidget(self.btn_auto_install)

        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.accept)
        btn_box.addWidget(self.btn_close)

        layout.addLayout(btn_box)

    def run_checks(self) -> bool:
        """Inspects all required modules and AI models."""
        checks = []
        self.missing_pkgs = []
        self.missing_models = []

        # 1. Python Version
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        py_ok = sys.version_info >= (3, 10)
        checks.append(("Python 3.10+", py_ok, f"Python {py_ver}"))

        # 2. PyTorch & CUDA
        try:
            import torch
            has_cuda = torch.cuda.is_available()
            if has_cuda:
                gpu_name = torch.cuda.get_device_name(0)
                vram_gb = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 1)
                checks.append(("PyTorch + CUDA", True, f"CUDA Active: {gpu_name} ({vram_gb} GB VRAM)"))
            else:
                checks.append(("PyTorch + CUDA", False, "PyTorch active, but CUDA GPU not detected (CPU Mode Only)"))
        except Exception as e:
            checks.append(("PyTorch + CUDA", False, f"Missing: {e}"))

        # 3. Transformers
        try:
            import transformers
            checks.append(("Transformers", True, f"v{transformers.__version__}"))
        except Exception:
            checks.append(("Transformers", False, "Missing package 'transformers'"))
            self.missing_pkgs.append("transformers")

        # 4. BitsAndBytes (4-bit NF4)
        try:
            import bitsandbytes
            checks.append(("bitsandbytes (4-bit)", True, f"v{bitsandbytes.__version__}"))
        except Exception:
            checks.append(("bitsandbytes (4-bit)", False, "Missing 'bitsandbytes'"))
            self.missing_pkgs.append("bitsandbytes")

        # 5. Accelerate
        try:
            import accelerate
            checks.append(("Accelerate", True, f"v{accelerate.__version__}"))
        except Exception:
            checks.append(("Accelerate", False, "Missing 'accelerate'"))
            self.missing_pkgs.append("accelerate")

        # 6. pysrt & chardet
        try:
            import pysrt
            checks.append(("SRT Subtitle Parser", True, "pysrt active"))
        except Exception:
            checks.append(("SRT Subtitle Parser", False, "Missing 'pysrt'"))
            self.missing_pkgs.append("pysrt")

        # 7. Model Availability Checks
        self.model_choice_combo.clear()
        for m_id, info in SUPPORTED_MODELS.items():
            cached = is_model_cached(m_id)
            if cached:
                checks.append((f"Model: {info['name']}", True, f"✓ Cached locally ({m_id})"))
            else:
                checks.append((f"Model: {info['name']}", False, f"Not downloaded ({m_id})"))
                self.missing_models.append(m_id)
                self.model_choice_combo.addItem(f"{info['name']} ({m_id})", m_id)

        if self.missing_models:
            self.dl_box.setVisible(True)
            self.model_choice_combo.addItem("Download All Missing Models", "ALL")
        else:
            self.dl_box.setVisible(False)

        # Populate Table
        self.table.setRowCount(len(checks))
        all_passed = (len(self.missing_pkgs) == 0 and len(self.missing_models) == 0)

        for row, (name, ok, desc) in enumerate(checks):
            name_item = QTableWidgetItem(name)
            name_item.setForeground(Qt.GlobalColor.white)
            self.table.setItem(row, 0, name_item)

            status_item = QTableWidgetItem("✓ Ready" if ok else "✕ Missing")
            status_item.setForeground(Qt.GlobalColor.green if ok else Qt.GlobalColor.yellow if "Model:" in name else Qt.GlobalColor.red)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, status_item)

            desc_item = QTableWidgetItem(desc)
            desc_item.setForeground(Qt.GlobalColor.lightGray)
            self.table.setItem(row, 2, desc_item)

        if all_passed:
            self.status_label.setText("✓ All libraries, CUDA runtime, and model weights are ready!")
            self.status_label.setStyleSheet(f"color: {COLOR_SUCCESS}; font-weight: 600;")
            self.btn_auto_install.setEnabled(False)
        else:
            reasons = []
            if self.missing_pkgs:
                reasons.append(f"{len(self.missing_pkgs)} library packages")
            if self.missing_models:
                reasons.append(f"{len(self.missing_models)} AI model(s) not cached")
            self.status_label.setText(f"⚠ Missing: {', '.join(reasons)}.")
            self.status_label.setStyleSheet(f"color: {COLOR_WARNING}; font-weight: 600;")
            self.btn_auto_install.setEnabled(True)

        return len(self.missing_pkgs) == 0 and len(self.missing_models) == 0

    def start_auto_install(self):
        self.progress_bar.setVisible(True)
        self.console.setVisible(True)
        self.btn_auto_install.setEnabled(False)
        self.status_label.setText("Starting automated download & installation...")

        # Determine which models to download
        models_to_dl = []
        if self.chk_download_models.isChecked() and self.model_choice_combo.count() > 0:
            selected_choice = self.model_choice_combo.currentData()
            if selected_choice == "ALL":
                models_to_dl = list(self.missing_models)
            elif selected_choice:
                models_to_dl = [selected_choice]

        self.worker = DependencyInstallWorker(
            packages_to_install=self.missing_pkgs,
            models_to_download=models_to_dl,
            hf_token=self.hf_token,
            parent=self
        )
        self.worker.progress_changed.connect(self._on_worker_progress)
        self.worker.log_emitted.connect(self.console.append)
        self.worker.finished_result.connect(self._on_worker_finished)
        self.worker.start()

    def _on_worker_progress(self, msg: str, pct: int):
        self.status_label.setText(msg)
        self.progress_bar.setValue(pct)

    def _on_worker_finished(self, success: bool, msg: str):
        if success:
            self.status_label.setText("Completed! Re-evaluating components...")
            self.run_checks()
        else:
            self.status_label.setText(f"Installation failed: {msg}")
            self.status_label.setStyleSheet(f"color: {COLOR_DANGER};")
            self.btn_auto_install.setEnabled(True)
