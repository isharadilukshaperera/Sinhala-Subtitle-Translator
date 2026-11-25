"""
Advanced settings modal dialog for Anti Gravity.
Allows configuring model selection, batch size, temperature, tokens, and system prompt.
"""
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QLineEdit,
    QPlainTextEdit,
    QGroupBox,
    QCheckBox,
    QTabWidget,
    QWidget,
    QMessageBox,
)
from PyQt6.QtCore import Qt

from anti_gravity.config import (
    SUPPORTED_MODELS,
    DEFAULT_MODEL_ID,
    DEFAULT_BATCH_SIZE,
    DEFAULT_MAX_NEW_TOKENS,
    DEFAULT_TEMPERATURE,
    SYSTEM_INSTRUCTION,
    COLOR_ACCENT,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_BG_DARK,
    COLOR_CARD_BG,
    COLOR_CARD_BORDER,
)
from anti_gravity.system_monitor import get_gpu_display_name


class SettingsDialog(QDialog):
    def __init__(self, current_settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Anti Gravity - Advanced Settings")
        self.resize(650, 580)
        self.settings = dict(current_settings)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLOR_BG_DARK};
            }}
            QGroupBox {{
                background-color: {COLOR_CARD_BG};
                border: 1px solid {COLOR_CARD_BORDER};
                border-radius: 10px;
                margin-top: 18px;
                padding: 14px;
                font-weight: 700;
                color: {COLOR_TEXT_PRIMARY};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                color: {COLOR_ACCENT};
            }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {COLOR_CARD_BORDER};
                border-radius: 8px;
                background-color: {COLOR_CARD_BG};
                padding: 10px;
            }}
            QTabBar::tab {{
                background-color: #12151D;
                color: {COLOR_TEXT_SECONDARY};
                padding: 8px 16px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
                font-weight: 600;
            }}
            QTabBar::tab:selected {{
                background-color: {COLOR_CARD_BG};
                color: {COLOR_ACCENT};
                border: 1px solid {COLOR_CARD_BORDER};
                border-bottom: none;
            }}
        """)

        # Tab 1: Inference & Hardware Settings
        tab_inference = QWidget()
        tab_inf_layout = QVBoxLayout(tab_inference)
        tab_inf_layout.setSpacing(14)

        # Model Selector
        grp_model = QGroupBox("Selected AI Model")
        m_layout = QVBoxLayout(grp_model)
        self.model_combo = QComboBox()
        for m_id, info in SUPPORTED_MODELS.items():
            self.model_combo.addItem(f"{info['name']} - {info['desc']}", m_id)

        current_mid = self.settings.get("model_id", DEFAULT_MODEL_ID)
        idx = self.model_combo.findData(current_mid)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        m_layout.addWidget(self.model_combo)

        lbl_token = QLabel("Hugging Face Access Token (Optional for gated/private models):")
        lbl_token.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px; margin-top: 6px;")
        m_layout.addWidget(lbl_token)
        self.token_edit = QLineEdit()
        self.token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_edit.setPlaceholderText("hf_... (leave blank for open models)")
        self.token_edit.setText(self.settings.get("hf_token", ""))
        m_layout.addWidget(self.token_edit)

        tab_inf_layout.addWidget(grp_model)

        # Hyperparameters
        grp_params = QGroupBox("Batching & Generation Hyperparameters")
        p_layout = QVBoxLayout(grp_params)
        p_layout.setSpacing(10)

        # Batch Size
        row_b = QHBoxLayout()
        lbl_b = QLabel("Vectorized Batch Size:")
        lbl_b.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        self.spin_batch = QSpinBox()
        self.spin_batch.setRange(1, 32)
        self.spin_batch.setValue(self.settings.get("batch_size", DEFAULT_BATCH_SIZE))
        row_b.addWidget(lbl_b)
        row_b.addStretch()
        row_b.addWidget(self.spin_batch)
        p_layout.addLayout(row_b)

        # Temperature
        row_t = QHBoxLayout()
        lbl_t = QLabel("Sampling Temperature (0.0 = Deterministic):")
        lbl_t.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        self.spin_temp = QDoubleSpinBox()
        self.spin_temp.setRange(0.0, 2.0)
        self.spin_temp.setSingleStep(0.05)
        self.spin_temp.setValue(self.settings.get("temperature", DEFAULT_TEMPERATURE))
        row_t.addWidget(lbl_t)
        row_t.addStretch()
        row_t.addWidget(self.spin_temp)
        p_layout.addLayout(row_t)

        # Max New Tokens
        row_tok = QHBoxLayout()
        lbl_tok = QLabel("Max Generation Tokens per Subtitle:")
        lbl_tok.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY};")
        self.spin_tokens = QSpinBox()
        self.spin_tokens.setRange(32, 1024)
        self.spin_tokens.setSingleStep(16)
        self.spin_tokens.setValue(self.settings.get("max_new_tokens", DEFAULT_MAX_NEW_TOKENS))
        row_tok.addWidget(lbl_tok)
        row_tok.addStretch()
        row_tok.addWidget(self.spin_tokens)
        p_layout.addLayout(row_tok)

        tab_inf_layout.addWidget(grp_params)

        # Hardware Optimizations
        grp_hw = QGroupBox(f"{get_gpu_display_name()} Optimizations")
        hw_layout = QVBoxLayout(grp_hw)
        self.chk_sdpa = QCheckBox("Enable Scaled Dot-Product Attention (SDPA) Acceleration")
        self.chk_sdpa.setChecked(self.settings.get("use_sdpa", True))
        hw_layout.addWidget(self.chk_sdpa)

        self.chk_compile = QCheckBox("Enable torch.compile (requires MSVC C++ runtime)")
        self.chk_compile.setChecked(self.settings.get("use_compile", False))
        hw_layout.addWidget(self.chk_compile)

        tab_inf_layout.addWidget(grp_hw)
        tab_inf_layout.addStretch()
        tabs.addTab(tab_inference, "Inference & GPU")

        # Tab 2: System Prompt & Translation Guidelines
        tab_prompt = QWidget()
        tab_p_layout = QVBoxLayout(tab_prompt)
        tab_p_layout.setSpacing(10)

        prompt_info = QLabel("Edit or inspect the Spoken Sinhala Subtitle system instruction:")
        prompt_info.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        tab_p_layout.addWidget(prompt_info)

        self.prompt_edit = QPlainTextEdit()
        self.prompt_edit.setPlainText(self.settings.get("system_prompt", SYSTEM_INSTRUCTION))
        self.prompt_edit.setStyleSheet("""
            QPlainTextEdit {
                font-family: 'Consolas', 'Segoe UI', monospace;
                font-size: 12px;
                line-height: 1.4;
            }
        """)
        tab_p_layout.addWidget(self.prompt_edit)

        btn_reset_prompt = QPushButton("↺ Reset to Spoken Sinhala Defaults")
        btn_reset_prompt.clicked.connect(self._reset_prompt)
        tab_p_layout.addWidget(btn_reset_prompt)

        tabs.addTab(tab_prompt, "System Prompt & Guidelines")

        main_layout.addWidget(tabs)

        # Bottom Dialog Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)

        btn_save = QPushButton("Save & Apply")
        btn_save.setProperty("class", "btn-primary")
        btn_save.setStyleSheet(f"background-color: {COLOR_ACCENT}; color: #0E1015; font-weight: 700;")
        btn_save.clicked.connect(self._save_and_close)
        btn_box.addWidget(btn_save)

        main_layout.addLayout(btn_box)

    def _reset_prompt(self):
        self.prompt_edit.setPlainText(SYSTEM_INSTRUCTION)

    def _save_and_close(self):
        # Validate: warn if system prompt is empty
        prompt_text = self.prompt_edit.toPlainText().strip()
        if not prompt_text:
            reply = QMessageBox.warning(
                self,
                "Empty System Prompt",
                "The system prompt is empty. This may significantly reduce translation quality.\n\n"
                "Do you want to reset it to the default, or continue with an empty prompt?",
                QMessageBox.StandardButton.Reset | QMessageBox.StandardButton.Ignore | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Reset,
            )
            if reply == QMessageBox.StandardButton.Reset:
                self.prompt_edit.setPlainText(SYSTEM_INSTRUCTION)
                return  # Stay in dialog so user can review the restored prompt
            elif reply == QMessageBox.StandardButton.Cancel:
                return  # Stay in dialog

        self.settings["model_id"] = self.model_combo.currentData()
        self.settings["hf_token"] = self.token_edit.text().strip()
        self.settings["batch_size"] = self.spin_batch.value()
        self.settings["temperature"] = self.spin_temp.value()
        self.settings["max_new_tokens"] = self.spin_tokens.value()
        self.settings["use_sdpa"] = self.chk_sdpa.isChecked()
        self.settings["use_compile"] = self.chk_compile.isChecked()
        self.settings["system_prompt"] = self.prompt_edit.toPlainText().strip()
        self.accept()

    def get_settings(self) -> dict:
        return self.settings

