# Lisn

Push-to-talk voice dictation for Linux.

Hold CapsLock to record. Release to transcribe. Text appears wherever your cursor is.

https://github.com/user-attachments/assets/f31da510-fd53-4f3d-95e7-18efdcaf2ac0

## Why Lisn

- **Fast** — Powered by Groq's Whisper API. Transcription in under a second.
- **Works everywhere** — Types directly into any application. Slack, VS Code, browser, terminal.
- **Minimal** — No app switching. No copy-paste. Just talk and it types.
- **Private** — Runs locally. Audio is processed via API, never stored.

## Requirements

- Ubuntu 24.04+ (or compatible Linux distro)
- Python 3.10+
- [Groq API key](https://console.groq.com) (free tier available)

## Installation

```bash
git clone https://github.com/itssubhodiproy/Lisn.git
cd Lisn
./install.sh
```

The installer will:
- Install system dependencies
- Set up the Python environment
- Prompt for your Groq API key
- Enable auto-start on login

After installation, log out and back in for keyboard permissions to take effect.

## Usage

Lisn starts automatically on login. To control it manually:

```bash
lisn start      # Start the daemon
lisn stop       # Stop the daemon
lisn status     # Check status
```

**How to dictate:**
1. Focus any text input (editor, browser, chat)
2. Hold CapsLock
3. Speak
4. Release CapsLock
5. Text appears at cursor

## Configuration

Config file: `~/.config/lisn/config.yaml`

```bash
lisn setup      # Re-run setup (change API key)
lisn status     # View current configuration
```

## Auto-start

Lisn runs as a systemd user service:

```bash
lisn service enable     # Enable auto-start on login
lisn service disable    # Disable auto-start
lisn service status     # Check service status
```

## Uninstall

```bash
./uninstall.sh
```

## How it works

1. CapsLock press triggers recording via evdev
2. Audio captured at 16kHz mono
3. On release, audio sent to Groq Whisper API
4. Transcription formatted with LLM for punctuation
5. Text injected at cursor via clipboard paste

## Troubleshooting

**Text not appearing?**
- Log out and back in (required for input group permissions)
- Check `lisn status` for errors

**CapsLock not detected?**
- Ensure you're in the `input` group: `groups | grep input`
- If not: `sudo usermod -aG input $USER` then log out/in

**Wayland issues?**
- Lisn uses XWayland for compatibility
- Ensure `ydotool` service is running: `systemctl --user status ydotoold`

## License

MIT
