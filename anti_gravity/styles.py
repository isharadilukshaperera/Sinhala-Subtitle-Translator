"""
Custom QSS Stylesheet and Theme Utilities for Translator.
Aesthetic: Obsidian Slate, Glowing Neon Amber Accents, Modular Rounded Cards, Frameless Window.
"""
from anti_gravity.config import (
    COLOR_BG_DARK,
    COLOR_CARD_BG,
    COLOR_CARD_BORDER,
    COLOR_CARD_HOVER,
    COLOR_ACCENT,
    COLOR_ACCENT_HOVER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
    COLOR_SUCCESS,
    COLOR_DANGER,
    COLOR_WARNING,
    COLOR_INFO,
)

APPLICATION_STYLESHEET = f"""
/* Global Reset and Main Window */
QWidget {{
    font-family: "Segoe UI", "Inter", -apple-system, BlinkMacSystemFont, "Roboto", sans-serif;
    color: {COLOR_TEXT_PRIMARY};
    font-size: 13px;
}}

QMainWindow, QDialog {{
    background-color: {COLOR_BG_DARK};
}}

/* Frameless Window Outer Frame */
#mainFrame {{
    background-color: {COLOR_BG_DARK};
    border: 1px solid #1E2330;
}}

/* Window Control Buttons (Minimize, Maximize, Close) */
QPushButton.btn-win-ctrl {{
    background-color: transparent;
    border: none;
    border-radius: 6px;
    color: {COLOR_TEXT_SECONDARY};
    font-size: 13px;
    font-weight: 700;
    min-width: 32px;
    max-width: 32px;
    min-height: 28px;
    max-height: 28px;
    padding: 0;
}}

QPushButton.btn-win-ctrl:hover {{
    background-color: #212635;
    color: #FFFFFF;
}}

QPushButton.btn-win-close:hover {{
    background-color: #DC2626;
    color: #FFFFFF;
}}

/* Card Container Styles */
QFrame.dashboard-card {{
    background-color: {COLOR_CARD_BG};
    border: 1px solid {COLOR_CARD_BORDER};
    border-radius: 16px;
    padding: 14px;
}}

QFrame.dashboard-card:hover {{
    border: 1px solid #333A48;
}}

/* Section Titles */
QLabel.card-title {{
    color: {COLOR_TEXT_PRIMARY};
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.5px;
}}

QLabel.card-subtitle {{
    color: {COLOR_TEXT_SECONDARY};
    font-size: 12px;
}}

/* Buttons */
QPushButton {{
    background-color: #1F2430;
    border: 1px solid #2F3646;
    border-radius: 8px;
    color: {COLOR_TEXT_PRIMARY};
    padding: 8px 16px;
    font-weight: 600;
    font-size: 13px;
    min-height: 20px;
}}

QPushButton:hover {{
    background-color: #282F3F;
    border: 1px solid #454E63;
}}

QPushButton:pressed {{
    background-color: #171B24;
}}

QPushButton:disabled {{
    background-color: #141720;
    border: 1px solid #1E222D;
    color: #4B5563;
}}

/* Primary Accent Button (Neon Amber) */
QPushButton.btn-primary {{
    background-color: {COLOR_ACCENT};
    border: 1px solid {COLOR_ACCENT};
    color: #0E1015;
    font-weight: 700;
}}

QPushButton.btn-primary:hover {{
    background-color: {COLOR_ACCENT_HOVER};
    border: 1px solid {COLOR_ACCENT_HOVER};
}}

QPushButton.btn-primary:pressed {{
    background-color: #E05E00;
}}

QPushButton.btn-primary:disabled {{
    background-color: #472611;
    border: 1px solid #472611;
    color: #8C6A53;
}}

/* Danger Button (Abort) */
QPushButton.btn-danger {{
    background-color: rgba(239, 68, 68, 0.15);
    border: 1px solid rgba(239, 68, 68, 0.4);
    color: #F87171;
    font-weight: 600;
}}

QPushButton.btn-danger:hover {{
    background-color: rgba(239, 68, 68, 0.3);
    border: 1px solid #EF4444;
    color: #FFFFFF;
}}

QPushButton.btn-danger:pressed {{
    background-color: rgba(239, 68, 68, 0.45);
}}

QPushButton.btn-danger:disabled {{
    background-color: #1A1D26;
    border: 1px solid #252A37;
    color: #4B5563;
}}

/* Small Action Icon Buttons */
QPushButton.btn-action-sm {{
    background-color: #1B202A;
    border: 1px solid #2B3342;
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 11px;
    min-height: 22px;
}}

QPushButton.btn-action-sm:hover {{
    background-color: #272E3D;
    border: 1px solid {COLOR_ACCENT};
    color: {COLOR_ACCENT};
}}

/* Progress Bars */
QProgressBar {{
    background-color: #12151C;
    border: 1px solid #232834;
    border-radius: 6px;
    text-align: center;
    color: {COLOR_TEXT_PRIMARY};
    font-size: 11px;
    font-weight: 600;
    min-height: 12px;
}}

QProgressBar::chunk {{
    background-color: {COLOR_ACCENT};
    border-radius: 5px;
}}

/* Table Widget */
QTableWidget {{
    background-color: #12151D;
    border: 1px solid #212633;
    border-radius: 10px;
    gridline-color: #1E232F;
    selection-background-color: rgba(255, 107, 0, 0.15);
    selection-color: #FFFFFF;
    outline: none;
}}

QTableWidget::item {{
    padding: 4px 8px;
    border-bottom: 1px solid #1A1F2B;
}}

QTableWidget::item:selected {{
    background-color: rgba(255, 107, 0, 0.15);
}}

QHeaderView::section {{
    background-color: #161A23;
    color: {COLOR_TEXT_SECONDARY};
    padding: 10px 10px;
    border: none;
    border-bottom: 2px solid #262D3D;
    font-weight: 600;
    font-size: 12px;
    text-align: left;
}}

/* Text Inputs and Dropdowns */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: #12151D;
    border: 1px solid #262D3D;
    border-radius: 8px;
    color: {COLOR_TEXT_PRIMARY};
    padding: 8px 12px;
    selection-background-color: {COLOR_ACCENT};
}}

QLineEdit:focus, QComboBox:focus {{
    border: 1px solid {COLOR_ACCENT};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border-left: 1px solid #262D3D;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {COLOR_TEXT_SECONDARY};
    width: 0;
    height: 0;
    margin-right: 6px;
}}

QComboBox QAbstractItemView {{
    background-color: #181C26;
    border: 1px solid #2F374A;
    border-radius: 8px;
    color: {COLOR_TEXT_PRIMARY};
    selection-background-color: {COLOR_ACCENT};
    selection-color: #0E1015;
    padding: 4px;
}}

/* Plain Text Edit / Console */
QPlainTextEdit, QTextEdit {{
    background-color: #0B0D12;
    border: 1px solid #202532;
    border-radius: 10px;
    color: #E2E8F0;
    font-family: "Consolas", "Cascadia Code", "Fira Code", monospace;
    font-size: 12px;
    padding: 10px;
}}

/* Scrollbars */
QScrollBar:vertical {{
    background: #0E1015;
    width: 8px;
    margin: 0;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background: #2A303F;
    border-radius: 4px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLOR_ACCENT};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background: #0E1015;
    height: 8px;
    margin: 0;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal {{
    background: #2A303F;
    border-radius: 4px;
    min-width: 20px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {COLOR_ACCENT};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Drop Area */
QFrame.drop-zone {{
    background-color: rgba(22, 25, 34, 0.7);
    border: 2px dashed #2E3647;
    border-radius: 14px;
}}

QFrame.drop-zone:hover, QFrame.drop-zone-active {{
    background-color: rgba(255, 107, 0, 0.05);
    border: 2px dashed {COLOR_ACCENT};
}}

/* Hardware Badges */
QFrame.hardware-badge {{
    background-color: #151822;
    border: 1px solid #262D3D;
    border-radius: 20px;
    padding: 4px 12px;
}}
"""

def get_status_badge_html(status: str) -> str:
    """Return styled HTML badge for table cell status with generous non-cropped padding."""
    status_lower = status.lower()
    if status_lower == "queued":
        return f'<span style="background-color: rgba(245, 158, 11, 0.15); color: {COLOR_WARNING}; padding: 5px 14px; border-radius: 12px; font-weight: 700; font-size: 11px; border: 1px solid rgba(245, 158, 11, 0.35); white-space: nowrap;">Queued</span>'
    elif status_lower in ("processing", "translating"):
        return f'<span style="background-color: rgba(255, 107, 0, 0.18); color: {COLOR_ACCENT}; padding: 5px 14px; border-radius: 12px; font-weight: 800; font-size: 11px; border: 1px solid {COLOR_ACCENT}; white-space: nowrap;">⚡ Processing</span>'
    elif status_lower == "completed":
        return f'<span style="background-color: rgba(16, 185, 129, 0.15); color: {COLOR_SUCCESS}; padding: 5px 14px; border-radius: 12px; font-weight: 700; font-size: 11px; border: 1px solid rgba(16, 185, 129, 0.35); white-space: nowrap;">✓ Completed</span>'
    elif status_lower == "aborted":
        return f'<span style="background-color: rgba(148, 163, 184, 0.15); color: {COLOR_TEXT_SECONDARY}; padding: 5px 14px; border-radius: 12px; font-weight: 700; font-size: 11px; border: 1px solid #334155; white-space: nowrap;">⊘ Aborted</span>'
    elif status_lower == "failed":
        return f'<span style="background-color: rgba(239, 68, 68, 0.15); color: {COLOR_DANGER}; padding: 5px 14px; border-radius: 12px; font-weight: 700; font-size: 11px; border: 1px solid rgba(239, 68, 68, 0.35); white-space: nowrap;">✕ Failed</span>'
    return f'<span style="color: {COLOR_TEXT_MUTED}; white-space: nowrap; font-weight: 600;">{status}</span>'
