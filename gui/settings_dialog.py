"""Settings dialog for configuring providers, themes, and preferences."""

from typing import Any, Dict, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.audio import Transcriber
from core.config import Config


class SettingsDialog(QDialog):
    """Application settings dialog with tabs for each configuration section."""

    def __init__(self, config: Config, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Settings")
        self.setMinimumSize(550, 500)
        self.setStyleSheet(self._dialog_style())
        self._init_ui()

    @staticmethod
    def _dialog_style() -> str:
        return """
            QDialog {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QGroupBox {
                border: 1px solid #444;
                border-radius: 6px;
                margin-top: 12px;
                font-weight: bold;
                color: #ccc;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
            }
            QLineEdit {
                background-color: #2a2a2a;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 6px;
                color: #e0e0e0;
            }
            QLineEdit:focus {
                border-color: #4fc3f7;
            }
            QComboBox {
                background-color: #2a2a2a;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 6px;
                color: #e0e0e0;
            }
            QComboBox:focus { border-color: #4fc3f7; }
            QComboBox::drop-down {
                border: none;
                padding-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #2a2a2a;
                color: #e0e0e0;
                selection-background-color: #4fc3f7;
                selection-color: #000;
            }
            QLabel { color: #ccc; }
            QCheckBox { color: #ccc; spacing: 8px; }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #555;
                border-radius: 3px;
                background: #2a2a2a;
            }
            QCheckBox::indicator:checked {
                background: #4fc3f7;
                border-color: #4fc3f7;
            }
            QTabWidget::pane {
                border: 1px solid #444;
                border-radius: 4px;
                background: #1e1e1e;
            }
            QTabBar::tab {
                background: #2a2a2a;
                color: #aaa;
                padding: 8px 16px;
                border: 1px solid #444;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #1e1e1e;
                color: #fff;
                border-bottom: 1px solid #1e1e1e;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #333;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 16px;
                height: 16px;
                margin: -5px 0;
                background: #4fc3f7;
                border-radius: 8px;
            }
            QScrollArea {
                border: none;
            }
            QPushButton {
                background-color: #333;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 6px 16px;
                color: #e0e0e0;
            }
            QPushButton:hover {
                background-color: #444;
                border-color: #4fc3f7;
            }
            QSpinBox {
                background-color: #2a2a2a;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px;
                color: #e0e0e0;
            }
            QSpinBox:focus { border-color: #4fc3f7; }
        """

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Tab widget
        tabs = QTabWidget()
        tabs.addTab(self._providers_tab(), "Providers")
        tabs.addTab(self._tools_tab(), "Tools")
        tabs.addTab(self._appearance_tab(), "Appearance")
        tabs.addTab(self._speech_tab(), "Speech")
        layout.addWidget(tabs)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self._on_apply)
        layout.addWidget(buttons)

    def _providers_tab(self) -> QWidget:
        widget = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        layout = QVBoxLayout(widget)

        # Provider selector
        provider_group = QGroupBox("Active Provider")
        provider_layout = QFormLayout(provider_group)
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["openai", "anthropic", "ollama", "gemini", "openai_compatible"])
        self.provider_combo.setCurrentText(self.config.active_provider)
        provider_layout.addRow("Default Provider:", self.provider_combo)
        layout.addWidget(provider_group)

        # OpenAI
        openai_group = QGroupBox("OpenAI")
        openai_layout = QFormLayout(openai_group)
        self.openai_key = QLineEdit()
        self.openai_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_key.setText(self.config.provider_config("openai").get("api_key", ""))
        openai_layout.addRow("API Key:", self.openai_key)
        self.openai_model = QLineEdit(self.config.provider_config("openai").get("model", "gpt-4o"))
        openai_layout.addRow("Model:", self.openai_model)
        layout.addWidget(openai_group)

        # Anthropic
        anthro_group = QGroupBox("Anthropic")
        anthro_layout = QFormLayout(anthro_group)
        self.anthro_key = QLineEdit()
        self.anthro_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.anthro_key.setText(self.config.provider_config("anthropic").get("api_key", ""))
        anthro_layout.addRow("API Key:", self.anthro_key)
        self.anthro_model = QLineEdit(self.config.provider_config("anthropic").get("model", "claude-sonnet-4-20250514"))
        anthro_layout.addRow("Model:", self.anthro_model)
        layout.addWidget(anthro_group)

        # Ollama
        ollama_group = QGroupBox("Ollama (Local)")
        ollama_layout = QFormLayout(ollama_group)
        self.ollama_url = QLineEdit(self.config.provider_config("ollama").get("base_url", "http://localhost:11434"))
        ollama_layout.addRow("Base URL:", self.ollama_url)
        self.ollama_model = QLineEdit(self.config.provider_config("ollama").get("model", "llama3"))
        ollama_layout.addRow("Model:", self.ollama_model)
        layout.addWidget(ollama_group)

        # Gemini
        gemini_group = QGroupBox("Google Gemini")
        gemini_layout = QFormLayout(gemini_group)
        self.gemini_key = QLineEdit()
        self.gemini_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_key.setText(self.config.provider_config("gemini").get("api_key", ""))
        gemini_layout.addRow("API Key:", self.gemini_key)
        self.gemini_model = QLineEdit(self.config.provider_config("gemini").get("model", "gemini-2.0-flash"))
        gemini_layout.addRow("Model:", self.gemini_model)
        layout.addWidget(gemini_group)

        # OpenAI-Compatible (DeepSeek, Groq, Together, etc.)
        oai_compat_group = QGroupBox("OpenAI-Compatible (DeepSeek, Groq, Together...)")
        oai_compat_layout = QFormLayout(oai_compat_group)
        self.oai_compat_key = QLineEdit()
        self.oai_compat_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.oai_compat_key.setText(self.config.provider_config("openai_compatible").get("api_key", ""))
        oai_compat_layout.addRow("API Key:", self.oai_compat_key)
        self.oai_compat_url = QLineEdit(
            self.config.provider_config("openai_compatible").get("base_url", "https://api.deepseek.com/v1")
        )
        oai_compat_layout.addRow("Base URL:", self.oai_compat_url)
        self.oai_compat_model = QLineEdit(
            self.config.provider_config("openai_compatible").get("model", "deepseek-chat")
        )
        oai_compat_layout.addRow("Model:", self.oai_compat_model)
        layout.addWidget(oai_compat_group)

        # Common temperature
        temp_group = QGroupBox("Default Parameters")
        temp_layout = QFormLayout(temp_group)
        self.temp_slider = QSlider(Qt.Orientation.Horizontal)
        self.temp_slider.setRange(0, 100)
        current_temp = int(self.config.provider_config().get("temperature", 0.7) * 100)
        self.temp_slider.setValue(current_temp)
        self.temp_label = QLabel(f"{current_temp / 100:.1f}")
        self.temp_slider.valueChanged.connect(
            lambda v: self.temp_label.setText(f"{v / 100:.1f}")
        )
        temp_layout.addRow("Temperature:", self._slider_layout(self.temp_slider, self.temp_label))
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(256, 128000)
        self.max_tokens_spin.setValue(self.config.provider_config().get("max_tokens", 4096))
        temp_layout.addRow("Max Tokens:", self.max_tokens_spin)
        layout.addWidget(temp_group)

        layout.addStretch()
        return scroll

    def _tools_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        tools_group = QGroupBox("Enabled Tools")
        tools_layout = QVBoxLayout(tools_group)
        self.tool_checks: Dict[str, QCheckBox] = {}
        for tool_name, enabled in self.config.tools_enabled.items():
            check = QCheckBox(tool_name.replace("_", " ").title())
            check.setChecked(enabled)
            self.tool_checks[tool_name] = check
            tools_layout.addWidget(check)
        layout.addWidget(tools_group)

        layout.addStretch()
        return widget

    def _appearance_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Theme selector
        theme_group = QGroupBox("Theme")
        theme_layout = QFormLayout(theme_group)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        self.theme_combo.setCurrentText(self.config.theme)
        theme_layout.addRow("Theme:", self.theme_combo)
        layout.addWidget(theme_group)

        # Font size
        font_group = QGroupBox("Font")
        font_layout = QFormLayout(font_group)
        self.font_spin = QSpinBox()
        self.font_spin.setRange(10, 24)
        self.font_spin.setValue(self.config.font_size)
        font_layout.addRow("Font Size:", self.font_spin)
        layout.addWidget(font_group)

        # Language
        lang_group = QGroupBox("Interface")
        lang_layout = QFormLayout(lang_group)
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("Español", "es")
        self.lang_combo.addItem("English", "en")
        idx = self.lang_combo.findData(self.config.language)
        if idx >= 0:
            self.lang_combo.setCurrentIndex(idx)
        lang_layout.addRow("Language:", self.lang_combo)
        self.verbose_check = QCheckBox("Show debug messages in console")
        self.verbose_check.setChecked(self.config.verbose)
        lang_layout.addRow("Debug:", self.verbose_check)
        layout.addWidget(lang_group)

        layout.addStretch()
        return widget

    def _speech_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        group = QGroupBox("Whisper (Speech Recognition)")
        form = QFormLayout(group)

        self.whisper_model_combo = QComboBox()
        self.whisper_model_combo.addItems(["tiny", "base", "small", "medium", "large-v3"])
        self.whisper_model_combo.setCurrentText(self.config.whisper_model_size)
        form.addRow("Model Size:", self.whisper_model_combo)

        self.whisper_device_combo = QComboBox()
        self.whisper_device_combo.addItems(["auto", "cpu", "cuda"])
        self.whisper_device_combo.setCurrentText(self.config.whisper_device)
        form.addRow("Device:", self.whisper_device_combo)

        self.whisper_compute_combo = QComboBox()
        self.whisper_compute_combo.addItems(["auto", "float16", "int8_float16", "int8"])
        self.whisper_compute_combo.setCurrentText(self.config.whisper_compute_type)
        form.addRow("Compute Type:", self.whisper_compute_combo)

        hint = QLabel(
            "Changes take effect on the next recording.\n"
            "Model is loaded lazily on first use."
        )
        hint.setStyleSheet("color: #888; font-size: 11px;")
        group.layout().addWidget(hint)

        layout.addWidget(group)
        layout.addStretch()
        return widget

    @staticmethod
    def _slider_layout(slider: QSlider, label: QLabel) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(slider)
        layout.addWidget(label)
        return container

    def _on_accept(self) -> None:
        self._save_config()
        self.accept()

    def _on_apply(self) -> None:
        self._save_config()
        QMessageBox.information(self, "Settings", "Settings saved successfully.")

    def _save_config(self) -> None:
        """Save all settings from the dialog to the config."""
        # Active provider
        self.config.active_provider = self.provider_combo.currentText()

        # OpenAI
        self.config.set("providers", "openai", "api_key", self.openai_key.text())
        self.config.set("providers", "openai", "model", self.openai_model.text())

        # Anthropic
        self.config.set("providers", "anthropic", "api_key", self.anthro_key.text())
        self.config.set("providers", "anthropic", "model", self.anthro_model.text())

        # Ollama
        self.config.set("providers", "ollama", "base_url", self.ollama_url.text())
        self.config.set("providers", "ollama", "model", self.ollama_model.text())

        # Gemini
        self.config.set("providers", "gemini", "api_key", self.gemini_key.text())
        self.config.set("providers", "gemini", "model", self.gemini_model.text())

        # OpenAI-Compatible
        self.config.set("providers", "openai_compatible", "api_key", self.oai_compat_key.text())
        self.config.set("providers", "openai_compatible", "base_url", self.oai_compat_url.text())
        self.config.set("providers", "openai_compatible", "model", self.oai_compat_model.text())

        # Common params
        temp_value = self.temp_slider.value() / 100.0
        for provider in ["openai", "anthropic", "ollama", "gemini", "openai_compatible"]:
            self.config.set("providers", provider, "temperature", temp_value)
            self.config.set("providers", provider, "max_tokens", self.max_tokens_spin.value())

        # Theme
        self.config.theme = self.theme_combo.currentText()

        # Font size
        self.config.font_size = self.font_spin.value()

        # Language
        self.config.language = self.lang_combo.currentData()

        # Verbose logging
        self.config.verbose = self.verbose_check.isChecked()

        # Whisper
        self.config.whisper_model_size = self.whisper_model_combo.currentText()
        self.config.whisper_device = self.whisper_device_combo.currentText()
        self.config.whisper_compute_type = self.whisper_compute_combo.currentText()

        # Tools
        for tool_name, check in self.tool_checks.items():
            self.config.set("tools_enabled", tool_name, check.isChecked())
