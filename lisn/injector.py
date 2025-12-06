"""
Text injection module for Lisn.

Types transcribed text into the currently focused window.
Supports X11 (xdotool) and Wayland (ydotool).
"""

import shutil
import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional


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
    
    Uses xdotool for X11 and ydotool for Wayland.
    
    Usage:
        injector = TextInjector()
        injector.type_text("Hello, world!")
    """
    
    delay_ms: int = 0  # Delay between keystrokes (0 = fast)
    
    def __post_init__(self):
        """Initialize and detect available tools."""
        self._display_server = detect_display_server()
        self._tool = self._detect_tool()

    def _detect_tool(self) -> str:
        """Detect which typing tool is available."""
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
        
        raise InjectorError(
            "No text injection tool found. Please install xdotool (for X11) "
            "or ydotool (for Wayland):\n"
            "  sudo apt install xdotool  # For X11\n"
            "  sudo apt install ydotool  # For Wayland"
        )

    def _escape_text_xdotool(self, text: str) -> str:
        """Escape special characters for xdotool."""
        # xdotool's type command handles most characters
        # but we need to be careful with shell escaping
        return text

    def _type_with_xdotool(self, text: str) -> None:
        """Type text using xdotool."""
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
        """Type text using ydotool."""
        cmd = ["ydotool", "type", "--"]
        
        # ydotool has different delay syntax
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
                # Check for common ydotool issues
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
        Type text into the currently focused window.
        
        Args:
            text: Text to type
        
        Raises:
            InjectorError: If typing fails
        """
        if not text:
            return
        
        # Small delay to ensure focus is ready
        time.sleep(0.05)
        
        if self._tool == "xdotool":
            self._type_with_xdotool(text)
        elif self._tool == "ydotool":
            self._type_with_ydotool(text)
        else:
            raise InjectorError(f"Unknown tool: {self._tool}")

    def type_key(self, key: str) -> None:
        """
        Press a special key (e.g., Return, Tab).
        
        Args:
            key: Key name (e.g., "Return", "Tab", "space")
        """
        if self._tool == "xdotool":
            cmd = ["xdotool", "key", "--clearmodifiers", key]
        else:
            # ydotool uses different key names
            cmd = ["ydotool", "key", key]
        
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
        """Get the name of the tool being used."""
        return self._tool

    @staticmethod
    def is_available() -> bool:
        """Check if any text injection tool is available."""
        return bool(shutil.which("xdotool") or shutil.which("ydotool"))
