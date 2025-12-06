"""
Audio recording module for Lisn.

Captures audio from the microphone using sounddevice.
"""

import io
import threading
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import sounddevice as sd


class AudioError(Exception):
    """Exception raised for audio-related errors."""
    pass


@dataclass
class AudioRecorder:
    """
    Records audio from the microphone.
    
    Usage:
        recorder = AudioRecorder()
        recorder.start_recording()
        # ... user speaks ...
        audio_data = recorder.stop_recording()
    """
    sample_rate: int = 16000
    channels: int = 1
    device: Optional[str] = None
    
    # Internal state
    _recording: bool = field(default=False, init=False)
    _audio_buffer: list = field(default_factory=list, init=False)
    _stream: Optional[sd.InputStream] = field(default=None, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def _audio_callback(self, indata: np.ndarray, frames: int, 
                        time_info: dict, status: sd.CallbackFlags) -> None:
        """Callback function called for each audio block."""
        if status:
            # Log status flags (xruns, etc.) but don't fail
            pass
        
        # Copy the audio data to our buffer
        with self._lock:
            if self._recording:
                self._audio_buffer.append(indata.copy())

    def start_recording(self) -> None:
        """
        Start recording audio from the microphone.
        
        Raises:
            AudioError: If no audio device is available or recording fails.
        """
        if self._recording:
            return  # Already recording
        
        # Clear previous recording
        with self._lock:
            self._audio_buffer = []
        
        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                device=self.device,
                dtype=np.float32,
                callback=self._audio_callback,
            )
            self._stream.start()
            self._recording = True
        except sd.PortAudioError as e:
            raise AudioError(f"Failed to start recording: {e}") from e
        except Exception as e:
            raise AudioError(f"Audio error: {e}") from e

    def stop_recording(self) -> bytes:
        """
        Stop recording and return the audio data as bytes.
        
        Returns:
            Audio data as bytes (float32 numpy array serialized).
            Returns empty bytes if no audio was recorded.
        """
        if not self._recording:
            return b""
        
        self._recording = False
        
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        
        # Concatenate all audio chunks
        with self._lock:
            if not self._audio_buffer:
                return b""
            
            audio_data = np.concatenate(self._audio_buffer, axis=0)
            self._audio_buffer = []
        
        # Return as bytes
        return audio_data.tobytes()

    def get_audio_numpy(self) -> Optional[np.ndarray]:
        """
        Stop recording and return the audio data as a numpy array.
        
        Returns:
            Audio data as numpy float32 array, or None if no audio.
        """
        audio_bytes = self.stop_recording()
        if not audio_bytes:
            return None
        
        return np.frombuffer(audio_bytes, dtype=np.float32)

    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._recording

    @staticmethod
    def list_devices() -> list[dict]:
        """List available audio input devices."""
        devices = []
        for i, dev in enumerate(sd.query_devices()):
            if dev['max_input_channels'] > 0:
                devices.append({
                    'index': i,
                    'name': dev['name'],
                    'channels': dev['max_input_channels'],
                    'sample_rate': dev['default_samplerate'],
                })
        return devices

    @staticmethod
    def get_default_device() -> Optional[dict]:
        """Get the default input device info."""
        try:
            device_id = sd.default.device[0]  # Input device
            if device_id is None:
                return None
            dev = sd.query_devices(device_id)
            return {
                'index': device_id,
                'name': dev['name'],
                'channels': dev['max_input_channels'],
                'sample_rate': dev['default_samplerate'],
            }
        except Exception:
            return None
