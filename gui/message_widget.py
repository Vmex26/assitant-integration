"""Message bubble widget for rendering chat messages with markdown support."""

import re
from pathlib import Path
from typing import Any, Callable, List, Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPixmap, QTextCursor
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)


class MarkdownTextBrowser(QTextBrowser):
    """QTextBrowser with improved markdown and code rendering."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setOpenExternalLinks(True)
        self.setReadOnly(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def set_markdown(self, text: str) -> None:
        """Set markdown content with syntax highlighting."""
        html = self._markdown_to_html(text)
        self.setHtml(html)
        QTimer.singleShot(0, self._adjust_height)

    def append_markdown(self, text: str) -> None:
        """Append streaming text to existing content."""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)
        html = self._markdown_to_html(text)
        self.insertHtml(html)
        QTimer.singleShot(0, self._adjust_height)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self._adjust_height)

    def _adjust_height(self) -> None:
        """Auto-resize to fit content."""
        try:
            if self.sipIsDeleted():
                return
            w = self.viewport().width()
            if w > 0:
                self.document().setTextWidth(w)
            doc_height = self.document().size().height()
            h = min(int(doc_height) + 12, 800)
            h = max(h, 30)
            self.setFixedHeight(h)
        except Exception:
            pass

    @staticmethod
    def _markdown_to_html(text: str) -> str:
        """Convert markdown text to HTML with basic formatting."""
        import html as html_mod

        # Escape HTML entities first
        text = html_mod.escape(text)

        # Code blocks (```...```) with syntax highlighting hint
        def replace_code_block(match: "re.Match[str]") -> str:
            lang = match.group(1) or ""
            code = match.group(2)
            # We don't do full syntax highlighting here, but add language class
            lang_class = f' class="language-{lang}"' if lang else ""
            return f'<pre><code{lang_class}>{code}</code></pre>'

        text = re.sub(
            r'```(\w*)\n(.*?)```',
            replace_code_block,
            text,
            flags=re.DOTALL,
        )

        # Inline code
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)

        # Bold and italic
        text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)

        # Headers
        text = re.sub(r'^### (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
        text = re.sub(r'^## (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
        text = re.sub(r'^# (.+)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)

        # Links
        text = re.sub(
            r'\[([^\]]+)\]\(([^)]+)\)',
            r'<a href="\2">\1</a>',
            text,
        )

        # Unordered lists
        text = re.sub(r'^\s*[-*] (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
        text = re.sub(r'(<li>.*</li>\n?)+', r'<ul>\g<0></ul>', text, flags=re.DOTALL)

        # Ordered lists
        text = re.sub(r'^\s*\d+\. (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
        text = re.sub(
            r'(<li>.*</li>\n?)+',
            r'<ol>\g<0></ol>',
            text,
            flags=re.DOTALL,
        )

        # Blockquotes
        text = re.sub(r'^&gt; (.+)$', r'<blockquote>\1</blockquote>', text, flags=re.MULTILINE)

        # Horizontal rules
        text = re.sub(r'^---+$', r'<hr>', text, flags=re.MULTILINE)

        # Paragraphs (double newlines)
        paragraphs = text.split("\n\n")
        processed = []
        for para in paragraphs:
            stripped = para.strip()
            if not stripped:
                continue
            if not stripped.startswith(("<h", "<ul", "<ol", "<li", "<pre", "<blockquote", "<hr")):
                stripped = f"<p>{stripped}</p>"
            processed.append(stripped)

        return "\n".join(processed)


class MessageWidget(QFrame):
    """A single message bubble in the chat."""

    def __init__(
        self,
        role: str,
        content: str,
        files: Optional[List[str]] = None,
        is_streaming: bool = False,
        on_tts: Optional[Callable[[str], None]] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.role = role
        self.files = files or []
        self.is_streaming = is_streaming
        self._full_content = content
        self._on_tts = on_tts
        self._init_ui()

    def _init_ui(self) -> None:
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Minimum,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # Header (role label + timestamp)
        header_layout = QHBoxLayout()
        role_label = QLabel(self._get_role_display())
        role_label.setStyleSheet(self._get_role_style())
        role_label.setFont(QFont("sans-serif", 10, QFont.Weight.Bold))
        header_layout.addWidget(role_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # File attachments
        for file_path in self.files:
            file_widget = self._create_file_attachment(file_path)
            if file_widget:
                layout.addWidget(file_widget)

        # Message content — plain text for tool, markdown for others
        if self.role == "tool":
            self.text_label = QLabel(self._full_content)
            self.text_label.setWordWrap(True)
            self.text_label.setStyleSheet("""
                QLabel {
                    background: transparent;
                    color: #c0c0c0;
                    font-size: 12px;
                    font-family: 'Courier New', monospace;
                    padding: 4px;
                }
            """)
            layout.addWidget(self.text_label)
        else:
            self.text_browser = MarkdownTextBrowser()
            self.text_browser.set_markdown(self._full_content)
            self.text_browser.setStyleSheet(self._get_content_style())
            layout.addWidget(self.text_browser)

        # Button row
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        if self.role == "assistant" and self._on_tts:
            tts_btn = QPushButton("🔊 Speak")
            tts_btn.setFixedSize(80, 24)
            tts_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: 1px solid #555;
                    border-radius: 4px;
                    color: #81c784;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background: #2a3a2a;
                    color: #a5d6a7;
                }
            """)
            tts_btn.clicked.connect(lambda: self._on_tts(self._full_content))
            btn_layout.addWidget(tts_btn)

        copy_btn = QPushButton("Copy")
        copy_btn.setFixedSize(60, 24)
        copy_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #555;
                border-radius: 4px;
                color: #aaa;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #3a3a3a;
                color: #fff;
            }
        """)
        copy_btn.clicked.connect(self._copy_content)
        btn_layout.addWidget(copy_btn)
        layout.addLayout(btn_layout)

        self.setStyleSheet(self._get_bubble_style())

    def _get_role_display(self) -> str:
        if self.role == "user":
            return "You"
        elif self.role == "assistant":
            return "Assistant"
        elif self.role == "system":
            return "System"
        elif self.role == "tool":
            return "Tool"
        return self.role.capitalize()

    def _get_role_style(self) -> str:
        colors = {
            "user": "color: #4fc3f7;",
            "assistant": "color: #81c784;",
            "system": "color: #ffb74d;",
            "tool": "color: #a1887f;",
        }
        return colors.get(self.role, "color: #ccc;")

    def _get_bubble_style(self) -> str:
        user_bg = "#1a3a4a"
        assistant_bg = "#2a2a2a"
        system_bg = "#3a2a1a"
        tool_bg = "#2a2520"
        bg = {
            "user": user_bg,
            "assistant": assistant_bg,
            "system": system_bg,
            "tool": tool_bg,
        }.get(self.role, assistant_bg)
        return f"""
            MessageWidget {{
                background-color: {bg};
                border-radius: 8px;
                margin: 4px 0px;
            }}
        """

    def _get_content_style(self) -> str:
        return """
            QTextBrowser {
                background: transparent;
                color: #e0e0e0;
                font-size: 13px;
                border: none;
                padding: 4px;
            }
            QTextBrowser h1 { color: #fff; font-size: 18px; }
            QTextBrowser h2 { color: #eee; font-size: 16px; }
            QTextBrowser h3 { color: #ddd; font-size: 14px; }
            QTextBrowser code {
                background-color: #1a1a1a;
                color: #a8d8ea;
                padding: 1px 4px;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
            }
            QTextBrowser pre {
                background-color: #1a1a1a;
                color: #d4d4d4;
                padding: 8px;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
            }
            QTextBrowser a { color: #4fc3f7; }
            QTextBrowser blockquote {
                border-left: 3px solid #555;
                margin: 8px 0;
                padding: 4px 12px;
                color: #aaa;
            }
            QTextBrowser hr { border: none; border-top: 1px solid #444; }
            QTextBrowser ul, QTextBrowser ol { margin: 4px 0; }
            QTextBrowser li { margin: 2px 0; }
        """

    def _create_file_attachment(self, file_path: str) -> Optional[QWidget]:
        """Create a widget showing an attached file."""
        path = Path(file_path)
        if not path.exists():
            return None

        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: #333;
                border-radius: 4px;
                padding: 4px;
            }
        """)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(8, 4, 8, 4)

        # Show image thumbnail if image
        ext = path.suffix.lower()
        if ext in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                scaled = pixmap.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                img_label = QLabel()
                img_label.setPixmap(scaled)
                img_label.setFixedSize(120, 120)
                layout.addWidget(img_label)

        name_label = QLabel(f"📎 {path.name}")
        name_label.setStyleSheet("color: #aaa; font-size: 12px;")
        layout.addWidget(name_label)
        layout.addStretch()

        return container

    def append_stream_text(self, text: str) -> None:
        """Append text during streaming."""
        self._full_content += text
        if self.role == "tool":
            self.text_label.setText(self._full_content)
        else:
            self.text_browser.append_markdown(text)

    def _copy_content(self) -> None:
        """Copy message content to clipboard."""
        from PyQt6.QtGui import QGuiApplication
        QGuiApplication.clipboard().setText(self._full_content)

    def set_content(self, content: str) -> None:
        """Set/replace the full content."""
        self._full_content = content
        if self.role == "tool":
            self.text_label.setText(content)
        else:
            self.text_browser.set_markdown(content)
