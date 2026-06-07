---
name: call-mode-debug
description: Workflow para diagnosticar y reparar el modo de llamada por voz. Usar cuando el modo llamada esté roto, bloqueado, sin audio, sin respuesta de la IA, o con comportamiento inesperado. Aplicar ante cualquier error relacionado con sounddevice, edge-tts, AudioRecorder, TTSEngine, _process_call_loop, _call_active, transcripción, o el ciclo record→transcribe→AI→TTS. También usar si el agente necesita entender cómo funciona el modo llamada antes de modificar esa parte del código.
---

# Call Mode Debug Skill

## Arquitectura del modo llamada

Flujo completo iniciado desde `chat_widget.py`:

```
_on_call_button → _run_async_call(_process_call_loop)
                           ↓
              [record → transcribe → AI → TTS → repeat]
```

**Diferencia crítica**: `_run_async_call` (usado en call mode) **NO resetea** `_set_processing_state(False)` al terminar — a diferencia de `_run_async`. Esto es intencional.

## Variables de estado a verificar primero

```python
# En chat_widget.py:
_call_active           # bool — ¿está el modo llamada activo?
_audio_recorder.is_recording   # bool — ¿AudioRecorder capturando?
_tts_engine.is_speaking        # bool — ¿TTS reproduciendo audio?
```

Si alguna de estas está en estado inconsistente con lo que debería estar pasando, ahí está el problema.

## Gotchas críticos del audio

```python
sd.play()    # NO BLOQUEANTE — el código sigue ejecutándose inmediatamente
sd.wait()    # bloqueante — espera a que termine la reproducción
sd.stop()    # detiene TODOS los streams de sounddevice (TTS + beep + grabación)
```

- `TTSEngine` usa `sd.play()` + `sd.wait()` → correcto, espera a que termine
- `_play_beep` en chat_widget usa solo `sd.play()` → intencional, no espera
- `edge-tts.Communicate.save()` es async — se llama con `asyncio.run()` dentro de un daemon thread

**Bug frecuente**: si algo llama `sd.stop()` mientras TTS está reproduciendo, corta el audio y puede dejar `_tts_engine.is_speaking` en True si no se maneja el callback.

## Cross-thread en call mode

El loop corre en el `AsyncWorker` (background thread). Para actualizar la UI:
- Usar `_run_in_main(func, *args)` — pone la llamada en `queue.Queue`
- El `QTimer` de 30ms en el hilo principal drena la cola con `_flush_main_queue`
- **Nunca** `QTimer.singleShot(0, callback)` desde un thread que no sea el main — corre en el thread llamador, no en el main

## Logs a revisar

Activar modo verbose para más detalle:
```python
# En código o consola:
from core.logger import set_verbose
set_verbose(True)
```

Filtrar la salida por: `"Call mode"`, `"Audio"`, `"TTS"`, `"transcri"`

## Secuencia de reinicio limpio

```python
# 1. Terminar el call mode actual
_end_call()   # detiene grabación, limpia _call_active, resetea estado

# 2. Esperar confirmación en logs que el call terminó limpio
# Buscar: "Call ended" o ausencia de actividad en cola

# 3. Re-iniciar desde el botón
_on_call_button()  # inicia nuevo ciclo desde cero
```

## Diagnóstico por síntoma

| Síntoma | Causa probable | Dónde mirar |
|---------|---------------|-------------|
| Loop activo pero sin respuesta de IA | `_run_async_call` no devolvió control | Estado de `AsyncWorker`, excepciones no capturadas |
| Audio cortado a mitad | `sd.stop()` llamado mientras TTS reproducía | Llamadas a `sd.stop()` en el flujo |
| Grabación no inicia tras TTS | `_audio_recorder.is_recording` quedó True | Callback `on_stop` del `AudioRecorder` |
| `[END_CALL]` no termina la llamada | Token no llegó completo en streaming | Ensamblado de chunks en `_process_call_loop` |
| Race condition en cola | Dos coroutines escribiendo a la vez | `_flush_main_queue`, orden de operaciones en loop |
| TTS no produce audio | `edge-tts` falló silenciosamente en el daemon thread | Wrappear `asyncio.run()` con try/except y loggear |

## System prompt en call mode

El modo llamada inyecta instrucciones especiales:
- Sin markdown en las respuestas
- Sin comandos sudo
- Usar token `[END_CALL]` para terminar

Si la IA deja de responder con formato correcto, verificar que el system prompt se construyó con estas instrucciones (revisar `_default_system_prompt()` o el override de call mode).
