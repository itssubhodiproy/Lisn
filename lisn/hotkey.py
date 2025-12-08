"""
Hotkey listener for Lisn.

Grabs CapsLock at the hardware level to prevent caps toggle.
Uses python-evdev for low-level keyboard access.
"""

import threading
from dataclasses import dataclass, field
from typing import Callable, Optional, List

import evdev
from evdev import ecodes, InputDevice, UInput


class HotkeyError(Exception):
    """Exception raised for hotkey errors."""
    pass


def find_keyboard_devices() -> List[InputDevice]:
    """Find all keyboard input devices."""
    keyboards = []
    for path in evdev.list_devices():
        try:
            device = InputDevice(path)
            caps = device.capabilities()
            # Check if device has EV_KEY capability with typical keyboard keys
            if ecodes.EV_KEY in caps:
                keys = caps[ecodes.EV_KEY]
                # Check for CapsLock and some letter keys to confirm it's a keyboard
                if ecodes.KEY_CAPSLOCK in keys and ecodes.KEY_A in keys:
                    keyboards.append(device)
        except Exception:
            continue
    return keyboards


@dataclass
class HotkeyListener:
    """
    Hardware-level CapsLock listener using evdev.
    
    Grabs CapsLock events exclusively so they never reach the system,
    preventing caps toggle while still triggering recording.
    
    Usage:
        listener = EvdevHotkeyListener(
            on_press=start_recording,
            on_release=stop_recording,
        )
        listener.start()  # Runs in background thread
        # ... app runs ...
        listener.stop()
    """
    
    on_press: Optional[Callable[[], None]] = None
    on_release: Optional[Callable[[], None]] = None
    
    # Internal state
    _devices: List[InputDevice] = field(default_factory=list, init=False)
    _uinputs: List[UInput] = field(default_factory=list, init=False)
    _threads: List[threading.Thread] = field(default_factory=list, init=False)
    _running: bool = field(default=False, init=False)
    _pressed: bool = field(default=False, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def _handle_device(self, device: InputDevice, uinput: UInput) -> None:
        """Handle events from a single keyboard device."""
        import select
        
        try:
            # Grab device exclusively
            device.grab()
            
            while self._running:
                # Use select with timeout to allow clean shutdown
                r, _, _ = select.select([device.fd], [], [], 0.1)
                if not r:
                    continue  # Timeout, check _running flag
                
                for event in device.read():
                    if not self._running:
                        break
                    
                    if event.type == ecodes.EV_KEY:
                        if event.code == ecodes.KEY_CAPSLOCK:
                            # CapsLock event - handle it, don't forward
                            if event.value == 1:  # Key press
                                with self._lock:
                                    if not self._pressed:
                                        self._pressed = True
                                        if self.on_press:
                                            threading.Thread(
                                                target=self.on_press, 
                                                daemon=True
                                            ).start()
                            elif event.value == 0:  # Key release
                                with self._lock:
                                    if self._pressed:
                                        self._pressed = False
                                        if self.on_release:
                                            threading.Thread(
                                                target=self.on_release,
                                                daemon=True
                                            ).start()
                            # Don't forward CapsLock - swallow it completely
                        else:
                            # Forward all other key events
                            uinput.write(event.type, event.code, event.value)
                            uinput.syn()
                    else:
                        # Forward non-key events (like EV_SYN, EV_MSC)
                        try:
                            uinput.write(event.type, event.code, event.value)
                        except Exception:
                            pass  # Some events can't be forwarded
                        
        except Exception as e:
            if self._running:
                print(f"[Lisn] Keyboard handler error: {e}")
        finally:
            try:
                device.ungrab()
            except Exception:
                pass

    def start(self) -> None:
        """
        Start listening for CapsLock events.
        
        Raises:
            EvdevHotkeyError: If no keyboard found or permission denied
        """
        if self._running:
            return
        
        # Find keyboards
        self._devices = find_keyboard_devices()
        if not self._devices:
            raise HotkeyError(
                "No keyboard device found. Make sure you have permission to access "
                "/dev/input/event*. Add your user to the 'input' group:\n"
                "  sudo usermod -aG input $USER\n"
                "Then log out and back in."
            )
        
        self._running = True
        
        # Create UInput for each device to forward non-CapsLock events
        for device in self._devices:
            try:
                # Create virtual input device with same capabilities
                caps = device.capabilities()
                # Remove EV_SYN as it's handled automatically
                caps.pop(ecodes.EV_SYN, None)
                
                uinput = UInput(caps, name=f"lisn-{device.name}")
                self._uinputs.append(uinput)
                
                # Start handler thread for this device
                thread = threading.Thread(
                    target=self._handle_device,
                    args=(device, uinput),
                    daemon=True,
                )
                thread.start()
                self._threads.append(thread)
                
            except Exception as e:
                print(f"[Lisn] Warning: Could not grab {device.name}: {e}")
                continue
        
        if not self._uinputs:
            self._running = False
            raise HotkeyError("Failed to grab any keyboard device")

    def stop(self) -> None:
        """Stop listening and release all devices."""
        if not self._running:
            return
        
        self._running = False
        
        # Close devices to break read loops
        for device in self._devices:
            try:
                device.close()
            except Exception:
                pass
        
        # Wait for threads
        for thread in self._threads:
            thread.join(timeout=1)
        
        # Close UInputs
        for uinput in self._uinputs:
            try:
                uinput.close()
            except Exception:
                pass
        
        self._devices = []
        self._uinputs = []
        self._threads = []
        self._pressed = False

    @property
    def is_pressed(self) -> bool:
        """Check if CapsLock is currently pressed."""
        return self._pressed

    @property
    def is_running(self) -> bool:
        """Check if listener is running."""
        return self._running

    def __enter__(self) -> "HotkeyListener":
        self.start()
        return self

    def __exit__(self, *args) -> None:
        self.stop()
