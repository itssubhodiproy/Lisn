#!/usr/bin/env bash
#
# Lisn Uninstallation Script
# Cleanly removes Lisn from the system
#
# Usage: ./uninstall.sh
#
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
LOCAL_BIN="$HOME/.local/bin"
SERVICE_FILE="$HOME/.config/systemd/user/lisn.service"
CONFIG_DIR="$HOME/.config/lisn"
PID_DIR="$HOME/.local/run/lisn"

echo_step() {
    echo -e "\n${BLUE}==>${NC} ${BOLD}$1${NC}"
}

echo_ok() {
    echo -e "${GREEN}✓${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# ============================================================================
# Uninstallation
# ============================================================================

echo -e "${BOLD}╔════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║      Lisn Voice Dictation Uninstaller  ║${NC}"
echo -e "${BOLD}╚════════════════════════════════════════╝${NC}"

# Step 1: Stop and disable systemd service
echo_step "Stopping systemd service..."

if [[ -f "$SERVICE_FILE" ]]; then
    systemctl --user stop lisn 2>/dev/null || true
    systemctl --user disable lisn 2>/dev/null || true
    rm -f "$SERVICE_FILE"
    systemctl --user daemon-reload
    echo_ok "Service stopped and removed"
else
    echo_ok "Service not installed"
fi

# Step 2: Remove symlink
echo_step "Removing command symlink..."

if [[ -L "$LOCAL_BIN/lisn" ]]; then
    rm "$LOCAL_BIN/lisn"
    echo_ok "Symlink removed"
else
    echo_ok "Symlink not found"
fi

# Step 3: Remove PID directory
echo_step "Cleaning up runtime files..."

if [[ -d "$PID_DIR" ]]; then
    rm -rf "$PID_DIR"
    echo_ok "PID directory removed"
else
    echo_ok "No runtime files found"
fi

# Step 4: Ask about config
echo_step "Configuration..."

if [[ -d "$CONFIG_DIR" ]]; then
    read -p "Remove configuration and API key? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$CONFIG_DIR"
        echo_ok "Configuration removed"
    else
        echo_ok "Configuration kept at: $CONFIG_DIR"
    fi
else
    echo_ok "No configuration found"
fi

# Step 5: Ask about venv
echo_step "Virtual environment..."

if [[ -d "$VENV_DIR" ]]; then
    read -p "Remove virtual environment? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$VENV_DIR"
        echo_ok "Virtual environment removed"
    else
        echo_ok "Virtual environment kept at: $VENV_DIR"
    fi
else
    echo_ok "Virtual environment not found"
fi

# ============================================================================
# Final Output
# ============================================================================

echo ""
echo -e "${GREEN}${BOLD}════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}   Lisn has been uninstalled.${NC}"
echo -e "${GREEN}${BOLD}════════════════════════════════════════${NC}"
echo ""
echo "Note: System packages were not removed."
echo "To remove them manually:"
echo "  sudo apt remove xdotool ydotool xclip wl-clipboard"

