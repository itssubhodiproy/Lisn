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

# Step 0: Stop running lisn daemon
echo_step "Stopping running Lisn daemon..."

if [[ -L "$LOCAL_BIN/lisn" ]] && command -v "$LOCAL_BIN/lisn" &> /dev/null; then
    "$LOCAL_BIN/lisn" stop 2>/dev/null || true
    echo_ok "Lisn daemon stopped"
elif [[ -f "$PID_DIR/lisn.pid" ]]; then
    PID=$(cat "$PID_DIR/lisn.pid" 2>/dev/null)
    if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
        kill "$PID" 2>/dev/null || true
        echo_ok "Lisn daemon stopped (PID $PID)"
    fi
else
    echo_ok "No running daemon found"
fi

# Step 1: Stop and disable systemd service
echo_step "Stopping Lisn systemd service..."

if [[ -f "$SERVICE_FILE" ]]; then
    systemctl --user stop lisn 2>/dev/null || true
    systemctl --user disable lisn 2>/dev/null || true
    rm -f "$SERVICE_FILE"
    systemctl --user daemon-reload
    echo_ok "Lisn service stopped and removed"
else
    echo_ok "Lisn service not installed"
fi

# Step 1b: Handle ydotoold user service
YDOTOOL_SERVICE="$HOME/.config/systemd/user/ydotoold.service"
if [[ -f "$YDOTOOL_SERVICE" ]]; then
    read -p "Stop and remove ydotoold user service? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        systemctl --user stop ydotoold 2>/dev/null || true
        systemctl --user disable ydotoold 2>/dev/null || true
        rm -f "$YDOTOOL_SERVICE"
        systemctl --user daemon-reload
        echo_ok "ydotoold user service removed"
    else
        echo_ok "ydotoold user service kept"
    fi
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

