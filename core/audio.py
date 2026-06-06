import os
import tempfile
import threading
from pathlib import Path
from typing import Callable, Optional

import sounddevice as sd
import soundfile as sf


class AudioRecorder:
    """Record audio from microphone to a WAV file."""

    def __init__(self):
        self._fs = 16000
        self._recording: list = []
        self._stream: Optional[sd.InputStream] = None
        self._is_recording = False
        self._on_stop_callback: Optional[Callable[[str], None]] = None

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

        def callback(indata, frames, time_info, status):
            if self._is_recording:
                self._recording.append(indata.copy())

        self._stream = sd.InputStream(
            samplerate=self._fs,
            channels=1,
            dtype="float32",
            callback=callback,
        )
        self._stream.start()

    def stop(self) -> Optional[str]:
        """Stop recording and return path to saved WAV file."""
        if not self._is_recording:
            return None
        self._is_recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if not self._recording:
            return None

        import numpy as np
        audio_data = np.concatenate(self._recording, axis=0)

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False, prefix="recording_")
        tmp.close()
        sf.write(tmp.name, audio_data, self._fs)
        self._recording = []

        if self._on_stop_callback:
            self._on_stop_callback(tmp.name)

        return tmp.name


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

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking

    def speak(self, text: str, voice: str = "es-MX-DaliaNeural") -> None:
        """Speak text in a background thread."""
        if self._is_speaking:
            return
        self._stop_event.clear()
        self._is_speaking = True
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
            print(f"TTS error: {e}")
        finally:
            self._is_speaking = False

    def _play_audio(self, path: str) -> None:
        try:
            import numpy as np
            data, fs = sf.read(path)
            sd.play(data, fs)
            sd.wait()
        except Exception as e:
            print(f"Audio playback error: {e}")

    def stop(self) -> None:
        self._stop_event.set()
        sd.stop()
        self._is_speaking = False
