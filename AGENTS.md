# AI Assistant Integrer — AGENTS.md

## Workflow Preference (Plan → Implement)
- **Preferred workflow**: Plan first, then implement step by step. Before making changes, outline what will be done and in what order. Implement one phase at a time, verify, then proceed.
- **Override**: If the user says "implement X, Y, Z all at once" or similar, proceed directly without planning — just warn once: "Preferimos planificar primero, pero voy directo como pides." The warning is advisory, not blocking.
- **Commit per phase**: After completing each phase (all bugs/features in that phase verified working), commit with a descriptive message. Do not commit mid-phase.
- **Stuck after 6 attempts**: If a single bug or feature cannot be fixed after 6 distinct attempts, stop completely. Create a file `ERROR-<description>.md` in the project root documenting: the error, all attempts made (what was tried and why it failed), and possible remaining solutions. Do not continue — wait for the user.

## Run & Verify
```bash
./run.sh                          # Launch GUI (requires display)
source venv/bin/activate && python3 main.py
```

### Pre-commit verification (run before each commit)
```bash
source venv/bin/activate && ruff check . && ruff format . --check && basedpyright .
```

### Run tests (when pytest is configured)
```bash
source venv/bin/activate && python -m pytest tests/ -v
```

- After each phase, test: (1) app starts without crash, (2) send a text message, (3) verify no console errors.

## Architecture Overview

### Cross-thread dispatch
- **`AsyncWorker(QObject)`** moved to `QThread` runs `asyncio.run_forever()` in a background loop.
- **`_run_in_main(func, *args)`** puts a callable on `queue.Queue`; a `QTimer(30ms)` fires `_flush_main_queue` in the GUI thread to drain it.
- **`_run_async(coro)`** submits a coroutine to the worker and automatically calls `_set_processing_state(False)` when done.
- `_flush_main_queue` catches `queue.Empty` and generic exceptions — errors in queued calls are logged but don't crash the timer.

### Conversation & Storage
- **`Conversation`** has a `threading.Lock` (`_lock`). Always acquire it when reading/writing entries from non-main threads.
- **Empty conversations are never persisted** — `_save_active_conversation` skips `len(conv) == 0`.
- Storage is SQLite with WAL mode. `conversations` + `messages` tables.

### Audio (core/audio.py)
- **`AudioRecorder`**: `sounddevice.InputStream` at 16 kHz, float32. Silence detection via background thread (1.5s timeout, RMS threshold 0.01). Stops manually via `stop()`.
- **`Transcriber`**: Uses `speech_recognition.Recognizer.recognize_google()` (free Google API, requires internet). Not faster-whisper.
- **`TTSEngine`**: `edge-tts.Communicate.save()` inside a daemon thread using `asyncio.run()`. `sd.play()` + `sd.wait()` for playback. `sd.stop()` stops all sounddevice streams.
- `_on_audio_ready` (recording callback) now dispatches transcription to a daemon thread, then Qt updates to the main thread via `_run_in_main` — thread-safe.

### Providers (core/providers/)
Each implements `BaseProvider.chat(messages, tools, on_stream)`:
- **Gemini**: Uses `google.genai` SDK. `thought_signature` stored/restored as `base64` bytes on `Part`. Must use `part.function_call.id` (not `.name`) for tool call IDs in streaming.
- **Ollama**: Creates a new `httpx.AsyncClient` per `chat()` call (no connection pooling).
- **Anthropic**: Uses `AsyncAnthropic` with `client.messages.stream()` context manager.
- **OpenAI / OpenAI Compatible**: Uses `AsyncOpenAI`. Compatible provider `supports_images()` is `False`.

### Tools (core/tools/)
- Only `execute_command` and `execute_python` show confirmation dialogs.
- `execute_command` runs with `async def` using `asyncio.create_subprocess_shell`.
- `sudo` commands trigger KDE/zenity password dialog (handled by sudo itself, not by code).
- AUR package audit: always run `show_pkgbuild` before suggesting AUR install (check maintainer, votes, source URLs, suspicious patterns).

### UI Patterns
- **MessageWidget**: `QTextBrowser` with custom markdown→HTML conversion. `_adjust_height()` via `QTimer.singleShot(0)` to fit content after layout.
- **`_rebuild_messages`**: Clears all items from `messages_layout` with `takeAt(0)` + `setParent(None)` (immediate deletion), then rebuilds from `conversation.entries`.
- **`_remove_welcome`**: Calls `deleteLater()` on the welcome label, replaces with empty `QLabel()`.
- **`conversation_updated`** pyqtSignal connected to `_save_active_conversation` in MainWindow.

## Gotchas & Quirks
- `sd.play()` is non-blocking; `sd.wait()` blocks. `_play_beep` in `chat_widget` calls `sd.play()` only (no wait).
- `edge-tts.Communicate.save()` is async — called with `asyncio.run()` inside a daemon thread.
- `QTimer.singleShot(0, callback)` runs the callback in the CALLING thread, not the main thread. Our cross-thread dispatch always uses the queue.
- `_scroll_to_bottom` uses `QTimer.singleShot(50, self._do_scroll_to_bottom)` with a try/except RuntimeError guard to survive widget deletion.
- Message `name` field is critical for Gemini tool result matching after conversation reload.
- `ConversationEntry` tool_calls are serialized as JSON in SQLite, deserialized on load.
- The system prompt is dynamically built from OS info, config language, and safety rules.
- Language is configured in Settings (`es`/`en`), not auto-detected. System prompt instructs AI to respond in that language.
