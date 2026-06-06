"""
System health panel - shows real-time system metrics in the sidebar.
"""

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class SystemHealthPanel(QWidget):
    """Compact widget showing CPU, RAM, disk, and temperature."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._init_ui()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(5000)
        self._refresh()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 4)
        layout.setSpacing(3)

        header = QLabel("System")
        header.setStyleSheet("color: #4fc3f7; font-size: 13px; font-weight: bold;")
        layout.addWidget(header)

        def make_row(label_text: str) -> tuple[QLabel, QProgressBar, QHBoxLayout]:
            row = QHBoxLayout()
            row.setSpacing(6)
            lbl = QLabel(label_text)
            lbl.setFixedWidth(32)
            lbl.setStyleSheet("color: #aaa; font-size: 11px;")
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setTextVisible(False)
            bar.setFixedHeight(10)
            bar.setStyleSheet("""
                QProgressBar {
                    background-color: #2a2a2a;
                    border-radius: 3px;
                }
                QProgressBar::chunk {
                    border-radius: 3px;
                    background-color: #4fc3f7;
                }
            """)
            row.addWidget(lbl)
            row.addWidget(bar, 1)
            layout.addLayout(row)
            return lbl, bar, row

        self.cpu_label, self.cpu_bar, _ = make_row("CPU")
        self.ram_label, self.ram_bar, _ = make_row("RAM")
        self.disk_label, self.disk_bar, _ = make_row("Disk")

        self.temp_label = QLabel()
        self.temp_label.setStyleSheet("color: #888; font-size: 10px;")
        self.temp_label.setVisible(False)
        layout.addWidget(self.temp_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #333;")
        layout.addWidget(sep)

    def _refresh(self):
        import psutil

        cpu = int(psutil.cpu_percent(interval=0))
        self.cpu_bar.setValue(cpu)
        color = self._bar_color(cpu)
        self.cpu_bar.setStyleSheet(self._bar_style(color))

        ram = psutil.virtual_memory()
        ram_pct = int(ram.percent)
        self.ram_bar.setValue(ram_pct)
        self.ram_label.setText("RAM")
        self.ram_bar.setStyleSheet(self._bar_style(self._bar_color(ram_pct)))

        disk = psutil.disk_usage("/")
        disk_pct = int(disk.percent)
        self.disk_bar.setValue(disk_pct)
        self.disk_label.setText("Disk")
        self.disk_bar.setStyleSheet(self._bar_style(self._bar_color(disk_pct)))

        temps = psutil.sensors_temperatures()
        for name, entries in temps.items():
            if entries:
                self.temp_label.setText(f"Temp: {entries[0].current:.0f}°C")
                self.temp_label.setVisible(True)
                break
        else:
            self.temp_label.setVisible(False)

    def _bar_color(self, pct: int) -> str:
        if pct < 60:
            return "#4fc3f7"
        if pct < 85:
            return "#ffa726"
        return "#ef5350"

    def _bar_style(self, color: str) -> str:
        return f"""
            QProgressBar {{
                background-color: #2a2a2a;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                border-radius: 3px;
                background-color: {color};
            }}
        """

    def cleanup(self):
        self._timer.stop()
