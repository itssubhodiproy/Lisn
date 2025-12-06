"""
Core daemon process for Lisn.

Orchestrates the full dictation flow:
hotkey press → audio recording → transcription → formatting → text injection
"""

import signal
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from lisn.config import Config
from lisn.audio import AudioRecorder, to_wav_bytes, is_silent, trim_silence
from lisn.groq_client import GroqClient, GroqClientError
from lisn.hotkey import HotkeyListener
from lisn.injector import TextInjector, InjectorError


class DaemonState(Enum):
    """State of the daemon."""
    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"
    ERROR = "error"


@dataclass
class DaemonProcess:
    """
    Main daemon process for Lisn voice dictation.
    
    Orchestrates the full flow:
    1. Listen for CapsLock press → start recording
    2. Listen for CapsLock release → stop recording
    3. Send audio to Groq Whisper for transcription
    4. Format text with LLM
    5. Type text into focused window
    
    Usage:
        daemon = DaemonProcess()
        daemon.run()  # Blocks until stopped
    """
    
    config: Config = field(default_factory=Config.load)
    on_state_change: Optional[Callable[[DaemonState], None]] = None
    on_transcription: Optional[Callable[[str], None]] = None
    
    # Internal state
    _state: DaemonState = field(default=DaemonState.IDLE, init=False)
    _running: bool = field(default=False, init=False)
    _recorder: Optional[AudioRecorder] = field(default=None, init=False)
    _groq_client: Optional[GroqClient] = field(default=None, init=False)
    _injector: Optional[TextInjector] = field(default=None, init=False)
    _hotkey_listener: Optional[HotkeyListener] = field(default=None, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _stop_event: threading.Event = field(default_factory=threading.Event, init=False)

    def _set_state(self, state: DaemonState) -> None:
        """Update state and notify listeners."""
        self._state = state
        if self.on_state_change:
            try:
                self.on_state_change(state)
            except Exception:
                pass  # Don't let callback errors crash daemon

    def _on_hotkey_press(self) -> None:
        """Handle hotkey press - start recording."""
        with self._lock:
            if self._state != DaemonState.IDLE:
                return  # Already recording or processing
            
            self._set_state(DaemonState.RECORDING)
        
        try:
            self._recorder.start_recording()
        except Exception as e:
            print(f"[Lisn] Recording error: {e}")
            self._set_state(DaemonState.ERROR)
            time.sleep(1)
            self._set_state(DaemonState.IDLE)

    def _on_hotkey_release(self) -> None:
        """Handle hotkey release - stop recording and process."""
        with self._lock:
            if self._state != DaemonState.RECORDING:
                return  # Not recording
            
            self._set_state(DaemonState.PROCESSING)
        
        # Process in background thread to not block hotkey listener
        threading.Thread(target=self._process_recording, daemon=True).start()

    def _process_recording(self) -> None:
        """Process the recorded audio: transcribe, format, inject."""
        try:
            # Get audio data
            audio = self._recorder.get_audio_numpy()
            
            if audio is None or len(audio) == 0:
                self._set_state(DaemonState.IDLE)
                return
            
            # Trim silence
            audio = trim_silence(audio, sample_rate=self.config.audio.sample_rate)
            
            # Check if mostly silent
            if is_silent(audio, sample_rate=self.config.audio.sample_rate):
                self._set_state(DaemonState.IDLE)
                return
            
            # Convert to WAV
            wav_bytes = to_wav_bytes(audio, sample_rate=self.config.audio.sample_rate)
            
            # Transcribe
            result = self._groq_client.transcribe_audio(wav_bytes)
            text = result.text
            
            if not text or not text.strip():
                self._set_state(DaemonState.IDLE)
                return
            
            # Format with LLM (optional, can be disabled)
            try:
                formatted_text = self._groq_client.format_text(
                    text, 
                    llm_model=self.config.api.llm_model
                )
            except GroqClientError:
                # On formatting error, use raw transcription
                formatted_text = text
            
            # Notify listeners
            if self.on_transcription:
                try:
                    self.on_transcription(formatted_text)
                except Exception:
                    pass
            
            # Inject text into focused window
            try:
                self._injector.type_text(formatted_text)
            except InjectorError as e:
                print(f"[Lisn] Injection error: {e}")
            
        except GroqClientError as e:
            print(f"[Lisn] API error: {e}")
        except Exception as e:
            print(f"[Lisn] Error: {e}")
        finally:
            self._set_state(DaemonState.IDLE)

    def _setup_signal_handlers(self) -> None:
        """Set up graceful shutdown on SIGINT/SIGTERM."""
        def handle_signal(signum, frame):
            print("\n[Lisn] Shutting down...")
            self.stop()
        
        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

    def run(self) -> None:
        """
        Run the daemon. Blocks until stop() is called.
        
        Raises:
            RuntimeError: If configuration is invalid
        """
        # Validate config
        errors = self.config.validate()
        if errors:
            raise RuntimeError(f"Invalid configuration: {'; '.join(errors)}")
        
        # Initialize components
        self._recorder = AudioRecorder(
            sample_rate=self.config.audio.sample_rate,
            channels=self.config.audio.channels,
            device=self.config.audio.device,
        )
        
        self._groq_client = GroqClient(
            api_key=self.config.api.api_key,
            whisper_model=self.config.api.whisper_model,
        )
        
        self._injector = TextInjector()
        
        self._hotkey_listener = HotkeyListener(
            on_press=self._on_hotkey_press,
            on_release=self._on_hotkey_release,
            trigger_key=self.config.hotkey.trigger,
        )
        
        # Set up signal handlers
        self._setup_signal_handlers()
        
        # Start listening
        self._running = True
        self._hotkey_listener.start()
        self._set_state(DaemonState.IDLE)
        
        print(f"[Lisn] Ready! Hold {self.config.hotkey.trigger.upper()} to dictate.")
        
        # Block until stopped
        try:
            while self._running and not self._stop_event.is_set():
                self._stop_event.wait(timeout=0.5)
        finally:
            self._cleanup()

    def stop(self) -> None:
        """Stop the daemon gracefully."""
        self._running = False
        self._stop_event.set()

    def _cleanup(self) -> None:
        """Clean up resources."""
        if self._hotkey_listener:
            self._hotkey_listener.stop()
        
        if self._recorder and self._recorder.is_recording:
            self._recorder.stop_recording()
        
        self._set_state(DaemonState.IDLE)
        print("[Lisn] Stopped.")

    @property
    def state(self) -> DaemonState:
        """Get current daemon state."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Check if daemon is running."""
        return self._running
