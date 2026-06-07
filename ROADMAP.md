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
- [ ] Bug 8: `audio.py:64,92,132` — `_check_silence` sin lock, `TTSEngine._is_speaking` sin lock, temp file leak
- [ ] Bug 9: `storage.py:79` — itera `conv.entries` sin `conv._lock`
- [ ] Bug 10: `conversation.py:127` — `from_dict` añade entries sin lock
- [ ] Bug 11: `message_widget.py:35` — `_adjust_height` timer racea con `deleteLater()`
- [ ] Bug 12: `chat_widget.py:819` — `_rebuild_messages` deferred delete racea con streaming height adjustments

## Fase 2 — Medium/Low severity + mejoras
- [ ] Bug 13: `anthropic_provider.py:186-191` — código duplicado de image processing
- [ ] Bug 14: `system_panel.py:80` — primer CPU% siempre 0%
- [ ] Bug 15: `chat_widget.py:492` — orphan `QLabel()` en `_remove_welcome`
- [ ] Bug 16: `main_window.py:493,502` — `active_provider` seteado dos veces
- [ ] Bug 17: `settings_dialog.py:341` — Apply y OK muestran popup
- [ ] Bug 18: `chat_widget.py:592` — busy-wait con `asyncio.sleep(0.1)` en vez de `asyncio.Event()`
- [ ] Bug 19: `message_widget.py:37` — markdown roto entre chunks streaming

## Fase 3 — Feature: Verbosity/Debug parameter
- [ ] Añadir `verbose: bool` en `Config`
- [ ] Checkbox "Debug mode" en Settings → Interface
- [ ] Logger centralizado con `logging` module (INFO/DEBUG/ERROR)
- [ ] Reemplazar `print()` por `logger.debug()` / `logger.error()`
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
