"""
Systemd service viewer dialog.
"""

import subprocess
from typing import List, Optional

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class ServiceEntry:
    def __init__(self, name: str, state: str, status: str, description: str):
        self.name = name
        self.state = state
        self.status = status
        self.description = description


class ServiceLoader(QObject):
    """Background worker to list systemd services."""

    finished = pyqtSignal(list)  # list[ServiceEntry]
    error = pyqtSignal(str)

    def run(self):
        try:
            result = subprocess.run(
                ["systemctl", "list-units", "--type=service", "--all", "--no-pager"],
                capture_output=True, text=True, timeout=20,
            )
            if result.returncode != 0:
                self.error.emit(result.stderr.strip())
                return
            entries = []
            for line in result.stdout.split("\n"):
                if not line.strip() or ".service" not in line:
                    continue
                parts = line.split()
                if len(parts) < 4:
                    continue
                name = parts[0]
                state = parts[1]  # loaded
                status = parts[2]  # active/inactive
                desc = " ".join(parts[3:])
                entries.append(ServiceEntry(
                    name=name.replace(".service", ""),
                    state=state,
                    status=status,
                    description=desc,
                ))
            self.finished.emit(entries)
        except FileNotFoundError:
            self.error.emit("systemctl not found — is this a systemd-based system?")
        except subprocess.TimeoutExpired:
            self.error.emit("Timed out listing services")
        except Exception as e:
            self.error.emit(str(e))


class ServiceDialog(QDialog):
    """Dialog to view and manage systemd services."""

    service_explain = pyqtSignal(str, str)  # service_name, description

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("System Services")
        self.resize(750, 500)
        self._services: List[ServiceEntry] = []
        self._is_loading = False
        self._init_ui()
        self._load_services()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Search bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Filter:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type to filter services...")
        self.search_input.textChanged.connect(self._filter_services)
        search_layout.addWidget(self.search_input)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._load_services)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #4fc3f7; border: none;
                border-radius: 4px; padding: 6px 12px; color: #000;
            }
            QPushButton:hover { background-color: #29b6f6; }
        """)
        search_layout.addWidget(refresh_btn)
        layout.addLayout(search_layout)

        # Service table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Service", "State", "Status", "Description"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(0, 180)
        self.table.setColumnWidth(1, 60)
        self.table.setColumnWidth(2, 200)
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(self.table.SelectionMode.SingleSelection)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                border: 1px solid #333;
                color: #ccc;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #2a2a2a;
                color: #aaa;
                border: 1px solid #333;
                padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: #333;
                color: #4fc3f7;
            }
        """)
        layout.addWidget(self.table)

        # Action buttons
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(lambda: self._action("start"))
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(lambda: self._action("stop"))
        self.restart_btn = QPushButton("Restart")
        self.restart_btn.clicked.connect(lambda: self._action("restart"))
        self.enable_btn = QPushButton("Enable")
        self.enable_btn.clicked.connect(lambda: self._action("enable"))
        self.disable_btn = QPushButton("Disable")
        self.disable_btn.clicked.connect(lambda: self._action("disable"))

        for btn in [self.start_btn, self.stop_btn, self.restart_btn,
                    self.enable_btn, self.disable_btn]:
            btn.setEnabled(False)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2a2a2a; border: 1px solid #444;
                    border-radius: 4px; padding: 6px 12px; color: #ccc;
                }
                QPushButton:disabled { color: #555; }
                QPushButton:hover:!disabled { border-color: #4fc3f7; color: #fff; }
            """)
            btn_layout.addWidget(btn)

        layout.addLayout(btn_layout)

        # Explain button
        explain_layout = QHBoxLayout()
        self.explain_btn = QPushButton("Explain this service with AI")
        self.explain_btn.setEnabled(False)
        self.explain_btn.setStyleSheet("""
            QPushButton {
                background-color: #4fc3f7; border: none;
                border-radius: 6px; padding: 8px 16px; color: #000; font-weight: bold;
            }
            QPushButton:disabled { background-color: #444; color: #666; }
            QPushButton:hover:!disabled { background-color: #29b6f6; }
        """)
        self.explain_btn.clicked.connect(self._explain_service)
        explain_layout.addWidget(self.explain_btn, 1)
        layout.addLayout(explain_layout)

        self.status_label = QLabel("Loading services...")
        self.status_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.status_label)

        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self._all_services = []

    def _load_services(self):
        if self._is_loading:
            return
        self._is_loading = True
        self.status_label.setText("Loading services...")
        self.table.setRowCount(0)
        self.table.setEnabled(False)

        thread = QThread(self)
        worker = ServiceLoader()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_loaded)
        worker.error.connect(self._on_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(lambda: self._cleanup_loading(thread, worker))
        thread.start()

    def _on_loaded(self, entries: List[ServiceEntry]):
        self._is_loading = False
        self._all_services = entries
        self._services = list(entries)
        self._populate_table(entries)
        self.table.setEnabled(True)
        self.status_label.setText(f"{len(entries)} services loaded")

    def _on_error(self, msg: str):
        self._is_loading = False
        self.status_label.setText(f"Error: {msg}")
        self.table.setEnabled(True)

    def _cleanup_loading(self, thread: QThread, worker: QObject):
        thread.deleteLater()
        worker.deleteLater()

    def _populate_table(self, entries: List[ServiceEntry]):
        self.table.setRowCount(len(entries))
        for i, svc in enumerate(entries):
            self.table.setItem(i, 0, self._item(svc.name))
            self.table.setItem(i, 1, self._item(svc.state))
            status_item = self._item(svc.status)
            if svc.status == "active":
                status_item.setForeground(self._color("#4caf50"))
            elif svc.status == "inactive":
                status_item.setForeground(self._color("#ef5350"))
            elif svc.status == "failed":
                status_item.setForeground(self._color("#ff5252"))
            self.table.setItem(i, 2, status_item)
            self.table.setItem(i, 3, self._item(svc.description))

    def _item(self, text: str):
        item = QTableWidgetItem(text)
        item.setFlags(item.flags())
        return item

    def _color(self, hex_color: str):
        from PyQt6.QtGui import QColor
        return QColor(hex_color)

    def _filter_services(self, text: str):
        if not text.strip():
            self._services = list(self._all_services)
        else:
            t = text.lower()
            self._services = [s for s in self._all_services if t in s.name.lower() or t in s.description.lower()]
        self._populate_table(self._services)

    def _on_selection_changed(self):
        selected = self.table.currentRow() >= 0
        for btn in [self.start_btn, self.stop_btn, self.restart_btn,
                    self.enable_btn, self.disable_btn]:
            btn.setEnabled(selected)
        self.explain_btn.setEnabled(selected)

    def _explain_service(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._services):
            return
        svc = self._services[row]
        self.service_explain.emit(svc.name, svc.description)

    def _action(self, action: str):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._services):
            return
        svc = self._services[row]
        cmd = ["systemctl", action, f"{svc.name}.service"]
        self.status_label.setText(f"Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                self.status_label.setText(f"{action} {svc.name}: OK")
            else:
                self.status_label.setText(f"{action} {svc.name}: {result.stderr.strip()}")
        except Exception as e:
            self.status_label.setText(f"Error: {e}")
        # Reload list after action
        self._load_services()
