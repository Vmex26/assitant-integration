# AI Assistant Integrer — AGENTS.md

## Workflow
- Plan first, implement step by step, verify each phase.
- **Commit per phase** — after all bugs/features in a phase are verified, commit. Never mid-phase.
- **6-attempt limit**: if one bug/feature fails 6 distinct times, create `ERROR-<description>.md` documenting everything tried and stop.

## Run & Verify
```bash
./run.sh                          # Launch GUI
source venv/bin/activate && python3 main.py
```

### Lint, typecheck, test
```bash
source venv/bin/activate && ruff check . && ruff format . --check && basedpyright . && python -m pytest tests/ -v
```

## Architecture
- **Cross-thread dispatch**: All GUI updates from background threads must be dispatched via `self._run_in_main(func, *args)`.
- **Conversation Management**: `Conversation` has `threading.Lock` (`_lock`) — always acquire when reading/writing from non-main threads.
- **Audio (core/audio.py)**:
    - **`AudioRecorder`**: `sounddevice` at 16 kHz. Stops on silence.
    - **`Transcriber`**: `faster_whisper` (model `small`).
    - **`TTSEngine`**: `edge-tts`.
- **Providers (core/providers/)**: Registered in `model_manager.py`. `gemini` requires `thought_signature`. `openai_compatible` does NOT support images.
- **Tools (core/tools/)**: Registered in `main_window.py:_init_tools`.
    - **Smart Sudo Protocol**: If sudo needed: explain risk, ask confirmation (`user_confirmed: False` unless user explicitly requested `True`).
    - **SoftwareAssistantTool**: Unifies search/alternatives using `WebSearchTool` (dynamic/web-based).
    - **AUR Audit**: ALWAYS run `show_pkgbuild` before suggesting AUR install.

## Feature Tracking
- **Cuando el usuario comparte una idea**: escribirla en `IDEAS.md` con fecha y descripción.
- **Cuando el usuario pide una feature bien definida**: estructurarla y ponerla en `TODO_FEATURES.md` con el formato estándar (descripción, rationale, alcance, estado).
- **Recordatorio de ideas previas**: Al iniciar una conversación sobre un tema nuevo, si hay ideas relacionadas en `IDEAS.md` o `TODO_FEATURES.md`, mencionarlas.
- **Nunca poner ideas sueltas directamente en `TODO_FEATURES.md`**: primero van a `IDEAS.md`, y solo se promocionan cuando están bien definidas.

## Operational Gotchas
- **GUI Processes (Firefox, etc.)**: MUST use `command > /dev/null 2>&1 & disown`. NEVER omit redirection.
- **Voice Call Mode**:
    - Strictly plain text response, NO markdown.
    - Use `[END_CALL]` token ONLY when explicitly asked to terminate.
    - NEVER infer it's time to hang up based on context.
- **Qt Safety**: When accessing widgets from background threads, ALWAYS wrap with `try: ... except RuntimeError:` or verify `sipIsDeleted()`.
- **`_rebuild_messages`**: Use `takeAt(0)` + `setParent(None)` + `deleteLater()` for reliable widget removal.
- **`_scroll_to_bottom`**: Uses `QTimer.singleShot(50, self._do_scroll_to_bottom)` with `RuntimeError` guard.
- **`ConversationEntry`**: tool_calls serialized as JSON in SQLite, deserialized on load.
