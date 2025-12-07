"""
Hotkey detection module for Lisn.

Implements global hotkey listener for CapsLock push-to-talk.
"""

import threading
from dataclasses import dataclass, field
from typing import Callable, Optional
from enum import Enum

from pynput import keyboard


class HotkeyError(Exception):
    """Exception raised for hotkey-related errors."""
    pass


class KeyState(Enum):
    """State of the hotkey."""
    RELEASED = "released"
    PRESSED = "pressed"


@dataclass
class HotkeyListener:
    """
    Global hotkey listener for push-to-talk.
    
    Listens for CapsLock press and release events.
    
    Usage:
        def on_press():
            print("Recording started")
        
        def on_release():
            print("Recording stopped")
        
        listener = HotkeyListener(on_press=on_press, on_release=on_release)
        listener.start()
        # ... app runs ...
        listener.stop()
    """
    
    on_press: Optional[Callable[[], None]] = None
    on_release: Optional[Callable[[], None]] = None
    trigger_key: str = "caps_lock"
    
    # Internal state
    _listener: Optional[keyboard.Listener] = field(default=None, init=False)
    _state: KeyState = field(default=KeyState.RELEASED, init=False)
    _running: bool = field(default=False, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def _get_trigger_key(self) -> keyboard.Key:
        """Convert trigger key string to pynput Key."""
        key_map = {
            "caps_lock": keyboard.Key.caps_lock,
            "capslock": keyboard.Key.caps_lock,
            "control": keyboard.Key.ctrl_l,
            "ctrl": keyboard.Key.ctrl_l,
            "space": keyboard.Key.space,
        }
        
        key = key_map.get(self.trigger_key.lower())
        if key is None:
            raise HotkeyError(f"Unsupported trigger key: {self.trigger_key}")
        return key

    def _on_key_press(self, key: keyboard.Key) -> None:
        """Handle key press event."""
        try:
            trigger = self._get_trigger_key()
            if key == trigger:
                with self._lock:
                    if self._state == KeyState.RELEASED:
                        self._state = KeyState.PRESSED
                        if self.on_press:
                            # Run callback in separate thread to avoid blocking
                            threading.Thread(target=self.on_press, daemon=True).start()
        except Exception:
            pass  # Ignore errors in key handling

    def _on_key_release(self, key: keyboard.Key) -> None:
        """Handle key release event."""
        try:
            trigger = self._get_trigger_key()
            if key == trigger:
                with self._lock:
                    if self._state == KeyState.PRESSED:
                        self._state = KeyState.RELEASED
                        if self.on_release:
                            # Run callback in separate thread to avoid blocking
                            threading.Thread(target=self.on_release, daemon=True).start()
        except Exception:
            pass  # Ignore errors in key handling

    def start(self) -> None:
        """
        Start listening for hotkey events.
        
        Raises:
            HotkeyError: If listener fails to start (e.g., permission issues)
        """
        if self._running:
            return
        
        try:
            self._listener = keyboard.Listener(
                on_press=self._on_key_press,
                on_release=self._on_key_release,
            )
            self._listener.start()
            self._running = True
        except Exception as e:
            raise HotkeyError(
                f"Failed to start hotkey listener: {e}. "
                "Make sure you have permission to access input devices. "
                "On Linux, you may need to add your user to the 'input' group."
            ) from e

    def stop(self) -> None:
        """Stop listening for hotkey events."""
        if not self._running:
            return
        
        self._running = False
        if self._listener:
            self._listener.stop()
            self._listener = None
        
        with self._lock:
            self._state = KeyState.RELEASED

    @property
    def is_pressed(self) -> bool:
        """Check if the trigger key is currently pressed."""
        return self._state == KeyState.PRESSED

    @property
    def is_running(self) -> bool:
        """Check if the listener is running."""
        return self._running

    def __enter__(self) -> "HotkeyListener":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()
