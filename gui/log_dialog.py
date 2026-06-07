"""
Log analyzer dialog - fetch and analyze system logs with AI.
"""

import subprocess

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QVBoxLayout,
)


class LogFetcher(QObject):
    """Background worker to run journalctl without blocking the GUI."""

    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, args: list[str]):
        super().__init__()
        self.args = args

    def run(self):
        try:
            result = subprocess.run(
                self.args,
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode != 0:
                self.error.emit(result.stderr.strip() or f"Exit code {result.returncode}")
            else:
                output = result.stdout.strip()
                if not output:
                    output = "(no log output)"
                self.finished.emit(output)
        except FileNotFoundError:
            self.error.emit("journalctl not found — is this a systemd-based system?")
        except subprocess.TimeoutExpired:
            self.error.emit("Timed out fetching logs")
        except Exception as e:
            self.error.emit(str(e))


class LogDialog(QDialog):
    """Dialog to select log type, fetch output, and send to chat."""

    log_ready = pyqtSignal(str, str)  # content, context_description

    LOG_PRESETS = {
        "General (last hour)": ["journalctl", "--since", "-1h", "--no-pager", "-n", "200"],
        "General (last boot)": ["journalctl", "-b", "--no-pager", "-n", "200"],
        "Kernel messages": ["journalctl", "-k", "--no-pager", "-n", "200"],
        "System services": ["journalctl", "-u", "systemd", "--no-pager", "-n", "200"],
        "Errors & warnings": ["journalctl", "-p", "warning", "--no-pager", "-n", "200"],
        "Failed services": ["systemctl", "--failed"],
        "User log (current)": ["journalctl", "--user", "--since", "-1h", "--no-pager", "-n", "200"],
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Log Analyzer")
        self.resize(700, 500)
        self._fetched_content = ""
        self._current_preset = ""
        self._is_fetching = False
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Preset selector
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Log type:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(self.LOG_PRESETS.keys())
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        preset_layout.addWidget(self.preset_combo, 1)
        layout.addLayout(preset_layout)

        # Custom flags input
        custom_layout = QHBoxLayout()
        custom_layout.addWidget(QLabel("Custom flags:"))
        self.custom_input = QPlainTextEdit()
        self.custom_input.setPlaceholderText("e.g. --since -2h -u sshd --no-pager")
        self.custom_input.setFixedHeight(50)
        custom_layout.addWidget(self.custom_input, 1)
        layout.addLayout(custom_layout)

        # Fetch button
        self.fetch_btn = QPushButton("Fetch logs")
        self.fetch_btn.clicked.connect(self._fetch_logs)
        layout.addWidget(self.fetch_btn)

        # Output preview
        self.output_view = QPlainTextEdit()
        self.output_view.setReadOnly(True)
        self.output_view.setPlaceholderText("Log output will appear here...")
        self.output_view.setStyleSheet("font-family: monospace; font-size: 11px;")
        layout.addWidget(self.output_view, 1)

        # Buttons
        btn_layout = QHBoxLayout()
        self.analyze_btn = QPushButton("Send to AI for analysis")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self._send_to_chat)
        self.analyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #4fc3f7;
                border: none; border-radius: 6px; padding: 8px 16px;
                color: #000; font-weight: bold;
            }
            QPushButton:disabled { background-color: #444; color: #666; }
            QPushButton:hover:!disabled { background-color: #29b6f6; }
        """)
        btn_layout.addWidget(self.analyze_btn, 1)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _on_preset_changed(self, preset: str):
        self.custom_input.setPlainText("")
        self.output_view.clear()
        self.analyze_btn.setEnabled(False)

    def _fetch_logs(self):
        if self._is_fetching:
            return
        self._is_fetching = True

        preset = self.preset_combo.currentText()
        custom = self.custom_input.toPlainText().strip()

        if custom:
            args = ["journalctl", *custom.split()]
        else:
            args = self.LOG_PRESETS.get(preset, ["journalctl", "--no-pager", "-n", "200"])

        self.fetch_btn.setEnabled(False)
        self.fetch_btn.setText("Fetching...")
        self.output_view.setPlainText("Fetching logs...")
        self._current_preset = preset if not custom else f"Custom: journalctl {custom}"

        thread = QThread(self)
        worker = LogFetcher(args)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_fetched)
        worker.error.connect(self._on_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(lambda: self._cleanup_fetch(thread, worker))
        thread.start()

    def _on_fetched(self, content: str):
        self._fetched_content = content
        self.output_view.setPlainText(content)
        self.analyze_btn.setEnabled(bool(content.strip()) and content != "(no log output)")
        self.fetch_btn.setEnabled(True)
        self.fetch_btn.setText("Fetch logs")

    def _on_error(self, msg: str):
        self.output_view.setPlainText(f"Error: {msg}")
        self.analyze_btn.setEnabled(False)
        self.fetch_btn.setEnabled(True)
        self.fetch_btn.setText("Fetch logs")

    def _cleanup_fetch(self, thread: QThread, worker: QObject):
        thread.deleteLater()
        worker.deleteLater()
        self._is_fetching = False

    def _send_to_chat(self):
        if self._fetched_content:
            desc = self._current_preset or self.preset_combo.currentText()
            self.log_ready.emit(self._fetched_content, desc)
            self.close()
