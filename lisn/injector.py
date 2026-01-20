"""
Text injection module for Lisn.

Injects transcribed text into the currently focused window using clipboard paste.
Supports X11 and Wayland via pynput for Ctrl+V simulation.
Falls back to xdotool/ydotool type commands if paste fails.
"""

import shutil
import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import pyperclip
from pynput.keyboard import Controller, Key


class InjectorError(Exception):
    """Exception raised for text injection errors."""
    pass


class DisplayServer(Enum):
    """Display server type."""
    X11 = "x11"
    WAYLAND = "wayland"
    UNKNOWN = "unknown"


def detect_display_server() -> DisplayServer:
    """Detect which display server is running."""
    import os
    
    xdg_session = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if xdg_session == "wayland":
        return DisplayServer.WAYLAND
    elif xdg_session == "x11":
        return DisplayServer.X11
    
    # Fallback: check for WAYLAND_DISPLAY
    if os.environ.get("WAYLAND_DISPLAY"):
        return DisplayServer.WAYLAND
    
    # Fallback: check for DISPLAY (X11)
    if os.environ.get("DISPLAY"):
        return DisplayServer.X11
    
    return DisplayServer.UNKNOWN


@dataclass
class TextInjector:
    """
    Injects text into the currently focused window.
    
    Primary method: clipboard paste (Ctrl+V) - fast and reliable.
    Fallback: xdotool/ydotool type commands for apps that don't support paste.
    
    Usage:
        injector = TextInjector()
        injector.inject_text("Hello, world!")
    """
    
    delay_ms: int = 0  # Delay between keystrokes (for fallback typing)
    
    def __post_init__(self):
        """Initialize and detect available tools."""
        self._display_server = detect_display_server()
        self._keyboard = Controller()
        self._fallback_tool = self._detect_fallback_tool()

    def _detect_fallback_tool(self) -> Optional[str]:
        """Detect which typing tool is available for fallback."""
        # For X11, prefer xdotool
        if self._display_server == DisplayServer.X11:
            if shutil.which("xdotool"):
                return "xdotool"
        
        # For Wayland or as fallback, try ydotool
        if shutil.which("ydotool"):
            return "ydotool"
        
        # Final fallback to xdotool (might work via XWayland)
        if shutil.which("xdotool"):
            return "xdotool"
        
        return None  # No fallback available

    def _save_clipboard(self) -> Optional[str]:
        """Save current clipboard contents."""
        try:
            return pyperclip.paste()
        except Exception:
            return None  # Clipboard might be empty or inaccessible

    def _restore_clipboard(self, content: Optional[str]) -> None:
        """Restore clipboard contents."""
        if content is not None:
            try:
                pyperclip.copy(content)
            except Exception:
                pass  # Best effort restore

    def _paste_with_keyboard(self) -> None:
        """Simulate Ctrl+V to paste from clipboard."""
        time.sleep(0.02)

        if self._display_server == DisplayServer.WAYLAND:
            self._paste_with_ydotool()
        else:
            self._keyboard.press(Key.ctrl)
            self._keyboard.press('v')
            self._keyboard.release('v')
            self._keyboard.release(Key.ctrl)

        time.sleep(0.05)

    def _paste_with_ydotool(self) -> None:
        """Simulate Ctrl+V using ydotool (for Wayland)."""
        try:
            subprocess.run(
                ["ydotool", "key", "ctrl+v"],
                capture_output=True,
                timeout=5,
            )
        except Exception as e:
            raise InjectorError(f"ydotool paste failed: {e}")

    def inject_text(self, text: str, use_fallback: bool = True) -> None:
        """
        Inject text into the currently focused window using clipboard paste.
        
        Args:
            text: Text to inject
            use_fallback: If True, falls back to typing if paste fails
        
        Raises:
            InjectorError: If injection fails and no fallback available
        """
        if not text:
            return

        time.sleep(0.05)
        
        # Save original clipboard
        original_clipboard = self._save_clipboard()
        
        try:
            # Copy text to clipboard
            pyperclip.copy(text)
            
            # Paste with Ctrl+V
            self._paste_with_keyboard()
            
        except Exception as e:
            if use_fallback and self._fallback_tool:
                # Fall back to type-based injection
                self.type_text(text)
            else:
                raise InjectorError(f"Clipboard injection failed: {e}")
        finally:
            # Restore original clipboard (with small delay to ensure paste completed)
            time.sleep(0.1)
            self._restore_clipboard(original_clipboard)

    def _type_with_xdotool(self, text: str) -> None:
        """Type text using xdotool (fallback)."""
        cmd = ["xdotool", "type", "--clearmodifiers"]
        
        if self.delay_ms > 0:
            cmd.extend(["--delay", str(self.delay_ms)])
        
        cmd.append("--")
        cmd.append(text)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                raise InjectorError(f"xdotool failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            raise InjectorError("xdotool timed out")
        except FileNotFoundError:
            raise InjectorError("xdotool not found")

    def _type_with_ydotool(self, text: str) -> None:
        """Type text using ydotool (fallback)."""
        cmd = ["ydotool", "type", "--"]
        
        if self.delay_ms > 0:
            cmd.insert(2, f"--key-delay={self.delay_ms}")
        
        cmd.append(text)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                stderr = result.stderr.lower()
                if "uinput" in stderr or "permission" in stderr:
                    raise InjectorError(
                        "ydotool cannot access /dev/uinput. Fix with:\n"
                        "  sudo usermod -aG input $USER\n"
                        "  sudo chmod 666 /dev/uinput\n"
                        "Then log out and back in."
                    )
                elif "ydotoold" in stderr:
                    raise InjectorError(
                        "ydotoold daemon not running. Start with:\n"
                        "  sudo systemctl enable ydotool --now\n"
                        "Or run manually: sudo ydotoold &"
                    )
                else:
                    raise InjectorError(f"ydotool failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            raise InjectorError("ydotool timed out")
        except FileNotFoundError:
            raise InjectorError("ydotool not found")

    def type_text(self, text: str) -> None:
        """
        Type text character-by-character (fallback method).
        
        Uses xdotool for X11 and ydotool for Wayland.
        Slower than clipboard paste but works in more apps.
        
        Args:
            text: Text to type
        
        Raises:
            InjectorError: If typing fails
        """
        if not text:
            return
        
        if not self._fallback_tool:
            raise InjectorError(
                "No text injection tool found. Please install xdotool (for X11) "
                "or ydotool (for Wayland):\n"
                "  sudo apt install xdotool  # For X11\n"
                "  sudo apt install ydotool  # For Wayland"
            )
        
        time.sleep(0.05)
        
        if self._fallback_tool == "xdotool":
            self._type_with_xdotool(text)
        elif self._fallback_tool == "ydotool":
            self._type_with_ydotool(text)

    def type_key(self, key: str) -> None:
        """
        Press a special key (e.g., Return, Tab).
        
        Args:
            key: Key name (e.g., "Return", "Tab", "space")
        """
        if self._fallback_tool == "xdotool":
            cmd = ["xdotool", "key", "--clearmodifiers", key]
        elif self._fallback_tool == "ydotool":
            cmd = ["ydotool", "key", key]
        else:
            return  # No tool available
        
        try:
            subprocess.run(cmd, capture_output=True, timeout=5)
        except Exception:
            pass  # Best effort

    @property
    def display_server(self) -> DisplayServer:
        """Get the detected display server."""
        return self._display_server

    @property
    def tool_name(self) -> str:
        """Get the name of the fallback tool being used."""
        return self._fallback_tool or "clipboard"

    @staticmethod
    def is_available() -> bool:
        """Check if text injection is available (clipboard always works)."""
        return True

