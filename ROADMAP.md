# ROADMAP — AI Assistant Integrer

> Marca con `[x]` las fases completadas. Si llegas con contexto fresco, lee esto primero para saber dónde continuar.

---

## Fase 0 — Bugs críticos (crash garantizado)
- [x] Bug 1: `package_tools.py` — falta `import subprocess`
- [x] Bug 2: `chat_widget.py` — `_on_audio_ready` llamado desde hilo del silence checker (Qt thread safety)
- [x] Bug 3: `chat_widget.py` — `_flush_main_queue` sin try/except (mata el timer de 30ms)
- [x] Bug 4: `log_dialog.py` — thread reference race en doble fetch
- [x] Bug 5: `service_dialog.py` — thread reference race en doble load
- [x] Bug 6: `chat_widget.py` — `QTimer.singleShot` lambda use-after-free en scroll_area
- [x] Bug 7: `openai_provider.py` / `openai_compatible_provider.py` — `chunk` undefined en stream vacío

## Fase 1 — Thread safety + Qt hierarchy (high severity)
- [x] Bug 8: `audio.py` — `_check_silence` con lock, `TTSEngine._is_speaking` con `_speak_lock`, temp file cleanup en transcription thread
- [x] Bug 9: `storage.py:79` — itera `conv.entries` con `conv._lock`
- [x] Bug 10: `conversation.py:127` — `from_dict` añade entries con `conv._lock`
- [x] Bug 11: `message_widget.py:35` — `_adjust_height` con `sipIsDeleted()` check
- [x] Bug 12: `chat_widget.py:819` — `_rebuild_messages` con `setParent(None)` en vez de `deleteLater()`

## Fase 2 — Medium/Low severity + mejoras
- [x] Bug 13: `anthropic_provider.py` — eliminado código duplicado de image processing
- [x] Bug 14: `system_panel.py` — `interval=0` → `interval=0.1` para evitar 0% en primera lectura
- [x] Bug 15: `chat_widget.py` — `_remove_welcome` setea `None` en vez de `QLabel()` huérfano
- [x] Bug 16: `main_window.py` — eliminada línea redundante `active_provider` (seteado dos veces)
- [x] Bug 17: `settings_dialog.py` — popup movido de `_save_config` a `_on_apply` solo
- [x] Bug 18: `chat_widget.py` — `_request_assistant_widget`/`_request_confirm` usan `concurrent.futures.Future` + `asyncio.wrap_future` (sin busy-wait)
- [x] Bug 19: `message_widget.py` — `append_stream_text` re-renderea full content con `set_markdown` en vez de chunks independientes

## Fase 3 — Feature: Verbosity/Debug parameter
- [x] Añadir `verbose: bool` en `Config`
- [x] Checkbox "Debug mode" en Settings → Interface
- [x] Logger centralizado con `logging` module (INFO/DEBUG/ERROR)
- [x] Reemplazar `print()` por `logger.debug()` / `logger.error()`
- [ ] Panel de debug opcional (toggle con atajo)

## Fase 4 — Feature: faster-whisper
- [ ] Reemplazar `Transcriber` (Google Speech Recognition) por `faster_whisper.WhisperModel`
- [ ] Config: model size, device (CPU/CUDA/Auto), compute type en Settings
- [ ] Lazy-load del modelo en primer uso
- [ ] Transcription en background thread
- [ ] Añadir `faster-whisper` a `requirements.txt`
- [ ] Modelo default: `small` (mínimo viable para comandos/URLs)

## Fase 5 — Feature: Call Mode (desde cero)
- [ ] Bucle asyncio: speak → listen → transcribe (faster-whisper) → AI respond → TTS → loop
- [ ] Usar `asyncio.Event()` para espera no-bloqueante
- [ ] `sd.play()` no-bloqueante + timer poll para detectar fin
- [ ] Sin beeps ni estados de recording en call loop
- [ ] Simplificado respecto a versión revertida (sin `done_callback` complejo)
