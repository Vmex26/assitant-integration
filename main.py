"""
AI Assistant Integrer - Entry point.

A modular AI assistant application with support for multiple LLM providers,
tool execution (files, commands, web), and a rich PyQt6 GUI.

Usage:
    python main.py
"""

import os
import sys

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow


def main() -> None:
    """Initialize and run the application."""
    app = QApplication(sys.argv)
    app.setApplicationName("AI Assistant Integrer")
    app.setApplicationVersion("1.0.0")

    # Set default font
    font = QFont("sans-serif", 13)
    app.setFont(font)

    # Create and show main window
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
