"""Chat widget - the main conversation interface with message display and input."""

import asyncio
import json
import os as _os
import queue
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import threading as _threading

from PyQt6.QtCore import QObject, Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QKeyEvent
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.audio import AudioRecorder, TTSEngine, Transcriber
from core.conversation import Conversation, Message
from core.model_manager import ModelManager
from core.tools.base import ToolRegistry
from utils.helpers import format_api_error

from .message_widget import MessageWidget


class MessageInput(QPlainTextEdit):
    """Custom text input with Shift+Enter for newline, Enter to send."""

    send_requested = pyqtSignal()
    files_pasted = pyqtSignal(list)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setPlaceholderText("Type a message... (Shift+Enter for newline)")
        self.setFont(QFont("sans-serif", 13))
        self.setFixedHeight(60)
        self._temp_files: List[str] = []
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 8px;
                padding: 10px;
                color: #e0e0e0;
                selection-background-color: #4fc3f7;
                selection-color: #000;
            }
            QPlainTextEdit:focus {
                border-color: #4fc3f7;
            }
        """)

    def insertFromMimeData(self, source: Any) -> None:
        """Handle paste events - extract images/files from clipboard."""
        saved_files = []

        if source.hasImage():
            image = source.imageData()
            if image:
                path = self._save_clipboard_image(image)
                if path:
                    saved_files.append(path)

        if source.hasUrls():
            for url in source.urls():
                if url.isLocalFile():
                    saved_files.append(url.toLocalFile())

        if saved_files:
            self.files_pasted.emit(saved_files)

        if source.hasText():
            from PyQt6.QtCore import QMimeData
            text_only = QMimeData()
            text_only.setText(source.text())
            super().insertFromMimeData(text_only)
        else:
            super().insertFromMimeData(source)

    def _save_clipboard_image(self, image: Any) -> Optional[str]:
        """Save a QImage/QPixmap from clipboard to a temp file."""
        import tempfile
        from PyQt6.QtGui import QPixmap
        try:
            pixmap = QPixmap.fromImage(image) if not isinstance(image, QPixmap) else image
            tmp = tempfile.NamedTemporaryFile(
                suffix=".png", delete=False, prefix="clipboard_"
            )
            tmp.close()
            pixmap.save(tmp.name, "PNG")
            self._temp_files.append(tmp.name)
            return tmp.name
        except Exception as e:
            print(f"Failed to save clipboard image: {e}")
            return None

    def cleanup_temp_files(self) -> None:
        """Remove all temporary files created by this input."""
        import os as _os
        for path in self._temp_files:
            try:
                _os.unlink(path)
            except Exception:
                pass
        self._temp_files.clear()

    def keyPressEvent(self, event: Optional[QKeyEvent]) -> None:
        if event and event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            self.send_requested.emit()
        elif event and event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
            super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)


class AsyncWorker(QObject):
    """Runs an asyncio event loop in a background QThread."""

    def __init__(self):
        super().__init__()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def start(self) -> None:
        """Run the asyncio event loop (called from the QThread)."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def stop(self) -> None:
        """Stop the event loop."""
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

    def submit(self, coro) -> Any:
        """Submit a coroutine to the background event loop. Returns a concurrent.futures.Future."""
        return asyncio.run_coroutine_threadsafe(coro, self._loop)

    def cancel_all(self) -> None:
        """Cancel all running tasks (thread-safe)."""
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._cancel_tasks)

    def _cancel_tasks(self) -> None:
        """Cancel all tasks (must run on the event loop thread)."""
        for task in asyncio.all_tasks(self._loop):
            task.cancel()


class ChatWidget(QWidget):
    """Main chat interface with message history and input area."""

    conversation_updated = pyqtSignal()

    def __init__(
        self,
        model_manager: ModelManager,
        tool_registry: ToolRegistry,
        conversation: Conversation,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.model_manager = model_manager
        self.tool_registry = tool_registry
        self.conversation = conversation
        self._attached_files: List[str] = []
        self._is_processing = False
        self._cancel_requested = False

        # Audio recording & TTS
        self._audio_recorder = AudioRecorder()
        self._transcriber = Transcriber()
        self._tts_engine = TTSEngine()

        # Background worker for async AI processing
        self._async_worker = AsyncWorker()
        self._async_thread = QThread(self)
        self._async_worker.moveToThread(self._async_thread)
        self._async_thread.started.connect(self._async_worker.start)
        self._async_thread.finished.connect(self._async_worker.stop)
        self._async_thread.start()

        self._init_ui()
        self._connect_signals()

        # Cross-thread call queue (background thread → main thread)
        self._main_queue: queue.Queue = queue.Queue()
        self._queue_timer = QTimer(self)
        self._queue_timer.timeout.connect(self._flush_main_queue)
        self._queue_timer.start(30)

    def cleanup(self) -> None:
        """Stop the background thread. Call this before destroying the widget."""
        self._cancel_requested = True
        self._queue_timer.stop()
        self._async_worker.cancel_all()
        self._async_worker.stop()
        self._async_thread.quit()
        if not self._async_thread.wait(5000):
            print("Warning: worker thread did not finish in time")
        self.message_input.cleanup_temp_files()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Scroll area for messages
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #1a1a1a;
            }
            QScrollBar:vertical {
                background: #1a1a1a;
                width: 8px;
            }
            QScrollBar::handle:vertical {
                background: #444;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)

        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.messages_layout.setSpacing(4)
        self.messages_layout.setContentsMargins(12, 12, 12, 12)
        self.messages_container.setStyleSheet("background-color: #1a1a1a;")

        self.scroll_area.setWidget(self.messages_container)
        layout.addWidget(self.scroll_area, 1)

        # Welcome overlay (shown when chat is empty)
        self.welcome_label = QLabel()
        self._show_welcome()

        # Thinking indicator
        self.thinking_label = QLabel("  \u23F3 Assistant is thinking...")
        self.thinking_label.setVisible(False)
        self.thinking_label.setStyleSheet("""
            QLabel {
                background-color: #1e2a1e;
                color: #81c784;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
                border-top: 1px solid #2a3a2a;
            }
        """)
        layout.addWidget(self.thinking_label)

        # File attachments bar
        self.attachments_bar = QFrame()
        self.attachments_bar.setVisible(False)
        self.attachments_bar.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border-top: 1px solid #333;
                padding: 4px 12px;
            }
        """)
        attachments_layout = QHBoxLayout(self.attachments_bar)
        attachments_layout.setContentsMargins(8, 4, 8, 4)
        self.attachments_label = QLabel()
        self.attachments_label.setStyleSheet("color: #aaa; font-size: 12px;")
        attachments_layout.addWidget(self.attachments_label)
        attachments_layout.addStretch()
        self.clear_attachments_btn = QPushButton("Clear")
        self.clear_attachments_btn.setFixedSize(60, 24)
        self.clear_attachments_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #555;
                border-radius: 4px;
                color: #aaa;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #3a3a3a;
                color: #f77;
            }
        """)
        self.clear_attachments_btn.clicked.connect(self._clear_attachments)
        attachments_layout.addWidget(self.clear_attachments_btn)
        layout.addWidget(self.attachments_bar)

        # Input area
        input_container = QFrame()
        input_container.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-top: 1px solid #333;
                padding: 8px;
            }
        """)
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(8, 4, 8, 4)

        self.attach_btn = QPushButton("\U0001f4ce")
        self.attach_btn.setFixedSize(40, 40)
        self.attach_btn.setToolTip("Attach files (images, documents)")
        self.attach_btn.setStyleSheet("""
            QPushButton {
                background: #333;
                border: 1px solid #555;
                border-radius: 8px;
                font-size: 18px;
            }
            QPushButton:hover {
                background: #444;
                border-color: #4fc3f7;
            }
        """)
        input_layout.addWidget(self.attach_btn)

        self.audio_btn = QPushButton("🎤")
        self.audio_btn.setFixedSize(40, 40)
        self.audio_btn.setToolTip("Record audio message")
        self.audio_btn.setStyleSheet("""
            QPushButton {
                background: #333;
                border: 1px solid #555;
                border-radius: 8px;
                font-size: 18px;
            }
            QPushButton:hover {
                background: #444;
                border-color: #4fc3f7;
            }
        """)
        input_layout.addWidget(self.audio_btn)

        self.tts_btn = QPushButton("🔊")
        self.tts_btn.setFixedSize(40, 40)
        self.tts_btn.setToolTip("Stop audio playback")
        self.tts_btn.setStyleSheet("""
            QPushButton {
                background: #333;
                border: 1px solid #555;
                border-radius: 8px;
                font-size: 18px;
            }
            QPushButton:hover {
                background: #444;
                border-color: #4fc3f7;
            }
        """)
        input_layout.addWidget(self.tts_btn)

        self.message_input = MessageInput()
        input_layout.addWidget(self.message_input, 1)

        self.send_btn = QPushButton("Send")
        self.send_btn.setFixedSize(80, 40)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #4fc3f7;
                border: none;
                border-radius: 8px;
                color: #000;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #29b6f6;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
        """)

        self.stop_btn = QPushButton("\u25a0 Stop")
        self.stop_btn.setFixedSize(80, 40)
        self.stop_btn.setVisible(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #e53935;
                border: none;
                border-radius: 8px;
                color: #fff;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #c62828;
            }
        """)

        input_layout.addWidget(self.send_btn)
        input_layout.addWidget(self.stop_btn)

        layout.addWidget(input_container)

    def _connect_signals(self) -> None:
        self.send_btn.clicked.connect(self._on_send)
        self.message_input.send_requested.connect(self._on_send)
        self.message_input.files_pasted.connect(self._on_files_pasted)
        self.attach_btn.clicked.connect(self._on_attach_files)
        self.stop_btn.clicked.connect(self._on_stop)
        self.audio_btn.clicked.connect(self._on_audio_toggle)
        self.tts_btn.clicked.connect(self._on_tts_stop)

    def _on_tts_stop(self) -> None:
        """Stop current TTS playback."""
        self._tts_engine.stop()

    def _on_audio_toggle(self) -> None:
        """Toggle audio recording on/off."""
        if self._audio_recorder.is_recording:
            self._audio_recorder.stop()
            self.audio_btn.setStyleSheet("""
                QPushButton {
                    background: #333;
                    border: 1px solid #555;
                    border-radius: 8px;
                    font-size: 18px;
                }
                QPushButton:hover {
                    background: #444;
                    border-color: #4fc3f7;
                }
            """)
        else:
            self._audio_recorder.start(on_stop=self._on_audio_ready)
            self.audio_btn.setStyleSheet("""
                QPushButton {
                    background: #c62828;
                    border: 1px solid #e53935;
                    border-radius: 8px;
                    font-size: 18px;
                    color: #fff;
                }
                QPushButton:hover {
                    background: #e53935;
                }
            """)
            self.audio_btn.setText("⏹")

    def _on_audio_ready(self, audio_path: str) -> None:
        """Called when recording is complete — transcribe (bg) then send."""
        _threading.Thread(
            target=self._transcribe_and_send,
            args=(audio_path,),
            daemon=True,
        ).start()

    def _transcribe_and_send(self, audio_path: str) -> None:
        """Run transcription in background thread, dispatch Qt work to main thread."""
        text = self._transcriber.transcribe(audio_path)
        self._run_in_main(self._finish_audio, text, audio_path)

    def _finish_audio(self, text: str, audio_path: str) -> None:
        """Handle transcription result on main thread."""
        self.audio_btn.setText("🎤")
        self.audio_btn.setStyleSheet("""
            QPushButton {
                background: #333;
                border: 1px solid #555;
                border-radius: 8px;
                font-size: 18px;
            }
            QPushButton:hover {
                background: #444;
                border-color: #4fc3f7;
            }
        """)
        try:
            _os.unlink(audio_path)
        except Exception:
            pass
        if text and not text.startswith("[Error"):
            self.message_input.setPlainText(text)
            self._on_send()

    def _on_stop(self) -> None:
        """Stop the current AI generation."""
        self._cancel_requested = True
        self._async_worker.cancel_all()
        self.thinking_label.setText("  Stopping...")

    def _remove_welcome(self) -> None:
        """Remove the welcome label if present."""
        if self.welcome_label and self.welcome_label.parent():
            self.welcome_label.deleteLater()
            self.welcome_label = None

    def _on_files_pasted(self, files: List[str]) -> None:
        """Handle files pasted from clipboard."""
        for f in files:
            if f not in self._attached_files:
                self._attached_files.append(f)
        self._update_attachments_bar()

    def _on_attach_files(self) -> None:
        """Open file dialog to attach files."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Attach Files",
            "",
            "Supported Files (*.jpg *.jpeg *.png *.gif *.webp *.bmp *.txt *.md *.py *.js *.ts *.html *.css *.json *.xml *.pdf *.csv);;All Files (*)",
        )
        for f in files:
            if f not in self._attached_files:
                self._attached_files.append(f)
        self._update_attachments_bar()

    def _update_attachments_bar(self) -> None:
        """Update the attachments bar visibility and content."""
        if self._attached_files:
            self.attachments_bar.setVisible(True)
            names = [Path(f).name for f in self._attached_files]
            self.attachments_label.setText(f"Attached ({len(names)}): {', '.join(names[:3])}")
            if len(names) > 3:
                self.attachments_label.setText(
                    self.attachments_label.text() + f" +{len(names) - 3} more"
                )
        else:
            self.attachments_bar.setVisible(False)

    def _show_error(self, text: str) -> None:
        """Display an error message in the chat."""
        widget = MessageWidget("system", text)
        self.messages_layout.addWidget(widget)
        self._scroll_to_bottom()

    def _clear_attachments(self) -> None:
        """Clear all attached files."""
        self._attached_files.clear()
        self._update_attachments_bar()

    def _on_send(self) -> None:
        """Handle send button press or Enter key."""
        if self._is_processing:
            return

        text = self.message_input.toPlainText().strip()
        if not text and not self._attached_files:
            return

        self._remove_welcome()
        self._send_message(text)

    def _send_message(self, text: str) -> None:
        """Send a message and process the response."""
        files = list(self._attached_files)
        user_widget = MessageWidget("user", text, files=files)
        self.messages_layout.addWidget(user_widget)
        self._scroll_to_bottom()

        self.conversation.add("user", text, files=files)
        self.conversation_updated.emit()

        self.message_input.clear()
        self._clear_attachments()

        self._set_processing_state(True)

        self._run_async(self._process_response())

    def send_as_user(self, text: str) -> None:
        """Public method to send a message as if the user typed it."""
        if self._is_processing:
            return
        self.message_input.setPlainText(text)
        self._on_send()

    # ---- Thread-safe helpers for cross-thread GUI operations ----

    async def _request_assistant_widget(self) -> MessageWidget:
        """Create an assistant message widget in the main thread and return it."""
        import concurrent.futures
        future: concurrent.futures.Future = concurrent.futures.Future()

        def _tts_cb(text: str) -> None:
            self._tts_engine.speak(text)

        def _on_main() -> None:
            try:
                if self._cancel_requested:
                    future.set_result(None)
                    return
                widget = MessageWidget("assistant", "", is_streaming=True, on_tts=_tts_cb)
                self.messages_layout.addWidget(widget)
                self._scroll_to_bottom()
                future.set_result(widget)
            except Exception as e:
                future.set_exception(e)

        self._run_in_main(_on_main)
        return await asyncio.wrap_future(future)

    async def _request_confirm(self, tool_name: str, args: dict) -> bool:
        """Show confirmation dialog in the main thread and return result."""
        import concurrent.futures
        future: concurrent.futures.Future = concurrent.futures.Future()

        def _on_main() -> None:
            try:
                if self._cancel_requested:
                    future.set_result(False)
                    return
                command_preview = args.get("command") or args.get("code") or ""
                dialog = _ConfirmDialog(command_preview, tool_name, None)
                future.set_result(bool(dialog.exec()))
            except Exception as e:
                future.set_exception(e)

        self._run_in_main(_on_main)
        return await asyncio.wrap_future(future)

    def _add_tool_widget(self, role: str, content: str) -> None:
        """Schedule a tool result widget addition in the main thread."""
        self._run_in_main(self._do_add_tool_widget, role, content)

    def _do_add_tool_widget(self, role: str, content: str) -> None:
        widget = MessageWidget(role, content)
        self.messages_layout.addWidget(widget)
        self._scroll_to_bottom()

    def _add_conv_message(self, msg: Message) -> None:
        """Add a message to the conversation and emit signal (main thread)."""
        self.conversation.add_message(msg)
        self.conversation_updated.emit()

    def _append_stream(self, widget: MessageWidget, chunk: str) -> None:
        """Append streaming text and scroll (main thread)."""
        widget.append_stream_text(chunk)
        self._scroll_to_bottom()

    # ---- Async processing ----

    async def _process_response(self) -> None:
        """Process the conversation through the AI model with tool support."""
        provider_name = self.model_manager.config.active_provider
        provider, error = self.model_manager.get_provider()
        if error:
            message = format_api_error(error, provider_name)
            self._run_in_main(self._show_error, message)
            return

        tools = []
        for tool in self.tool_registry.get_all():
            if not self._get_parent_window_config().is_tool_enabled(tool.name):
                continue
            tools.append(tool)

        messages = self.conversation.to_messages()

        assistant_widget = await self._request_assistant_widget()
        if assistant_widget is None:
            return

        max_tool_rounds = 10
        current_round = 0

        def on_stream(chunk: str) -> None:
            self._run_in_main(self._append_stream, assistant_widget, chunk)

        while current_round < max_tool_rounds:
            current_round += 1

            try:
                result = await provider.chat(
                    messages,
                    tools=[t.to_definition() for t in tools] if tools else None,
                    on_stream=on_stream if current_round == 1 else None,
                )
            except asyncio.CancelledError:
                return
            except Exception as e:
                error_text = format_api_error(str(e), provider_name)
                self._run_in_main(assistant_widget.set_content, error_text)
                self._add_conv_message(Message(role="assistant", content=error_text))
                break

            if result.finish_reason == "error":
                error_text = format_api_error(result.content, provider_name)
                self._run_in_main(assistant_widget.set_content, error_text)
                self._add_conv_message(Message(role="assistant", content=error_text))
                break

            if result.tool_calls:
                self._add_conv_message(Message(
                    role="assistant",
                    content=result.content,
                    tool_calls=result.tool_calls,
                ))

                for tc in result.tool_calls:
                    tool_name = tc["function"]["name"]
                    try:
                        args = json.loads(tc["function"]["arguments"])
                    except json.JSONDecodeError:
                        args = {}

                    confirm = tool_name in ("execute_command", "execute_python")
                    if confirm:
                        confirmed = await self._request_confirm(tool_name, args)
                        if not confirmed:
                            tool_result = (
                                f"[The {tool_name} tool was NOT executed. "
                                f"The user cancelled it from the confirmation dialog.]\n\n"
                                f"The user chose to cancel the {tool_name} execution."
                            )
                            self._add_conv_message(Message(
                                role="tool",
                                content=tool_result,
                                tool_call_id=tc.get("id", ""),
                                name=tool_name,
                            ))
                            self._add_tool_widget("tool", f"**Cancelled:** {tool_name}")
                            continue

                    if self._cancel_requested:
                        return

                    tool_result = await self.tool_registry.execute(tool_name, **args)

                    tool_result_with_note = (
                        f"[The {tool_name} tool was executed automatically by the system. "
                        f"The following is the actual output/result, NOT provided by the user.]\n\n"
                        f"{tool_result}"
                    )

                    self._add_conv_message(Message(
                        role="tool",
                        content=tool_result_with_note,
                        tool_call_id=tc.get("id", ""),
                        name=tool_name,
                    ))
                    self._add_tool_widget("tool", tool_result)

                messages = self.conversation.to_messages()
            else:
                self._run_in_main(assistant_widget.set_content, result.content)
                self._run_in_main(self._set_assistant_done, assistant_widget)
                self._add_conv_message(Message(
                    role="assistant",
                    content=result.content,
                ))
                break
        else:
            error_text = "Error: Maximum tool call rounds reached."
            self._run_in_main(assistant_widget.set_content, error_text)
            self._add_conv_message(Message(role="assistant", content=error_text))

    @staticmethod
    def _set_assistant_done(widget: MessageWidget) -> None:
        """Mark assistant widget as done streaming (main thread)."""
        widget.is_streaming = False

    def _set_processing_state(self, processing: bool) -> None:
        """Enable/disable input during processing."""
        self._is_processing = processing
        self.message_input.setEnabled(not processing)
        self.send_btn.setVisible(not processing)
        self.stop_btn.setVisible(processing)
        self.thinking_label.setVisible(processing)
        if processing:
            self._cancel_requested = False
            self.thinking_label.setText("  \u23F3 Assistant is thinking...")

    def _scroll_to_bottom(self) -> None:
        """Scroll the message area to the bottom."""
        QTimer.singleShot(50, self._do_scroll_to_bottom)

    def _do_scroll_to_bottom(self) -> None:
        """Inner scroll to bottom (safe to call after widget deletion)."""
        try:
            self.scroll_area.verticalScrollBar().setValue(
                self.scroll_area.verticalScrollBar().maximum()
            )
        except RuntimeError:
            pass

    def _get_parent_window_config(self):
        """Get config from parent MainWindow."""
        parent = self.parent()
        while parent:
            if hasattr(parent, "config"):
                return parent.config
            parent = parent.parent()
        from core.config import Config
        return Config()

    def _flush_main_queue(self) -> None:
        """Process the cross-thread call queue in the main thread (called by QTimer)."""
        while True:
            try:
                item = self._main_queue.get_nowait()
                func, args = item
                func(*args)
            except queue.Empty:
                break
            except Exception as e:
                print(f"Error in queued call {func}: {e}")

    def _run_async(self, coro) -> None:
        """Submit coroutine to background worker without blocking the GUI."""

        async def _wrapper() -> None:
            try:
                await coro
            except asyncio.CancelledError:
                pass
            finally:
                self._run_in_main(self._set_processing_state, False)

        self._async_worker.submit(_wrapper())

    def _run_in_main(self, func: Callable, *args: Any) -> None:
        """Schedule a function to run in the main GUI thread via queue."""
        self._main_queue.put((func, args))

    def load_conversation(self, conversation: Conversation) -> None:
        """Load a different conversation into the chat view."""
        self.conversation = conversation
        self._rebuild_messages()

    def _rebuild_messages(self) -> None:
        """Rebuild the message display from conversation history."""
        # Clear existing widgets immediately (not via deleteLater)
        while self.messages_layout.count():
            item = self.messages_layout.takeAt(0)
            if item and item.widget():
                item.widget().setParent(None)

        if not self.conversation.entries:
            self._show_welcome()
            self._scroll_to_bottom()
            return

        def _tts_cb(text: str) -> None:
            self._tts_engine.speak(text)

        for entry in self.conversation.entries:
            widget = MessageWidget(
                entry.role,
                entry.content,
                files=entry.files,
                on_tts=_tts_cb if entry.role == "assistant" else None,
            )
            self.messages_layout.addWidget(widget)

        self._scroll_to_bottom()

    def _show_welcome(self) -> None:
        """Show the welcome label in the current layout."""
        self.welcome_label = QLabel()
        self.welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.welcome_label.setWordWrap(True)
        username = _os.environ.get("USER", "user")
        self.welcome_label.setText(
            f'<div style="font-size: 28px; color: #555; margin-top: 80px;">'
            f"Bienvenido {username}"
            f'</div>'
            f'<div style="font-size: 14px; color: #444;">'
            f"Escribe un mensaje o usa los botones de la barra lateral para comenzar"
            f"</div>"
        )
        self.messages_layout.addWidget(self.welcome_label)
        self.messages_layout.setAlignment(self.welcome_label, Qt.AlignmentFlag.AlignCenter)



    def clear_chat(self) -> None:
        """Clear the chat display and conversation."""
        self.conversation.clear()
        self._rebuild_messages()


class _ConfirmDialog(QDialog):
    """Confirmation dialog for command execution."""

    def __init__(self, command: str, tool_name: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Confirm Execution")
        self.setMinimumWidth(500)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 13px;
            }
            QTextEdit {
                background-color: #2a2a2a;
                border: 1px solid #555;
                border-radius: 6px;
                padding: 10px;
                color: #a8d8ea;
                font-family: 'Courier New', monospace;
                font-size: 13px;
            }
            QPushButton {
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-weight: bold;
                font-size: 13px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(QLabel(f"The AI wants to execute this {tool_name.replace('_', ' ')}:"))

        cmd_display = QTextEdit()
        cmd_display.setReadOnly(True)
        cmd_display.setPlainText(command)
        cmd_display.setMinimumHeight(80)
        cmd_display.setMaximumHeight(200)
        layout.addWidget(cmd_display)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #444;
                color: #ccc;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)
        cancel_btn.clicked.connect(self.reject)

        accept_btn = QPushButton("Execute")
        accept_btn.setStyleSheet("""
            QPushButton {
                background-color: #4fc3f7;
                color: #000;
            }
            QPushButton:hover {
                background-color: #29b6f6;
            }
        """)
        accept_btn.clicked.connect(self.accept)
        accept_btn.setDefault(True)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(accept_btn)
        layout.addLayout(btn_layout)
