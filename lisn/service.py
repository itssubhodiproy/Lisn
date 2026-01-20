"""
Systemd user service management for Lisn.

Provides functions to install, enable, disable, and check status of the
Lisn systemd user service for auto-start on login.
"""

import shutil
import subprocess
from pathlib import Path


# Service file location (user-space, no sudo required)
SERVICE_DIR = Path.home() / ".config" / "systemd" / "user"
SERVICE_FILE = SERVICE_DIR / "lisn.service"


def _get_lisn_executable() -> str:
    """
    Find the path to the lisn executable.
    
    Returns:
        Path to lisn executable, or 'lisn' if not found in PATH
    """
    # Check if lisn is in PATH
    lisn_path = shutil.which("lisn")
    if lisn_path:
        return lisn_path
    
    # Fallback to common user install locations
    user_bin = Path.home() / ".local" / "bin" / "lisn"
    if user_bin.exists():
        return str(user_bin)
    
    # Last resort: assume it's in PATH
    return "lisn"


def _get_service_content() -> str:
    """Generate the systemd unit file content."""
    lisn_path = _get_lisn_executable()

    # Import DISPLAY and XAUTHORITY from the graphical session
    # These are needed for pynput/X11 keyboard access
    return f"""[Unit]
Description=Lisn Voice Dictation
After=graphical-session.target network.target sound.target
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart={lisn_path} start --foreground
Restart=on-failure
RestartSec=3
Environment=PYTHONUNBUFFERED=1
PassEnvironment=DISPLAY XAUTHORITY WAYLAND_DISPLAY XDG_RUNTIME_DIR

[Install]
WantedBy=graphical-session.target
"""


def get_service_path() -> Path:
    """Get the path to the service file."""
    return SERVICE_FILE


def is_service_installed() -> bool:
    """Check if the service file exists."""
    return SERVICE_FILE.exists()


def install_service() -> bool:
    """
    Install the systemd service file.
    
    Creates the service directory if needed and writes the unit file.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure directory exists
        SERVICE_DIR.mkdir(parents=True, exist_ok=True)
        
        # Write service file
        SERVICE_FILE.write_text(_get_service_content())
        
        # Reload systemd daemon
        result = subprocess.run(
            ["systemctl", "--user", "daemon-reload"],
            capture_output=True,
            text=True
        )
        
        return result.returncode == 0
    except Exception as e:
        print(f"[Lisn] Failed to install service: {e}")
        return False


def enable_service() -> bool:
    """
    Enable the service to start on login.

    Returns:
        True if successful, False otherwise
    """
    # Always reinstall to pick up any changes
    if not install_service():
        return False

    try:
        # Enable the service
        result = subprocess.run(
            ["systemctl", "--user", "enable", "lisn"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"[Lisn] Failed to enable service: {result.stderr}")
            return False
        
        # Start the service
        result = subprocess.run(
            ["systemctl", "--user", "start", "lisn"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"[Lisn] Failed to start service: {result.stderr}")
            return False
        
        return True
    except Exception as e:
        print(f"[Lisn] Failed to enable service: {e}")
        return False


def disable_service() -> bool:
    """
    Disable the service (stop auto-start on login).
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Stop the service
        subprocess.run(
            ["systemctl", "--user", "stop", "lisn"],
            capture_output=True,
            text=True
        )
        
        # Disable the service
        result = subprocess.run(
            ["systemctl", "--user", "disable", "lisn"],
            capture_output=True,
            text=True
        )
        
        return result.returncode == 0
    except Exception as e:
        print(f"[Lisn] Failed to disable service: {e}")
        return False


def get_service_status() -> dict:
    """
    Get the current status of the systemd service.
    
    Returns:
        Dict with status information
    """
    status = {
        "installed": is_service_installed(),
        "enabled": False,
        "active": False,
        "status_text": "not installed"
    }
    
    if not status["installed"]:
        return status
    
    try:
        # Check if enabled
        result = subprocess.run(
            ["systemctl", "--user", "is-enabled", "lisn"],
            capture_output=True,
            text=True
        )
        status["enabled"] = result.returncode == 0
        
        # Check if active
        result = subprocess.run(
            ["systemctl", "--user", "is-active", "lisn"],
            capture_output=True,
            text=True
        )
        status["active"] = result.returncode == 0
        status["status_text"] = result.stdout.strip() or "unknown"
        
    except Exception:
        pass
    
    return status
