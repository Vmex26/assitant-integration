"""Main application window with sidebar and chat interface."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from core.config import Config
from core.conversation import Conversation
from core.model_manager import ModelManager
from core.storage import ConversationStorage
from core.tools.base import ToolRegistry
from core.tools.file_tools import ReadFileTool, WriteFileTool, ListDirectoryTool
from core.tools.command_tools import ExecuteCommandTool, ExecutePythonTool
from core.tools.search_tools import GlobSearchTool, ContentSearchTool
from core.tools.web_tools import WebFetchTool, WebSearchTool, DownloadFileTool

from .chat_widget import ChatWidget
from .settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, config_path: Optional[Path] = None):
        super().__init__()
        self.config = Config(config_path)
        self.model_manager = ModelManager(self.config)
        self.tool_registry = ToolRegistry()
        self.storage = ConversationStorage()
        self._conversations: Dict[str, Conversation] = {}
        self._active_conversation_id: Optional[str] = None
        self._init_tools()
        self._init_ui()
        self._load_saved_conversations()

        if self._conversations:
            first_id = next(iter(self._conversations))
            self._active_conversation_id = first_id
            self.chat_widget.load_conversation(self._conversations[first_id])
            for i in range(self.conv_list.count()):
                item = self.conv_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == first_id:
                    self.conv_list.setCurrentItem(item)
                    break
        else:
            self._new_conversation()

    def closeEvent(self, event):
        """Clean up background threads on close."""
        self.chat_widget.cleanup()
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
        conv = self._conversations.get(self._active_conversation_id)
        if conv:
            try:
                self.storage.save_conversation(conv)
            except Exception as e:
                print(f"Warning: Failed to save conversation: {e}")

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

        # Chat area (temporary conversation, will be replaced after loading)
        temp_conv = Conversation(system_prompt=self._default_system_prompt())
        self.chat_widget = ChatWidget(
            self.model_manager,
            self.tool_registry,
            temp_conv,
        )
        self.chat_widget.conversation_updated.connect(self._save_active_conversation)
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
        for name in ["openai", "anthropic", "ollama", "gemini"]:
            action = QAction(name.capitalize(), self, checkable=True)
            action.setChecked(name == self.config.active_provider)
            action.triggered.connect(lambda checked, n=name: self._switch_provider(n))
            model_menu.addAction(action)

        # Help menu
        help_menu = menubar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _new_conversation(self) -> None:
        """Create a new conversation."""
        # Save the current conversation first (if any)
        self._save_active_conversation()

        conv = Conversation(system_prompt=self._default_system_prompt())
        conv_id = conv.id
        self._conversations[conv_id] = conv
        self._active_conversation_id = conv_id

        # Add to list widget
        item = QListWidgetItem(f"  {conv.title}")
        item.setData(Qt.ItemDataRole.UserRole, conv_id)
        self.conv_list.insertItem(0, item)
        self.conv_list.setCurrentItem(item)

        # Persist immediately
        self._save_active_conversation()

        # Load into chat widget
        self.chat_widget.load_conversation(conv)
        self._update_model_indicator()

    def _on_conversation_selected(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]) -> None:
        """Handle conversation selection change."""
        if current is None:
            return
        conv_id = current.data(Qt.ItemDataRole.UserRole)
        if conv_id == self._active_conversation_id:
            return
        # Save current conversation before switching
        self._save_active_conversation()
        conv = self._conversations.get(conv_id)
        if conv:
            self._active_conversation_id = conv_id
            self.chat_widget.load_conversation(conv)
            self._update_model_indicator()

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

    def _rename_conversation(self, item: QListWidgetItem) -> None:
        """Rename a conversation from the sidebar."""
        conv_id = item.data(Qt.ItemDataRole.UserRole)
        conv = self._conversations.get(conv_id)
        if not conv:
            return
        new_title, ok = QInputDialog.getText(
            self, "Rename Conversation", "New name:",
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
            self, "Delete Conversation",
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
                for i in range(self.conv_list.count()):
                    it = self.conv_list.item(i)
                    if it.data(Qt.ItemDataRole.UserRole) == first:
                        self.conv_list.setCurrentItem(it)
                        break
            else:
                self._new_conversation()

    def _switch_provider(self, name: str) -> None:
        """Switch the active AI provider."""
        provider, error = self.model_manager.switch_provider(name)
        if error:
            QMessageBox.warning(
                self, "Provider Error",
                f"Could not switch to {name}:\n\n{error}\n\n"
                f"Check your API key in Settings (Ctrl+,).\n"
                f"The app will still work, but this model won't be available until fixed.",
            )
            return
        self.config.active_provider = name
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
                QMessageBox.warning(self, "Provider Warning",
                    f"Provider re-initialization issue:\n\n{error}")
            self.chat_widget.conversation.system_prompt = self._default_system_prompt()
            self.chat_widget.conversation_updated.emit()
            self._update_model_indicator()
            self._apply_theme()

    def _clear_chat(self) -> None:
        """Clear the current chat."""
        reply = QMessageBox.question(
            self, "Clear Chat",
            "Clear the current conversation?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.chat_widget.clear_chat()

    def _save_conversation(self) -> None:
        """Save the current conversation."""
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Conversation", "", "JSON Files (*.json)"
        )
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

    @staticmethod
    def _get_os_pretty_name() -> str:
        """Read the OS pretty name from /etc/os-release."""
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        return line.split("=", 1)[1].strip().strip('"')
        except Exception:
            pass
        return "Linux"

    def _default_system_prompt() -> str:
        # Gather system info
        os_name = MainWindow._get_os_pretty_name()
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
            "You are a friendly Linux system assistant. Your primary goal is to help users understand "
            "and manage their Linux system. The user may be a beginner — explain things clearly, "
            "avoid jargon when possible, and always provide context for what a command does before "
            "suggesting it.\n\n"
            "## How to help\n"
            "- If the user encounters an error, read the relevant logs or config files and explain "
            "the issue in plain language\n"
            "- If the user describes unexpected behavior without an error message, "
            "ask clarifying questions before touching anything — gather context first\n"
            "- If the user asks about a command, explain what it does, what the output means, and "
            "any potential risks\n"
            "- If the user wants to modify the system, explain the changes and suggest safer "
            "alternatives when appropriate\n"
            "- Use the tools available to you proactively — read files, check system state, "
            "search for information\n"
            "- When in doubt, explain your reasoning before taking action\n\n"
            "## Capabilities\n"
            "You can read and write files anywhere on the system using read_file / write_file. "
            "You can list directories with list_directory, search files with glob_search, "
            "and search file contents with content_search. "
            "You can execute shell commands and Python code via execute_command / execute_python. "
            "You can fetch web content and search the web with web_fetch / web_search. "
            "Download files with download_file.\n\n"
            "## Sudo / Root Access\n"
            "You CAN use sudo, but ONLY when the user explicitly authorizes it through the "
            "graphical sudo password dialog that appears on screen. "
            "The password dialog is shown automatically by the system when you execute a "
            "command prefixed with 'sudo'. "
            "The user must enter their password in that dialog for the command to proceed. "
            "If the user cancels the dialog, the command will not run.\n\n"
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
            "- Before modifying any system file in /etc, suggest creating a backup copy "
            "first (e.g. cp file file.bak)\n"
            "- If you are unsure about the impact of a command, say so and suggest safer "
            "alternatives or ask the user to confirm\n\n"
            "Detect the user's language from their first message and respond in that language "
            "throughout the conversation."
        )
