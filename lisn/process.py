"""
Daemon process management for Lisn.

Handles PID file management, single instance enforcement, and lifecycle control.
"""

import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Optional


# PID file location
PID_DIR = Path.home() / ".local" / "run" / "lisn"
PID_FILE = PID_DIR / "lisn.pid"


def _ensure_pid_dir() -> None:
    """Ensure PID directory exists."""
    PID_DIR.mkdir(parents=True, exist_ok=True)


def get_pid() -> Optional[int]:
    """
    Get the PID of the running daemon.
    
    Returns:
        PID if daemon is running, None otherwise
    """
    if not PID_FILE.exists():
        return None
    
    try:
        pid = int(PID_FILE.read_text().strip())
        
        # Check if process is actually running
        os.kill(pid, 0)  # Signal 0 = check existence
        return pid
    except (ValueError, ProcessLookupError, PermissionError):
        # Invalid PID or process not running
        _remove_pid_file()
        return None


def _write_pid_file(pid: int) -> None:
    """Write PID to file."""
    _ensure_pid_dir()
    PID_FILE.write_text(str(pid))


def _remove_pid_file() -> None:
    """Remove PID file if it exists."""
    try:
        PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def is_running() -> bool:
    """Check if daemon is currently running."""
    return get_pid() is not None


def start_daemon(foreground: bool = False) -> bool:
    """
    Start the daemon.
    
    Args:
        foreground: If True, run in foreground (blocking).
                   If False, fork to background.
    
    Returns:
        True if started successfully, False otherwise
    """
    # Check if already running
    pid = get_pid()
    if pid:
        print(f"[Lisn] Already running (PID {pid})")
        return False
    
    if foreground:
        # Run in foreground
        # Force GTK to use X11 backend on Wayland for reliable keyboard simulation
        if os.environ.get("XDG_SESSION_TYPE") == "wayland":
            os.environ["GDK_BACKEND"] = "x11"
        _write_pid_file(os.getpid())
        try:
            from lisn.daemon import DaemonProcess
            daemon = DaemonProcess()
            daemon.run()
        finally:
            _remove_pid_file()
        return True
    else:
        # Fork to background
        try:
            # Use subprocess to run the daemon in background
            # This approach works better than os.fork() for our use case
            cmd = [sys.executable, "-c", """
import os
import sys

# Detach from terminal
if os.fork() > 0:
    sys.exit(0)

os.setsid()

if os.fork() > 0:
    sys.exit(0)

# Run daemon
from lisn.process import _write_pid_file, _remove_pid_file
from lisn.daemon import DaemonProcess

_write_pid_file(os.getpid())
try:
    daemon = DaemonProcess()
    daemon.run()
finally:
    _remove_pid_file()
"""]

            # Preserve critical environment variables for Wayland/X11 access
            env = os.environ.copy()

            # Force GTK to use X11 backend on Wayland for reliable keyboard simulation
            # Native Wayland GTK has issues with focus handling for text injection
            if os.environ.get("XDG_SESSION_TYPE") == "wayland":
                env["GDK_BACKEND"] = "x11"

            # Start detached process with inherited environment
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                env=env,
            )
            
            # Wait for daemon to start and write PID file
            import time
            for _ in range(20):  # Wait up to 2 seconds
                time.sleep(0.1)
                if is_running():
                    pid = get_pid()
                    print(f"[Lisn] Started (PID {pid})")
                    return True
            
            print("[Lisn] Failed to start")
            return False
                
        except Exception as e:
            print(f"[Lisn] Failed to start: {e}")
            return False


def stop_daemon() -> bool:
    """
    Stop the daemon.
    
    Returns:
        True if stopped successfully, False otherwise
    """
    pid = get_pid()
    if not pid:
        print("[Lisn] Not running")
        return False
    
    try:
        # Send SIGTERM for graceful shutdown
        os.kill(pid, signal.SIGTERM)
        
        # Wait for process to exit
        import time
        for _ in range(10):  # Wait up to 5 seconds
            time.sleep(0.5)
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                # Process has exited
                _remove_pid_file()
                print("[Lisn] Stopped")
                return True
        
        # Force kill if still running
        os.kill(pid, signal.SIGKILL)
        _remove_pid_file()
        print("[Lisn] Killed")
        return True
        
    except ProcessLookupError:
        _remove_pid_file()
        print("[Lisn] Not running")
        return False
    except PermissionError:
        print(f"[Lisn] Permission denied to stop PID {pid}")
        return False
    except Exception as e:
        print(f"[Lisn] Failed to stop: {e}")
        return False


def restart_daemon() -> bool:
    """
    Restart the daemon.
    
    Returns:
        True if restarted successfully, False otherwise
    """
    if is_running():
        stop_daemon()
        import time
        time.sleep(0.5)
    
    return start_daemon(foreground=False)


def get_status() -> dict:
    """
    Get daemon status information.
    
    Returns:
        Dict with status info: running, pid, etc.
    """
    pid = get_pid()
    return {
        "running": pid is not None,
        "pid": pid,
        "pid_file": str(PID_FILE),
    }
