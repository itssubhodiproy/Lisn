# Lisn

**Push-to-talk voice dictation for Linux**

Lisn is a minimal voice dictation app that uses Groq Cloud (Whisper + LLM) to transcribe your speech and type it into any focused window. Hold CapsLock to record, release to transcribe.

## Features

- 🎤 **Push-to-talk** - Hold CapsLock to record, release to transcribe
- ⚡ **Fast** - Powered by Groq's ultra-fast Whisper API
- 🔧 **Works everywhere** - Types text into any focused application
- 🎯 **Minimal UI** - Floating widget shows recording status
- 🐧 **Linux-first** - Built for Ubuntu 24.04+

## Demo

https://github.com/itssubhodiproy/Lisn/raw/main/demo/Demo.mp4

## Requirements

- Python 3.10+
- Ubuntu 24.04 (or compatible Linux distro)
- Groq API key

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/lisn.git
cd lisn

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e .
```

## Usage

```bash
# Run lisn
lisn
```

## Development

This project is in early development. See `lisn_project_plan.md` for the development roadmap.

## License

MIT
