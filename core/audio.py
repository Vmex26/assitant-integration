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
    """Transcribe audio using Google's free Speech Recognition API."""

    def transcribe(self, audio_path: str) -> Optional[str]:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            audio = recognizer.record(source)
        try:
            return recognizer.recognize_google(audio, language="es-ES,en-US")
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            return f"[Error: Speech recognition service unavailable: {e}]"


class TTSEngine:
    """Text-to-speech using edge-tts (Microsoft Edge)."""

    def __init__(self):
        self._max_chars = 2000
        self._is_speaking = False
        self._stop_event = threading.Event()
        self._speak_lock = threading.Lock()

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking

    def speak(self, text: str, voice: str = "es-MX-DaliaNeural") -> None:
        """Speak text in a background thread."""
        with self._speak_lock:
            if self._is_speaking:
                return
            self._is_speaking = True
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
            self._play_audio(tmp.name)
            os.unlink(tmp.name)
        except Exception as e:
            logger.error("TTS error: %s", e)
        finally:
            with self._speak_lock:
                self._is_speaking = False

    def _play_audio(self, path: str) -> None:
        try:
            import numpy as np
            data, fs = sf.read(path)
            sd.play(data, fs)
            sd.wait()
        except Exception as e:
            logger.error("Audio playback error: %s", e)

    def stop(self) -> None:
        self._stop_event.set()
        sd.stop()
        with self._speak_lock:
            self._is_speaking = False
