# AI Assistant Integrer — AGENTS.md

## Workflow
- Plan first, implement step by step, verify each phase. If user says "do X,Y,Z all at once", warn once then proceed directly.
- **Commit per phase** — after all bugs/features in a phase are verified, commit. Never mid-phase.
- **6-attempt limit**: if one bug/feature fails 6 distinct times, create `ERROR-<description>.md` in project root documenting everything tried and remaining options, then stop.

## Run & Verify
```bash
./run.sh                          # Launch GUI (requires display)
source venv/bin/activate && python3 main.py
```

### Lint, typecheck, test
```bash
source venv/bin/activate && pre-commit run --all-files
```
Equivalent manual check:
```bash
source venv/bin/activate && ruff check . && ruff format . --check && basedpyright . && python -m pytest tests/ -v
```
- After each phase: app starts without crash, send a text message, verify no console errors.

## Architecture

### Cross-thread dispatch
- **`AsyncWorker(QObject)`** on `QThread` runs `asyncio.run_forever()` in a background loop.
- **`_run_in_main(func, *args)`** puts `(func, args)` on `queue.Queue`. A `QTimer(30ms)` calls `_flush_main_queue` in the GUI thread to drain it. Errors in queued calls are logged but don't crash the timer.
- **`_run_async(coro)`** submits to worker, auto-sets `_set_processing_state(False)` on completion.
- **`_run_async_call(coro)`** same but for voice call mode — does NOT reset processing state.

### Conversation & Storage
- `Conversation` has `threading.Lock` (`_lock`) — always acquire when reading/writing from non-main threads.
- Empty conversations are never persisted (guard in `_save_active_conversation`).
- SQLite WAL mode. Tables: `conversations` + `messages` (tool_calls/files as JSON).

### Audio (core/audio.py)
- **`AudioRecorder`**: `sounddevice.InputStream` at 16 kHz, float32. Silence detection in daemon thread (1.5s timeout, RMS threshold 0.01). Stops via `stop()` or auto on silence. Saves WAV to temp file, calls `on_stop(path)` callback.
- **`Transcriber`**: Uses **`faster_whisper.WhisperModel`** (local, NOT Google STT). Default model `small`, lazy-loaded on first call. Device/compute auto-detects CUDA. `transcribe(path, language="es")` returns text or None.
- **`TTSEngine`**: `edge-tts.Communicate.save()` in daemon thread via `asyncio.run()`. `sd.play()` + `sd.wait()` for playback. `sd.stop()` stops all sounddevice streams.
- `_on_audio_ready` recording callback dispatches transcription to a daemon thread, then Qt update via `_run_in_main`.
- **Voice call mode**: `_process_call_loop` — record → transcribe → AI → TTS → repeat loop. Starts from `_on_call_button` in chat_widget. Adds special system prompt instructions (no markdown, no sudo, `[END_CALL]` token).

### Providers (core/providers/)
Each implements `BaseProvider.chat(messages, tools, on_stream)`:
| Key | Class | SDK | Images |
|-----|-------|-----|--------|
| `openai` | `OpenAIProvider` | `AsyncOpenAI` | Yes |
| `anthropic` | `AnthropicProvider` | `AsyncAnthropic` | Yes |
| `ollama` | `OllamaProvider` | `httpx.AsyncClient` (new per call) | Yes |
| `gemini` | `GeminiProvider` | `google.genai` | Yes |
| `openai_compatible` | `OpenAICompatibleProvider` | `AsyncOpenAI` | **No** |

Quirks:
- Gemini: `thought_signature` stored/restored as `base64` bytes on `Part`. Use `part.function_call.id` (not `.name`) for tool call IDs in streaming.
- Message `name` field is critical for Gemini tool result matching after conversation reload.
- Ollama creates new `httpx.AsyncClient` per `chat()` — no connection pooling.
- Anthropic uses `client.messages.stream()` context manager.
- `model_manager.py` — registry pattern: `register_provider(name, class)` for plugins, lazy singleton instantiation.

### Tools (core/tools/)
Registered in `main_window.py:_init_tools` — 12 tools:
```
file:      read_file, write_file, list_directory
command:   execute_command, execute_python
search:    glob_search, content_search
web:       web_fetch, web_search, download_file
package:   search_package, show_pkgbuild
```
- Only `execute_command` and `execute_python` show confirmation dialogs.
- `execute_command` uses `asyncio.create_subprocess_shell`.
- `sudo` triggers KDE/zenity password dialog (handled by sudo, not by code).
- **AUR package audit**: always run `show_pkgbuild` before suggesting AUR install (check maintainer, votes, source URLs, suspicious patterns).
- Tools are individually enable/disable-able in Settings.
- Max 10 tool call rounds per message.

### System prompt
Dynamically built in `MainWindow._default_system_prompt()` from OS info, kernel, CPU, memory, desktop, shell, config language. Language is `es`/`en` (from Settings), not auto-detected. System prompt includes safety rules and capability descriptions.

### GUI files (gui/)
| File | Purpose |
|------|---------|
| `main_window.py` | Window, menus, sidebar, conversation list, tool registration |
| `chat_widget.py` | Chat area, message input, streaming, audio recording, voice call loop, cross-thread dispatch |
| `message_widget.py` | Per-message bubble with custom markdown→HTML rendering, copy/speak buttons |
| `settings_dialog.py` | 3-tab settings (Providers, Tools, Appearance) |
| `system_panel.py` | Sidebar panel with CPU/RAM/Disk progress bars + temp (updates every 5s) |
| `service_dialog.py` | systemd service manager (list/start/stop/restart/enable/disable) |
| `log_dialog.py` | journalctl log analyzer with presets; "Send to AI" emits `log_ready` signal |

### core/logger.py
Centralized `logging` module. `get_logger(name)` returns child logger. `set_verbose(bool)` toggles INFO↔DEBUG. All console output uses this.

### Testing
- `tests/` dir with conftest.py and per-module test files.
- Run with: `python -m pytest tests/ -v` (also runs in pre-commit hook).

## Gotchas & Quirks
- `sd.play()` is non-blocking; `sd.wait()` blocks. `_play_beep` in chat_widget calls `sd.play()` only (no wait).
- `edge-tts.Communicate.save()` is async — called with `asyncio.run()` inside a daemon thread.
- `QTimer.singleShot(0, callback)` runs in the CALLING thread, not the main thread. Cross-thread dispatch always uses the queue.
- `_scroll_to_bottom` uses `QTimer.singleShot(50, self._do_scroll_to_bottom)` with try/except RuntimeError guard to survive widget deletion.
- `_rebuild_messages` uses `takeAt(0)` + `setParent(None)` (immediate deletion), not `deleteLater()`.
- `_remove_welcome` calls `deleteLater()` then replaces with empty `QLabel()`.
- `ConversationEntry` tool_calls serialized as JSON in SQLite, deserialized on load.
- `pyproject.toml` targets Python 3.14. Basedpyright configured with relaxed PyQt6 stubs (several `report*` set to `"warning"`).
- System prompt is dynamically built from OS info, config language, and safety rules.
- Requirements include `faster-whisper` (not `SpeechRecognition`).
