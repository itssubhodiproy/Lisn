#!/usr/bin/env bash
#
# Lisn Installation Script
# One-command setup for Lisn voice dictation
#
# Usage: ./install.sh
#
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Script directory (where this script lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
LOCAL_BIN="$HOME/.local/bin"

# Track if logout is needed
NEEDS_LOGOUT=false

# ============================================================================
# Helper Functions
# ============================================================================

echo_step() {
    echo -e "\n${BLUE}==>${NC} ${BOLD}$1${NC}"
}

echo_ok() {
    echo -e "${GREEN}✓${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

echo_error() {
    echo -e "${RED}✗${NC} $1"
}

check_command() {
    command -v "$1" &> /dev/null
}

# ============================================================================
# Main Installation Steps
# ============================================================================

echo -e "${BOLD}╔════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║     Lisn Voice Dictation Installer     ║${NC}"
echo -e "${BOLD}╚════════════════════════════════════════╝${NC}"

# Step 1: Check sudo access
echo_step "Checking sudo access..."
if sudo -v; then
    echo_ok "Sudo access confirmed"
else
    echo_error "Sudo access required for installing dependencies"
    exit 1
fi

# Step 2: Install system dependencies
echo_step "Installing system dependencies..."

PACKAGES=(
    # Python
    python3-venv
    python3-pip
    # Text injection
    xdotool        # X11
    ydotool        # Wayland
    # Clipboard (for pyperclip backend)
    xclip          # X11 clipboard
    wl-clipboard   # Wayland clipboard
    # GTK for widget
    gir1.2-gtk-3.0
    python3-gi
    python3-gi-cairo
    # Audio
    libportaudio2
    portaudio19-dev
)

sudo apt update -qq
sudo apt install -y "${PACKAGES[@]}"
echo_ok "System dependencies installed"

# Step 3: Setup input group for keyboard detection
echo_step "Setting up input group permissions..."

if groups "$USER" | grep -q '\binput\b'; then
    echo_ok "User already in input group"
else
    sudo usermod -aG input "$USER"
    NEEDS_LOGOUT=true
    echo_ok "Added user to input group"
fi

# Step 4: Wayland-specific setup
echo_step "Detecting display server..."

if [[ "$XDG_SESSION_TYPE" == "wayland" ]]; then
    echo_ok "Wayland session detected"
    
    # Setup udev rule for /dev/uinput
    UDEV_RULE="/etc/udev/rules.d/80-uinput.rules"
    if [[ ! -f "$UDEV_RULE" ]]; then
        echo "  Setting up uinput permissions..."
        echo 'KERNEL=="uinput", MODE="0660", GROUP="input"' | sudo tee "$UDEV_RULE" > /dev/null
        sudo udevadm control --reload-rules
        sudo udevadm trigger
        echo_ok "uinput permissions configured"
    else
        echo_ok "uinput rule already exists"
    fi
    
    # Enable ydotoold service
    if systemctl is-active --quiet ydotoold 2>/dev/null; then
        echo_ok "ydotoold service already running"
    else
        echo "  Enabling ydotoold service..."
        sudo systemctl enable --now ydotoold 2>/dev/null || echo_warn "ydotoold service not available (may need reboot)"
    fi
else
    echo_ok "X11 session detected (or session type unknown)"
fi

# Step 5: Create Python virtual environment
echo_step "Setting up Python environment..."

if [[ -d "$VENV_DIR" ]]; then
    echo_ok "Virtual environment already exists"
else
    python3 -m venv "$VENV_DIR" --system-site-packages
    echo_ok "Virtual environment created"
fi

# Step 6: Install Lisn package
echo_step "Installing Lisn..."

# Use explicit venv pip path (source activation is unreliable in scripts)
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -e "$SCRIPT_DIR" -q
echo_ok "Lisn package installed"

# Step 7: Create symlink in ~/.local/bin
echo_step "Setting up command symlink..."

mkdir -p "$LOCAL_BIN"
LISN_BIN="$VENV_DIR/bin/lisn"

if [[ -L "$LOCAL_BIN/lisn" ]]; then
    rm "$LOCAL_BIN/lisn"
fi

ln -sf "$LISN_BIN" "$LOCAL_BIN/lisn"
echo_ok "Symlink created: $LOCAL_BIN/lisn"

# Ensure ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
    echo_warn "$LOCAL_BIN is not in your PATH"
    echo "  Add this to your ~/.bashrc or ~/.zshrc:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# Step 8: Run lisn setup (interactive)
echo_step "Configuring Lisn..."
echo ""
"$LISN_BIN" setup

# Step 9: Enable systemd service
echo_step "Enabling auto-start service..."
"$LISN_BIN" service enable

# ============================================================================
# Final Output
# ============================================================================

echo ""
echo -e "${GREEN}${BOLD}════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}   Lisn installation complete! 🎉${NC}"
echo -e "${GREEN}${BOLD}════════════════════════════════════════${NC}"
echo ""
echo "Usage:"
echo "  lisn start       - Start dictation daemon"
echo "  lisn stop        - Stop daemon"
echo "  lisn status      - Check status"
echo ""

if [[ "$NEEDS_LOGOUT" == true ]]; then
    echo -e "${YELLOW}${BOLD}⚠ IMPORTANT: You must log out and back in${NC}"
    echo -e "${YELLOW}  for keyboard detection to work.${NC}"
    echo ""
fi

echo "Hold CapsLock to dictate. Release to transcribe."
