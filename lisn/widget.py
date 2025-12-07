"""
Floating widget for Lisn.

Shows a visual indicator when recording is active.
Positions above the focused window.
"""

import subprocess
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib


class WidgetState(Enum):
    """Visual states for the widget."""
    HIDDEN = "hidden"
    RECORDING = "recording"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"


# State-specific colors and messages
STATE_STYLES = {
    WidgetState.RECORDING: {
        "message": "🎤 Recording",
        "bg_color": "#e74c3c",  # Red
    },
    WidgetState.PROCESSING: {
        "message": "⏳ Processing...",
        "bg_color": "#3498db",  # Blue
    },
    WidgetState.DONE: {
        "message": "✓ Done",
        "bg_color": "#27ae60",  # Green
    },
    WidgetState.ERROR: {
        "message": "❌ Error",
        "bg_color": "#e67e22",  # Orange
    },
}


@dataclass
class RecordingWidget:
    """
    Floating widget that shows recording status.
    
    Displays a small indicator above the focused window
    when recording is active.
    
    Usage:
        widget = RecordingWidget()
        widget.show()  # Show "Recording..."
        widget.hide()  # Hide widget
    """
    
    message: str = "🎤 Recording..."
    bg_color: str = "#e74c3c"  # Red
    text_color: str = "#ffffff"  # White
    padding: int = 12
    offset_y: int = 50  # Pixels above focused window
    
    # Internal state
    _window: Optional[Gtk.Window] = field(default=None, init=False)
    _label: Optional[Gtk.Label] = field(default=None, init=False)
    _initialized: bool = field(default=False, init=False)
    _visible: bool = field(default=False, init=False)

    def _ensure_initialized(self) -> None:
        """Initialize GTK window if needed (must be called from main thread)."""
        if self._initialized:
            return
        
        # Create window
        self._window = Gtk.Window(type=Gtk.WindowType.POPUP)
        self._window.set_decorated(False)
        self._window.set_keep_above(True)
        self._window.set_skip_taskbar_hint(True)
        self._window.set_skip_pager_hint(True)
        self._window.set_accept_focus(False)
        self._window.set_resizable(False)
        
        # Make window semi-transparent and styled
        screen = self._window.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self._window.set_visual(visual)
        self._window.set_app_paintable(True)
        
        # Apply CSS styling
        css = f"""
            window {{
                background-color: {self.bg_color};
                border-radius: 8px;
            }}
            label {{
                color: {self.text_color};
                font-size: 14px;
                font-weight: bold;
                padding: {self.padding}px {self.padding + 8}px;
            }}
        """
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_screen(
            screen,
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        
        # Create label
        self._label = Gtk.Label(label=self.message)
        self._window.add(self._label)
        
        self._initialized = True

    def _get_active_window_geometry(self) -> Optional[Tuple[int, int, int, int]]:
        """
        Get the geometry of the active window.
        
        Returns:
            Tuple of (x, y, width, height) or None if not available
        """
        try:
            # Try using xdotool for X11
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowgeometry", "--shell"],
                capture_output=True,
                text=True,
                timeout=1,
            )
            if result.returncode == 0:
                geometry = {}
                for line in result.stdout.strip().split('\n'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        geometry[key] = int(value)
                
                return (
                    geometry.get('X', 0),
                    geometry.get('Y', 0),
                    geometry.get('WIDTH', 400),
                    geometry.get('HEIGHT', 300),
                )
        except Exception:
            pass
        
        return None

    def _position_window(self) -> None:
        """Position window above the focused window."""
        if not self._window:
            return
        
        # Get widget size
        self._window.show_all()
        widget_width = self._window.get_allocated_width()
        widget_height = self._window.get_allocated_height()
        
        # Get active window geometry
        geometry = self._get_active_window_geometry()
        
        if geometry:
            win_x, win_y, win_width, win_height = geometry
            # Center horizontally above the window
            x = win_x + (win_width - widget_width) // 2
            y = win_y - widget_height - self.offset_y
            
            # Ensure widget stays on screen
            display = Gdk.Display.get_default()
            monitor = display.get_primary_monitor()
            if monitor:
                screen_rect = monitor.get_geometry()
                x = max(screen_rect.x, min(x, screen_rect.x + screen_rect.width - widget_width))
                y = max(screen_rect.y, min(y, screen_rect.y + screen_rect.height - widget_height))
        else:
            # Fallback: center on primary monitor
            display = Gdk.Display.get_default()
            monitor = display.get_primary_monitor()
            if monitor:
                rect = monitor.get_geometry()
                x = rect.x + (rect.width - widget_width) // 2
                y = rect.y + 100
            else:
                x, y = 100, 100
        
        self._window.move(x, y)

    def show(self, message: Optional[str] = None) -> None:
        """
        Show the recording widget.
        
        Args:
            message: Optional message to display (default: "🎤 Recording...")
        """
        def _show_in_main_thread():
            self._ensure_initialized()
            
            if message:
                self._label.set_text(message)
            
            self._position_window()
            self._window.show_all()
            self._visible = True
            return False
        
        GLib.idle_add(_show_in_main_thread)

    def hide(self) -> None:
        """Hide the recording widget."""
        def _hide_in_main_thread():
            if self._window:
                self._window.hide()
            self._visible = False
            return False
        
        GLib.idle_add(_hide_in_main_thread)

    def update_message(self, message: str) -> None:
        """Update the displayed message."""
        def _update_in_main_thread():
            if self._label:
                self._label.set_text(message)
            return False
        
        GLib.idle_add(_update_in_main_thread)

    def _update_style(self, bg_color: str) -> None:
        """Update widget background color."""
        def _apply_style():
            if not self._window:
                return False
            
            css = f"""
                window {{
                    background-color: {bg_color};
                    border-radius: 8px;
                }}
                label {{
                    color: {self.text_color};
                    font-size: 14px;
                    font-weight: bold;
                    padding: {self.padding}px {self.padding + 8}px;
                }}
            """
            style_provider = Gtk.CssProvider()
            style_provider.load_from_data(css.encode())
            screen = self._window.get_screen()
            Gtk.StyleContext.add_provider_for_screen(
                screen,
                style_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_USER
            )
            return False
        
        GLib.idle_add(_apply_style)

    def set_state(self, state: WidgetState) -> None:
        """
        Set widget to a specific state with appropriate styling.
        
        Args:
            state: New state (RECORDING, PROCESSING, DONE, ERROR, HIDDEN)
        """
        self._current_state = state
        
        if state == WidgetState.HIDDEN:
            self._stop_timer()
            self.hide()
            return
        
        style = STATE_STYLES.get(state, STATE_STYLES[WidgetState.ERROR])
        
        # Update style and message
        self._update_style(style["bg_color"])
        
        if state == WidgetState.RECORDING:
            # Start recording timer
            self._start_timer()
        else:
            self._stop_timer()
            self.update_message(style["message"])
        
        # Show widget
        self.show()
        
        # Auto-hide for DONE state
        if state == WidgetState.DONE:
            GLib.timeout_add(1500, self._auto_hide)

    def _auto_hide(self) -> bool:
        """Auto-hide callback."""
        if self._current_state == WidgetState.DONE:
            self.hide()
        return False  # Don't repeat

    def _start_timer(self) -> None:
        """Start recording duration timer."""
        self._timer_running = True
        self._timer_start = time.time()
        self._update_timer()

    def _stop_timer(self) -> None:
        """Stop recording duration timer."""
        self._timer_running = False

    def _update_timer(self) -> None:
        """Update timer display."""
        def _tick():
            if not self._timer_running:
                return False
            
            elapsed = time.time() - self._timer_start
            secs = int(elapsed)
            self.update_message(f"🎤 Recording... {secs}s")
            
            # Continue timer
            GLib.timeout_add(500, _tick)
            return False
        
        GLib.timeout_add(100, _tick)

    @property
    def is_visible(self) -> bool:
        """Check if widget is currently visible."""
        return self._visible

    @property
    def current_state(self) -> WidgetState:
        """Get current widget state."""
        return getattr(self, '_current_state', WidgetState.HIDDEN)

    def destroy(self) -> None:
        """Destroy the widget and clean up resources."""
        self._stop_timer()
        
        def _destroy_in_main_thread():
            if self._window:
                self._window.destroy()
                self._window = None
                self._label = None
                self._initialized = False
            return False
        
        GLib.idle_add(_destroy_in_main_thread)


class WidgetThread:
    """
    Runs GTK main loop in a separate thread.
    
    This allows the widget to be used from non-GTK applications.
    """
    
    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._widget: Optional[RecordingWidget] = None

    def start(self) -> RecordingWidget:
        """Start the widget thread and return the widget instance."""
        if self._running:
            return self._widget
        
        self._widget = RecordingWidget()
        self._running = True
        
        def run_gtk():
            # Initialize GTK in this thread
            GLib.idle_add(self._widget._ensure_initialized)
            Gtk.main()
        
        self._thread = threading.Thread(target=run_gtk, daemon=True)
        self._thread.start()
        
        return self._widget

    def stop(self) -> None:
        """Stop the widget thread."""
        if not self._running:
            return
        
        self._running = False
        
        def quit_gtk():
            if self._widget:
                self._widget.destroy()
            Gtk.main_quit()
            return False
        
        GLib.idle_add(quit_gtk)
        
        if self._thread:
            self._thread.join(timeout=1)
            self._thread = None
