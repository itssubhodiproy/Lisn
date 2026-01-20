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
from lisn.hotkey import HotkeyListener, HotkeyError
from lisn.injector import TextInjector, InjectorError
from lisn.widget import RecordingWidget, WidgetState, WidgetThread


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
    show_widget: bool = True  # Show visual indicator
    on_state_change: Optional[Callable[[DaemonState], None]] = None
    on_transcription: Optional[Callable[[str], None]] = None
    
    # Internal state
    _state: DaemonState = field(default=DaemonState.IDLE, init=False)
    _running: bool = field(default=False, init=False)
    _recorder: Optional[AudioRecorder] = field(default=None, init=False)
    _groq_client: Optional[GroqClient] = field(default=None, init=False)
    _injector: Optional[TextInjector] = field(default=None, init=False)
    _hotkey_listener: Optional[HotkeyListener] = field(default=None, init=False)
    _widget: Optional[RecordingWidget] = field(default=None, init=False)
    _widget_thread: Optional[WidgetThread] = field(default=None, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)
    _stop_event: threading.Event = field(default_factory=threading.Event, init=False)

    def _set_state(self, state: DaemonState) -> None:
        """Update state and notify listeners."""
        self._state = state
        
        # Update widget
        if self._widget:
            state_map = {
                DaemonState.IDLE: WidgetState.HIDDEN,
                DaemonState.RECORDING: WidgetState.RECORDING,
                DaemonState.PROCESSING: WidgetState.PROCESSING,
                DaemonState.ERROR: WidgetState.ERROR,
            }
            try:
                self._widget.set_state(state_map.get(state, WidgetState.HIDDEN))
            except Exception:
                pass
        
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
            
            # Transcribe with retry
            text = None
            for attempt in range(2):
                try:
                    result = self._groq_client.transcribe_audio(wav_bytes)
                    text = result.text
                    break
                except GroqClientError as e:
                    if attempt == 0 and "rate" in str(e).lower():
                        time.sleep(0.5)  # Brief pause for rate limits
                        continue
                    raise

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
            
            # Inject text into focused window (add trailing space for next dictation)
            try:
                self._injector.inject_text(formatted_text + " ")
                # Show success briefly
                self._set_state(DaemonState.IDLE)
            except InjectorError as e:
                self._show_error(f"Injection failed")
            
        except GroqClientError as e:
            error_msg = str(e)
            if "api_key" in error_msg.lower() or "auth" in error_msg.lower():
                self._show_error("Invalid API key")
            elif "rate" in error_msg.lower():
                self._show_error("Rate limited")
            elif "connect" in error_msg.lower() or "network" in error_msg.lower():
                self._show_error("No internet")
            else:
                self._show_error("API error")
        except Exception as e:
            self._show_error("Error")
        finally:
            # Ensure we return to idle after error display
            if self._state == DaemonState.ERROR:
                time.sleep(1.5)  # Show error briefly
                self._set_state(DaemonState.IDLE)

    def _show_error(self, message: str) -> None:
        """Show error in widget and set error state."""
        self._set_state(DaemonState.ERROR)
        if self._widget:
            self._widget.update_message(f"❌ {message}")

    def _setup_signal_handlers(self) -> None:
        """Set up graceful shutdown on SIGINT/SIGTERM."""
        def handle_signal(signum, frame):
            if not self._running:
                return  # Already stopping
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
        
        # Initialize widget for visual feedback (runs GTK in background thread)
        if self.show_widget:
            self._widget_thread = WidgetThread()
            self._widget = self._widget_thread.start()
            import time
            time.sleep(0.2)  # Give GTK a moment to initialize
        
        # Initialize hotkey listener (grabs CapsLock at hardware level)
        self._hotkey_listener = HotkeyListener(
            on_press=self._on_hotkey_press,
            on_release=self._on_hotkey_release,
        )
        
        # Set up signal handlers
        self._setup_signal_handlers()
        
        # Start listening
        self._running = True
        self._hotkey_listener.start()
        self._set_state(DaemonState.IDLE)
        
        print("[Lisn] Ready! Hold CAPSLOCK to dictate.")
        
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
        
        if self._widget_thread:
            self._widget_thread.stop()
        
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
