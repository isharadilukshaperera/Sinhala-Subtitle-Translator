"""
Entry point for Anti Gravity Subtitle Translator.
Configures High-DPI scaling, application properties, and launches the main window.
"""
import sys
import os
import warnings
import logging
from logging.handlers import RotatingFileHandler

warnings.filterwarnings("ignore", category=FutureWarning)

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QFont

from anti_gravity.config import APP_NAME
from anti_gravity.ui.main_window import MainWindow


def main():
    # Configure logging: console (INFO) + rotating file (DEBUG)
    log_dir = os.path.join(
        os.environ.get("APPDATA", os.path.expanduser("~")),
        "SinhalaSubtitleTranslator",
    )
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Console handler — INFO and above
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(levelname)s | %(name)s | %(message)s"))
    root_logger.addHandler(console_handler)

    # File handler — DEBUG, rotating 5 MB × 3 backups
    try:
        file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
        root_logger.addHandler(file_handler)
    except Exception:
        pass  # Don't crash if log file can't be opened

    # Global exception handler to catch unhandled exceptions
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logging.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception

    # Enable High DPI scaling
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("AntiGravity")

    # Set default clean system font
    font = QFont("Segoe UI", 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
