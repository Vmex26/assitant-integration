import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import sounddevice as sd
import soundfile as sf

from .logger import get_logger

logger = get_logger(__name__)


class AudioRecorder:
    """Record audio from microphone to a WAV file with silence detection."""

    def __init__(self, silence_timeout: float = 1.5, silence_threshold: float = 0.01):
        self._fs = 16000
        self._silence_timeout = silence_timeout
        self._silence_threshold = silence_threshold
        self._recording: list = []
        self._stream: Optional[sd.InputStream] = None
        self._is_recording = False
        self._on_stop_callback: Optional[Callable[[str], None]] = None
        self._last_sound_time: float = 0.0
        self._silence_checker: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def start(self, on_stop: Optional[Callable[[str], None]] = None) -> None:
        """Start recording audio."""
        if self._is_recording:
            return
        self._recording = []
        self._on_stop_callback = on_stop
        self._is_recording = True
        self._stop_event.clear()
        self._last_sound_time = time.time()

        def callback(indata, frames, time_info, status):
            if not self._is_recording:
                return
            self._recording.append(indata.copy())
            rms = np.sqrt(np.mean(indata ** 2))
            if rms > self._silence_threshold:
                self._last_sound_time = time.time()

        self._stream = sd.InputStream(
            samplerate=self._fs,
            channels=1,
            dtype="float32",
            callback=callback,
        )
        self._stream.start()

        self._silence_checker = threading.Thread(target=self._check_silence, daemon=True)
        self._silence_checker.start()

    def _check_silence(self) -> None:
        """Background thread that stops recording after sustained silence."""
        while not self._stop_event.is_set():
            with self._lock:
                if not self._is_recording:
                    break
            if time.time() - self._last_sound_time > self._silence_timeout:
                self._finalize()
                break
            time.sleep(0.1)

    def _finalize(self) -> None:
        """Internal: stop stream and save recording."""
        with self._lock:
            if not self._is_recording:
                return
            self._is_recording = False
            self._stop_event.set()
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None

            if not self._recording:
                self._recording = []
                return

            audio_data = np.concatenate(self._recording, axis=0)
            self._recording = []
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False, prefix="recording_")
        tmp.close()
        sf.write(tmp.name, audio_data, self._fs)

        if self._on_stop_callback:
            self._on_stop_callback(tmp.name)

    def stop(self) -> Optional[str]:
        """Manually stop recording."""
        if not self._is_recording:
            return None
        self._stop_event.set()
        self._finalize()
        return None


class Transcriber:
    """Transcribe audio using faster-whisper (local)."""

    def __init__(self) -> None:
        self._model = None
        self._model_size: str = "small"
        self._device: str = "auto"
        self._compute_type: str = "auto"

    def configure(self, model_size: str = "small", device: str = "auto", compute_type: str = "auto") -> None:
        """Update model parameters (takes effect on next transcribe)."""
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._model = None  # force reload on next call

    def _load_model(self) -> None:
        if self._model is not None:
            return
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise RuntimeError(
                "faster-whisper is not installed. Run: pip install faster-whisper"
            )
        device = self._device
        if device == "auto":
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        compute = self._compute_type
        if compute == "auto":
            compute = "float16" if device == "cuda" else "int8"
        logger.info("Loading whisper model '%s' on %s (compute=%s)", self._model_size, device, compute)
        self._model = WhisperModel(self._model_size, device=device, compute_type=compute)

    def transcribe(self, audio_path: str, language: str = "es") -> Optional[str]:
        """Transcribe audio file using faster-whisper."""
        self._load_model()
        try:
            segments, info = self._model.transcribe(audio_path, language=language, beam_size=5)
            text = " ".join(seg.text for seg in segments)
            return text.strip() or None
        except Exception as e:
            logger.error("Whisper transcription error: %s", e)
            return f"[Error: Transcription failed: {e}]"


class TTSEngine:
    """Text-to-speech using edge-tts (Microsoft Edge).

    ``speak()`` is non-blocking — returns immediately.
    Poll ``is_playing`` to detect when playback finishes.
    """

    def __init__(self):
        self._max_chars = 2000
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    @property
    def is_playing(self) -> bool:
        try:
            return self._stop_event.is_set() is False and sd.get_stream() is not None
        except Exception:
            return False

    def speak(self, text: str, voice: str = "es-MX-DaliaNeural") -> None:
        """Speak text in a background thread (non-blocking)."""
        with self._lock:
            if self.is_playing:
                return
            self._stop_event.clear()
        truncated = text[:self._max_chars]
        threading.Thread(target=self._do_speak, args=(truncated, voice), daemon=True).start()

    def _do_speak(self, text: str, voice: str) -> None:
        import asyncio
        import edge_tts
        try:
            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, prefix="tts_")
            tmp.close()
            asyncio.run(edge_tts.Communicate(text, voice).save(tmp.name))
            if self._stop_event.is_set():
                os.unlink(tmp.name)
                return
            data, fs = sf.read(tmp.name)
            os.unlink(tmp.name)
            sd.play(data, fs)
            sd.wait()
        except Exception as e:
            logger.error("TTS error: %s", e)

    def stop(self) -> None:
        self._stop_event.set()
        sd.stop()
