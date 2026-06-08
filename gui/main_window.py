"""Main application window with sidebar and chat interface."""

import os
import typing
from pathlib import Path

from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from core.config import Config
from core.conversation import Conversation
from core.logger import get_logger
from core.model_manager import ModelManager
from core.storage import ConversationStorage
from core.tools.base import ToolRegistry
from core.tools.command_tools import ExecuteCommandTool, ExecutePythonTool
from core.tools.file_tools import ListDirectoryTool, ReadFileTool, WriteFileTool
from core.tools.package_tools import SearchPackageTool, ShowPKGBUILDTool
from core.tools.search_tools import ContentSearchTool, GlobSearchTool
from core.tools.software_assistant import SoftwareAssistantTool
from core.tools.web_tools import DownloadFileTool, WebFetchTool, WebSearchTool

from .chat_widget import ChatWidget

logger = get_logger(__name__)
from .log_dialog import LogDialog  # noqa: E402
from .service_dialog import ServiceDialog  # noqa: E402
from .settings_dialog import SettingsDialog  # noqa: E402
from .system_panel import SystemHealthPanel  # noqa: E402


class GlobalHotkeyListener(QObject):
    """QShortcut-based hotkey listener. Requires app focus."""

    triggered = pyqtSignal()
    SHORTCUT = "Ctrl+Shift+Space"

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._shortcut = QShortcut(QKeySequence(self.SHORTCUT), parent)
        self._shortcut.activated.connect(self.triggered)

    def cleanup(self) -> None:
        pass


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, config_path: Path | None = None):
        super().__init__()
        self.config = Config(config_path)
        self.model_manager = ModelManager(self.config)
        self.tool_registry = ToolRegistry()
        self.storage = ConversationStorage()
        self._conversations: dict[str, Conversation] = {}
        self._active_conversation_id: str | None = None
        self._init_tools()
        self._init_ui()
        self._load_saved_conversations()

        self._new_conversation()

        # Global hotkey for voice call mode (key 199)
        self._hotkey_listener = GlobalHotkeyListener(self)
        self._hotkey_listener.triggered.connect(self._on_call_hotkey)

    @typing.override
    def closeEvent(self, event):
        """Clean up background threads on close."""
        self.chat_widget.cleanup()
        self.system_health.cleanup()
        self._hotkey_listener.cleanup()
        super().closeEvent(event)

    def _init_tools(self) -> None:
        """Register all available tools."""
        for tool_cls in [
            ReadFileTool,
            WriteFileTool,
            ListDirectoryTool,
            ExecuteCommandTool,
            ExecutePythonTool,
            GlobSearchTool,
            ContentSearchTool,
            WebFetchTool,
            WebSearchTool,
            DownloadFileTool,
            SearchPackageTool,
            ShowPKGBUILDTool,
            SoftwareAssistantTool,
        ]:
            self.tool_registry.register(tool_cls())

    def _load_saved_conversations(self) -> None:
        """Load saved conversations from storage into the sidebar."""
        summaries = self.storage.list_conversations()
        for summary in summaries:
            conv = self.storage.load_conversation(summary["id"])
            if conv:
                self._conversations[conv.id] = conv
                item = QListWidgetItem(f"  {conv.title}")
                item.setData(Qt.ItemDataRole.UserRole, conv.id)
                self.conv_list.addItem(item)

    def _save_active_conversation(self) -> None:
        """Persist the current conversation to storage."""
        conv_id = self._active_conversation_id or ""
        conv = self._conversations.get(conv_id)
        if conv and len(conv) > 0:
            try:
                self.storage.save_conversation(conv)
            except Exception as e:
                logger.warning("Failed to save conversation: %s", e)

    def _init_ui(self) -> None:
        self.setWindowTitle("AI Assistant Integrer")
        self.setMinimumSize(900, 600)
        self.resize(1200, 800)
        self._apply_theme()

        # Central widget with splitter
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #333;
            }
        """)

        # Sidebar
        sidebar = self._create_sidebar()
        splitter.addWidget(sidebar)

        # Chat area (temporary conversation)
        temp_conv = Conversation(system_prompt=self._default_system_prompt())
        self._conversations[temp_conv.id] = temp_conv
        self._active_conversation_id = temp_conv.id

        # Add temp_conv to sidebar list
        item = QListWidgetItem(f"  {temp_conv.title}")
        item.setData(Qt.ItemDataRole.UserRole, temp_conv.id)
        self.conv_list.addItem(item)
        self.conv_list.setCurrentItem(item)

        self.chat_widget = ChatWidget(
            self.model_manager,
            self.tool_registry,
            temp_conv,
            config=self.config,
        )
        self.chat_widget.conversation_updated.connect(self._save_active_conversation)
        self.chat_widget.conversation_renamed.connect(self._on_conversation_renamed)
        splitter.addWidget(self.chat_widget)

        splitter.setSizes([250, 950])
        main_layout.addWidget(splitter)

        # Create menu bar
        self._create_menu_bar()

    def _create_sidebar(self) -> QWidget:
        """Create the left sidebar with conversation list."""
        sidebar = QWidget()
        sidebar.setFixedWidth(250)
        sidebar.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border-right: 1px solid #333;
            }
        """)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # System health panel
        self.system_health = SystemHealthPanel()
        layout.addWidget(self.system_health)

        # Quick actions
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(4)

        info_btn = QPushButton("Info")
        info_btn.setToolTip("Show system information")
        info_btn.setStyleSheet(self._action_btn_style())
        info_btn.clicked.connect(
            lambda: self._confirm_and_run(
                "uname -a; echo '---'; lsb_release -a 2>/dev/null || cat /etc/os-release",
                "Show system information (OS, kernel, architecture)?",
            )
        )

        disk_btn = QPushButton("Disk")
        disk_btn.setToolTip("Show disk usage")
        disk_btn.setStyleSheet(self._action_btn_style())
        disk_btn.clicked.connect(
            lambda: self._confirm_and_run(
                "df -h | head -20", "Show disk usage for all mounted filesystems?"
            )
        )

        log_btn = QPushButton("Logs")
        log_btn.setToolTip("Analyze system logs")
        log_btn.setStyleSheet(self._action_btn_style())
        log_btn.clicked.connect(self._open_log_dialog)

        svc_btn = QPushButton("Services")
        svc_btn.setToolTip("View and manage system services")
        svc_btn.setStyleSheet(self._action_btn_style())
        svc_btn.clicked.connect(self._open_service_dialog)

        actions_layout.addWidget(info_btn)
        actions_layout.addWidget(disk_btn)
        actions_layout.addWidget(log_btn)
        actions_layout.addWidget(svc_btn)
        layout.addLayout(actions_layout)

        # Header
        header = QLabel("Conversations")
        header.setStyleSheet("color: #e0e0e0; font-size: 14px; font-weight: bold; padding: 4px;")
        layout.addWidget(header)

        # New conversation button
        new_btn = QPushButton("+ New Conversation")
        new_btn.setStyleSheet("""
            QPushButton {
                background-color: #4fc3f7;
                border: none;
                border-radius: 6px;
                padding: 8px;
                color: #000;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #29b6f6;
            }
        """)
        new_btn.clicked.connect(self._new_conversation)
        layout.addWidget(new_btn)

        # Conversation list
        self.conv_list = QListWidget()
        self.conv_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                border: none;
                outline: none;
                color: #ccc;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
                margin: 2px 0;
            }
            QListWidget::item:selected {
                background-color: #2a3a4a;
                color: #fff;
            }
            QListWidget::item:hover {
                background-color: #2a2a2a;
            }
        """)
        self.conv_list.currentItemChanged.connect(self._on_conversation_selected)
        self.conv_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.conv_list.customContextMenuRequested.connect(self._on_conv_context_menu)
        layout.addWidget(self.conv_list, 1)

        # Model indicator
        self.model_indicator = QLabel()
        self.model_indicator.setStyleSheet("color: #666; font-size: 11px; padding: 4px;")
        self._update_model_indicator()
        layout.addWidget(self.model_indicator)

        return sidebar

    def _action_btn_style(self) -> str:
        return """
            QPushButton {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 5px 8px;
                color: #ccc;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #333;
                border-color: #4fc3f7;
                color: #fff;
            }
        """

    def _run_diagnostic(self, command: str) -> None:
        """Run a diagnostic command via the AI assistant."""
        self.chat_widget.send_as_user(
            f"[System Action] Run this diagnostic and explain the results:\n```bash\n{command}\n```"
        )

    def _confirm_and_run(self, command: str, question: str) -> None:
        """Ask confirmation before running a diagnostic."""
        reply = QMessageBox.question(
            self,
            "Confirm diagnostic",
            question,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._run_diagnostic(command)

    def _open_log_dialog(self) -> None:
        """Open the log analyzer dialog."""
        dialog = LogDialog(self)
        dialog.log_ready.connect(self._on_log_ready)
        dialog.show()

    def _open_service_dialog(self) -> None:
        """Open the service manager dialog."""
        dialog = ServiceDialog(self)
        dialog.service_explain.connect(self._on_service_explain)
        dialog.show()

    def _on_service_explain(self, name: str, description: str) -> None:
        """Send a service description to the AI for explanation."""
        self.chat_widget.send_as_user(
            f"[System Action] Explain what this systemd service does, "
            f"whether it's safe to disable, and what depends on it:\n\n"
            f"- **Service:** {name}\n"
            f"- **Description:** {description}\n\n"
            f"Use `systemctl cat {name}.service` or check its unit file if needed."
        )

    def _on_log_ready(self, content: str, description: str) -> None:
        """Handle log content from the log dialog."""
        self.chat_widget.send_as_user(
            f"[System Action] Log analysis requested — {description}:\n```\n{content}\n```\n\n"
            "Analyze these logs and explain any errors or warnings in plain language. "
            "If you find issues, suggest how to fix them."
        )

    def _create_menu_bar(self) -> None:
        """Create the application menu bar."""
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #1e1e1e;
                color: #ccc;
                border-bottom: 1px solid #333;
                padding: 2px;
            }
            QMenuBar::item:selected {
                background-color: #333;
            }
            QMenu {
                background-color: #2a2a2a;
                color: #ccc;
                border: 1px solid #444;
            }
            QMenu::item:selected {
                background-color: #4fc3f7;
                color: #000;
            }
            QMenu::separator {
                height: 1px;
                background: #444;
                margin: 4px 8px;
            }
        """)

        # File menu
        file_menu = menubar.addMenu("File")
        new_action = QAction("New Conversation", self)
        new_action.setShortcut(QKeySequence("Ctrl+N"))
        new_action.triggered.connect(self._new_conversation)
        file_menu.addAction(new_action)

        save_action = QAction("Save Conversation", self)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(self._save_conversation)
        file_menu.addAction(save_action)

        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        settings_action = QAction("Settings...", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._show_settings)
        edit_menu.addAction(settings_action)

        clear_action = QAction("Clear Chat", self)
        clear_action.setShortcut(QKeySequence("Ctrl+L"))
        clear_action.triggered.connect(self._clear_chat)
        edit_menu.addAction(clear_action)

        # Model menu
        model_menu = menubar.addMenu("Model")
        for name in ["openai", "anthropic", "ollama", "gemini", "openai_compatible"]:
            action = QAction(name.capitalize(), self)
            action.setCheckable(True)
            action.setChecked(name == self.config.active_provider)
            action.triggered.connect(lambda checked, n=name: self._switch_provider(n))
            model_menu.addAction(action)

        # Help menu
        help_menu = menubar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _new_conversation(self) -> None:
        """Create a new conversation, or switch to an empty one if one exists."""
        # Check for existing empty conversation
        for conv_id, conv in self._conversations.items():
            if len(conv) == 0:
                self._save_active_conversation()
                self.chat_widget.load_conversation(conv)
                self._active_conversation_id = conv_id
                self.conv_list.blockSignals(True)
                for i in range(self.conv_list.count()):
                    item = self.conv_list.item(i)
                    if item and item.data(Qt.ItemDataRole.UserRole) == conv_id:
                        self.conv_list.setCurrentItem(item)
                        break
                self.conv_list.blockSignals(False)
                self._update_model_indicator()
                return

        self._save_active_conversation()

        conv = Conversation(system_prompt=self._default_system_prompt())
        conv_id = conv.id
        self._conversations[conv_id] = conv
        self._active_conversation_id = conv_id

        # Add to list widget
        self.conv_list.blockSignals(True)
        item = QListWidgetItem(f"  {conv.title}")
        item.setData(Qt.ItemDataRole.UserRole, conv_id)
        self.conv_list.insertItem(0, item)
        self.conv_list.setCurrentItem(item)
        self.conv_list.blockSignals(False)

        # Load into chat widget
        self.chat_widget.load_conversation(conv)
        self._update_model_indicator()

    def _on_call_hotkey(self) -> None:
        """Handle global hotkey press: new conversation + start call mode."""
        self._new_conversation()
        QTimer.singleShot(100, self._delayed_start_call)

    def _delayed_start_call(self) -> None:
        """Start call mode after conversation is loaded."""
        try:
            self.chat_widget._start_call()
        except RuntimeError:
            pass

    def _on_conversation_selected(
        self, current: QListWidgetItem | None, previous: QListWidgetItem | None
    ) -> None:
        """Handle conversation selection change."""
        if current is None:
            return
        conv_id = current.data(Qt.ItemDataRole.UserRole)
        if conv_id == self._active_conversation_id:
            return
        # Save current conversation before switching
        self._save_active_conversation()
        conv = self._conversations.get(conv_id)
        if conv is not None:
            self._active_conversation_id = conv_id
            self.chat_widget.load_conversation(conv)
            self._update_model_indicator()
        else:
            logger.error("Conversation %s not found in self._conversations.", conv_id)

    def _on_conv_context_menu(self, pos) -> None:
        """Show right-click context menu for conversation list items."""
        item = self.conv_list.itemAt(pos)
        if not item:
            return
        menu = QMenu(self)
        rename_action = menu.addAction("Rename")
        delete_action = menu.addAction("Delete")
        action = menu.exec(self.conv_list.mapToGlobal(pos))
        if action == rename_action:
            self._rename_conversation(item)
        elif action == delete_action:
            self._delete_conversation(item)

    def _on_conversation_renamed(self, conv_id: str, title: str) -> None:
        """Update sidebar item when conversation is auto-renamed."""
        for i in range(self.conv_list.count()):
            item = self.conv_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == conv_id:
                item.setText(f"  {title}")
                break

    def _rename_conversation(self, item: QListWidgetItem) -> None:
        """Rename a conversation from the sidebar."""
        conv_id = item.data(Qt.ItemDataRole.UserRole)
        conv = self._conversations.get(conv_id)
        if not conv:
            return
        new_title, ok = QInputDialog.getText(
            self,
            "Rename Conversation",
            "New name:",
            text=conv.title,
        )
        if ok and new_title.strip():
            conv.title = new_title.strip()
            item.setText(f"  {conv.title}")
            self._save_active_conversation()

    def _delete_conversation(self, item: QListWidgetItem) -> None:
        """Delete a conversation from the sidebar."""
        conv_id = item.data(Qt.ItemDataRole.UserRole)
        conv = self._conversations.get(conv_id)
        if not conv:
            return
        reply = QMessageBox.question(
            self,
            "Delete Conversation",
            f'Delete "{conv.title}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.storage.delete_conversation(conv_id)
        del self._conversations[conv_id]
        row = self.conv_list.row(item)
        self.conv_list.takeItem(row)
        if self._active_conversation_id == conv_id:
            remaining = list(self._conversations.keys())
            if remaining:
                first = remaining[0]
                self._active_conversation_id = first
                self.chat_widget.load_conversation(self._conversations[first])
                self.conv_list.blockSignals(True)
                for i in range(self.conv_list.count()):
                    it = self.conv_list.item(i)
                    if it.data(Qt.ItemDataRole.UserRole) == first:
                        self.conv_list.setCurrentItem(it)
                        break
                self.conv_list.blockSignals(False)
            else:
                self._new_conversation()

    def _switch_provider(self, name: str) -> None:
        """Switch the active AI provider."""
        provider, error = self.model_manager.switch_provider(name)
        if error:
            QMessageBox.warning(
                self,
                "Provider Error",
                f"Could not switch to {name}:\n\n{error}\n\n"
                f"Check your API key in Settings (Ctrl+,).\n"
                f"The app will still work, but this model won't be available until fixed.",
            )
            return
        self._update_model_indicator()

        # Update menu check states
        for action in self.menuBar().actions():
            menu = action.menu()
            if menu and action.text() == "Model":
                for a in menu.actions():
                    a.setChecked(a.text().lower() == name)

    def _update_model_indicator(self) -> None:
        """Update the model indicator label in the sidebar."""
        provider_name = self.config.active_provider
        provider_config = self.config.provider_config()
        model = provider_config.get("model", "unknown")
        self.model_indicator.setText(f"Model: {provider_name}/{model}")

    def _show_settings(self) -> None:
        """Open the settings dialog."""
        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            provider, error = self.model_manager.reload_provider()
            if error:
                QMessageBox.warning(
                    self, "Provider Warning", f"Provider re-initialization issue:\n\n{error}"
                )
            self.chat_widget.conversation.system_prompt = self._default_system_prompt()
            self.chat_widget.conversation_updated.emit()
            self._update_model_indicator()
            self._apply_theme()

    def _clear_chat(self) -> None:
        """Clear the current chat."""
        reply = QMessageBox.question(
            self,
            "Clear Chat",
            "Clear the current conversation?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.chat_widget.clear_chat()

    def _save_conversation(self) -> None:
        """Save the current conversation."""
        from PyQt6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(self, "Save Conversation", "", "JSON Files (*.json)")
        if path:
            self.chat_widget.conversation.save(Path(path))

    def _apply_theme(self) -> None:
        """Apply the current theme to the application."""
        theme = self.config.theme
        if theme == "dark":
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #1a1a1a;
                }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #f5f5f5;
                }
            """)

    def _show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About AI Assistant Integrer",
            "AI Assistant Integrer v1.0\n\n"
            "A modular AI assistant with support for multiple LLM providers,\n"
            "tool execution, and rich chat interface.\n\n"
            "Built with Python + PyQt6",
        )

    def _get_os_pretty_name(self) -> str:
        """Read the OS pretty name from /etc/os-release."""
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        return line.split("=", 1)[1].strip().strip('"')
        except Exception:
            pass
        return "Linux"

    def _default_system_prompt(self) -> str:
        # Gather system info
        os_name = self._get_os_pretty_name()
        machine = os.uname().machine
        cpu = "unknown"
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.startswith("model name"):
                        cpu = line.split(":", 1)[1].strip()
                        break
        except Exception:
            pass
        memory = "unknown"
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal"):
                        kb = int(line.split()[1])
                        memory = f"{kb // 1024} MB"
                        break
        except Exception:
            pass
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "unknown")
        session = os.environ.get("XDG_SESSION_TYPE", "unknown")
        shell = os.environ.get("SHELL", "unknown")

        lang = self.config.language
        lang_instruction = (
            "The user's language is set to Spanish — respond in Spanish."
            if lang == "es"
            else "The user's language is set to English — respond in English."
        )

        return (
            "## System Information\n"
            f"- OS: {os_name}\n"
            f"- Kernel: {os.uname().release}\n"
            f"- Architecture: {machine}\n"
            f"- CPU: {cpu}\n"
            f"- Memory: {memory}\n"
            f"- Desktop: {desktop} ({session})\n"
            f"- Shell: {shell}\n\n"
            "## Your Role\n"
            "You are a friendly Linux system assistant. Your primary goal is "
            "to help users understand and manage their Linux system. "
            "The user may be a beginner — explain things clearly, "
            "avoid jargon when possible.\n\n"
            "## How to help\n"
            "- Messages prefixed with `[System Action]` are sent automatically by the software "
            "(e.g. diagnostic buttons, log analyzer, service explain). "
            "Treat them as direct requests from the user — the user triggered the action, "
            "but the content was gathered automatically.\n"
            "- If the user encounters an error, read the relevant logs or config files and explain "
            "the issue in plain language\n"
            "- If the user describes unexpected behavior without an error message, "
            "ask clarifying questions before touching anything — gather context first\n"
            "- If the user needs to run a command, use execute_command yourself — "
            "do NOT ask the user to open a terminal or run it manually. "
            "The system will show a confirmation dialog to the user before the command runs.\n"
            "- Use common sense about when to ask for confirmation:\n"
            "  - Safe, reversible actions (reading files, listing directories, creating "
            "new files in user space) — proceed directly and inform the user of what you did\n"
            "  - Actions that modify existing files or install software — briefly explain "
            "and ask before proceeding\n"
            "  - Anything requiring sudo, destructive, or irreversible — always explain "
            "in detail and require explicit confirmation\n"
            "- If the user asks about a command, explain what it does, what the output means, and "
            "any potential risks\n"
            "- If the user wants to modify the system, explain the changes and suggest safer "
            "alternatives when appropriate\n"
            "- Use the tools available to you proactively — read files, check system state, "
            "search for information\n"
            "- After running a diagnostic or finding an issue, offer the next logical step: "
            '"Your disk is at 90% — do you want me to find large files?" or '
            '"There are failed service units — do you want me to check their logs?"\n'
            "- When in doubt, explain your reasoning before taking action\n\n"
            "## Capabilities\n"
            "You can read and write files anywhere on the system using read_file / write_file. "
            "You can list directories with list_directory, search files with glob_search, "
            "and search file contents with content_search. "
            "You can execute shell commands and Python code via execute_command / execute_python. "
            "Both tools include a built-in confirmation dialog — the user sees your explanation "
            "and the command, and decides whether to allow it.\n"
            "You can fetch web content and search the web with web_fetch / web_search. "
            "Download files with download_file.\n\n"
            "## Background Processes & GUI Applications\n"
            "When executing commands that launch GUI applications (like 'firefox') or background processes where "  # noqa: E501
            "you do not need any output from the process, you MUST use the following exact pattern to ensure "  # noqa: E501
            "it is fully detached and does not hang the assistant:\n"
            "`command > /dev/null 2>&1 & disown`\n"
            "- The entire segment `> /dev/null 2>&1` is REQUIRED to redirect stdout and stderr to null, "  # noqa: E501
            "preventing the process from trying to write to the assistant's buffers.\n"
            "- The `&` is required to run it in the background.\n"
            "- The `disown` is required to detach it from the assistant's process table.\n"
            "NEVER omit the redirection part.\n\n"
            "## Sudo / Root Access\n"
            "You CAN use sudo. However, you must follow these rules for security:\n"
            "- If the user EXPLICITLY asks to run a command with sudo, you may invoke the tool with `user_confirmed: True`.\n"  # noqa: E501
            "- If you infer that sudo is needed but the user has not explicitly requested it, "
            "you MUST explain why you need it, ask for confirmation, and invoke the tool with `user_confirmed: False` (or omit the parameter).\n"  # noqa: E501
            "The graphical sudo password dialog will ALWAYS appear as a final safety layer.\n\n"
            "You can access user files with the available tools, but always inform the user "
            "before writing or modifying any file, even without sudo.\n\n"
            "## Safety rules\n"
            "- NEVER suggest rm -rf, mkfs, dd, or any command that could destroy data or the "
            "operating system without an explicit warning that the action is irreversible, "
            "and even then, suggest a backup first\n"
            "- NEVER suggest disabling security features (firewall, SELinux, AppArmor, "
            "secure boot) as a first resort — investigate the real cause first\n"
            "- NEVER pipe curl/wget output directly into bash or sudo without first showing "
            "the user what the script contains\n"
            "- NEVER modify boot configuration (GRUB, kernel parameters, initramfs, fstab) "
            "without explaining exactly what each change does and suggesting a backup\n"
            "- If the system uses Arch Linux or an Arch derivative, avoid touching AUR helpers "
            "(paru, yay, pamac) cache or database files, and do not suggest manual PKGBUILD "
            "modifications unless the user explicitly asks for it\n"
            "- Be especially careful with pacman — avoid --force, --overwrite, or "
            "--dependsonly unless the user understands the risks\n"
            "- Before installing an AUR package, ALWAYS use show_pkgbuild first to inspect "
            "the PKGBUILD. Act as an auditor: check the maintainer's reputation (votes, "
            "popularity), review what the package does, examine sourced files and their "
            "origin URLs, and flag anything suspicious (precompiled binaries, curl/wget "
            "piped to shell, obscure sources). Clearly state whether the package looks "
            "trustworthy and what risk it poses to system stability before the user "
            "decides to install.\n"
            "- Before modifying any system file in /etc, suggest creating a backup copy "
            "first (e.g. cp file file.bak)\n"
            "- If you are unsure about the impact of a command, say so and suggest safer "
            "alternatives or ask the user to confirm\n\n"
            f"{lang_instruction}"
        )
