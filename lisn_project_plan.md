# Lisn - Voice Dictation for Linux

## Project Overview
Push-to-talk voice dictation app using Groq Cloud (Whisper + LLM) for Linux desktop users. CapsLock hotkey, minimal UI with floating widget, types transcribed text into any focused window.

## Prerequisites
- Python 3.10+
- Ubuntu 24.04 (target platform)
- Groq API key
- Basic understanding of: audio I/O, system hotkeys, subprocess management

---

## Development Plan

### Phase 1: Foundation & Setup

#### Step 1: Project Structure Setup
**Goal**: Create basic project skeleton with proper Python packaging

- Initialize git repository
- Create directory structure (lisn/, tests/, docs/)
- Set up pyproject.toml with basic metadata
- Create virtual environment
- Add .gitignore for Python projects
- Create empty README.md with project description

**Test**: Verify package structure is valid, venv activates correctly

**Commit**: "Initialize project structure and Python packaging"

---

#### Step 2: Configuration Management
**Goal**: Implement config file handling

- Create config.py module
- Define config.yaml schema (API key, hotkey, audio settings)
- Implement config loading from ~/.config/lisn/
- Implement config creation with defaults
- Add config validation

**Test**: Create/load/validate config files, handle missing/invalid configs

**Commit**: "Add configuration management system"

---

#### Step 3: CLI Framework
**Goal**: Build basic CLI commands using Click

- Create cli.py module
- Implement `lisn setup` command (creates config)
- Implement `lisn status` command (placeholder)
- Implement `lisn start/stop` commands (placeholder)
- Add proper help text and error messages

**Test**: Run all CLI commands, verify help text, test error cases

**Commit**: "Implement CLI framework with basic commands"

---

### Phase 2: Audio Recording

#### Step 4: Audio Capture Module
**Goal**: Record audio from microphone

- Create audio.py module
- Implement AudioRecorder class using sounddevice
- Add start_recording() and stop_recording() methods
- Save recording to in-memory buffer (bytes)
- Handle audio device errors gracefully

**Test**: Record 3-second test audio, verify buffer contains data, test with no mic

**Commit**: "Implement audio recording functionality"

---

#### Step 5: Audio Format & Optimization
**Goal**: Ensure audio format is compatible with Groq Whisper

- Convert recorded audio to required format (16kHz mono WAV)
- Implement audio buffer to file conversion
- Add silence detection to trim empty audio
- Optimize buffer size for low latency

**Test**: Record and convert audio, verify format specs, test with silent audio

**Commit**: "Add audio format conversion and optimization"

---

### Phase 3: Groq API Integration

#### Step 6: Groq Client - STT
**Goal**: Send audio to Whisper API and get transcription

- Create groq_client.py module
- Implement GroqClient class
- Add transcribe_audio() method using Groq SDK
- Handle API errors (rate limits, network issues)
- Add timeout and retry logic

**Test**: Send test audio file, verify transcription, test error cases

**Commit**: "Implement Groq Whisper STT integration"

---

#### Step 7: Groq Client - LLM Formatting
**Goal**: Format transcription with minimal grammar fixes

- Add format_text() method to GroqClient
- Implement minimal formatting prompt (punctuation only)
- Handle LLM API errors
- Add response validation

**Test**: Format sample texts, verify minimal changes, test edge cases

**Commit**: "Add LLM text formatting functionality"

---

### Phase 4: System Integration

#### Step 8: Hotkey Detection
**Goal**: Detect CapsLock press/release globally

- Create hotkey.py module
- Implement global hotkey listener using pynput
- Detect CapsLock press and release events
- Add callback system for key events
- Handle permission issues (input access)

**Test**: Detect CapsLock in different apps, verify press/release timing

**Commit**: "Implement global hotkey detection"

---

#### Step 9: Text Injection
**Goal**: Insert transcribed text into focused window

- Create injector.py module
- Implement clipboard-based paste injection
- Save and restore user's original clipboard
- Simulate Ctrl+V using pynput
- Add fallback for apps that don't support paste
- Handle both X11 and Wayland

**Test**: Inject text into various apps, verify clipboard is preserved

**Commit**: "Implement clipboard-based text injection"

---

### Phase 5: Daemon Process

#### Step 10: Core Daemon Logic
**Goal**: Create main daemon process that orchestrates everything

- Create daemon.py module
- Implement DaemonProcess class
- Wire together: hotkey → audio → API → injection
- Add state management (idle, recording, processing)
- Implement graceful shutdown handling

**Test**: Run daemon, trigger full recording→transcription→injection flow

**Commit**: "Implement core daemon process"

---

#### Step 11: Daemon Process Management
**Goal**: Start/stop daemon as background process

- Add daemon start logic to CLI (fork process)
- Implement PID file management (~/.config/lisn/lisn.pid)
- Add daemon stop logic (read PID, send signal)
- Implement status checking (is daemon running?)
- Add logging to ~/.config/lisn/logs/

**Test**: Start/stop daemon multiple times, check PID handling, verify logging

**Commit**: "Add daemon process management"

---

### Phase 6: User Feedback

#### Step 12: Floating Widget - Basic
**Goal**: Show visual feedback during recording

- Create widget.py module using GTK
- Implement floating window (always on top, no decorations)
- Show "Recording..." message above focused window
- Add window positioning logic using active window geometry
- Handle multi-monitor setups

**Test**: Show widget in various screen positions, verify always-on-top

**Commit**: "Add basic floating widget for visual feedback"

---

#### Step 13: Floating Widget - States
**Goal**: Show different states with animations

- Add "Recording" state with red pulsing dot
- Add "Processing" state with spinner
- Add "Done" state with checkmark
- Implement smooth fade-out animation
- Add error state for API failures

**Test**: Trigger all states manually, verify animations, test timing

**Commit**: "Enhance widget with state animations"

---

### Phase 7: Polish & Reliability

#### Step 14: Error Handling & Recovery
**Goal**: Handle all failure cases gracefully

- Add comprehensive error handling in all modules
- Implement user-friendly error messages in widget
- Add automatic retry for transient failures
- Log errors properly for debugging
- Test network failure scenarios

**Test**: Test all error paths (no internet, wrong API key, mic access denied)

**Commit**: "Add comprehensive error handling"

---

#### Step 15: Performance Optimization
**Goal**: Minimize latency from speech to text appearance

- Profile audio recording latency
- Optimize API request/response handling
- Add audio streaming if beneficial
- Minimize widget render time
- Add metrics logging for debugging

**Test**: Measure end-to-end latency, verify <3s total time

**Commit**: "Optimize performance and reduce latency"

---

### Phase 8: Installation & Distribution

#### Step 16: Systemd Service
**Goal**: Auto-start daemon on login

- Create lisn.service systemd unit file
- Add service installation to setup command
- Implement enable/disable service commands
- Test service restart on failure
- Add service logs integration

**Test**: Enable service, reboot, verify auto-start

**Commit**: "Add systemd service integration"

---

#### Step 17: Installation Script
**Goal**: One-command installation for users

- Create install.sh script
- Check system dependencies (Python, audio libs, GTK)
- Install text injection tools (xdotool for X11, ydotool for Wayland)
- Set up /dev/uinput permissions (udev rule for ydotool)
- Add user to input group for keyboard access
- Enable ydotoold service on Wayland systems
- Install Python package in user space
- Run initial setup automatically (API key prompt)
- Create systemd user service (~/.config/systemd/user/lisn.service)
- Enable autostart on login (systemctl --user enable lisn)
- Add uninstall script

**Test**: Run install on fresh Ubuntu VM, verify all components work

**Commit**: "Create installation script"

---

#### Step 18: Documentation
**Goal**: Help users install and use Lisn

- Write comprehensive README.md (features, installation, usage)
- Add troubleshooting section (common issues)
- Document configuration options
- Add development setup guide
- Create CONTRIBUTING.md

**Test**: Follow docs on clean system, verify accuracy

**Commit**: "Add user and developer documentation"

---

### Phase 9: Testing & Refinement

#### Step 19: Integration Testing
**Goal**: Test complete workflows end-to-end

- Create test suite for full recording flow
- Test with various speech patterns
- Test with different applications
- Verify resource cleanup
- Test concurrent recordings (spam CapsLock)

**Test**: Run full test suite, fix discovered issues

**Commit**: "Add integration tests and fix bugs"

---

#### Step 20: Beta Testing & Feedback
**Goal**: Use it yourself daily, find issues

- Use Lisn for all dictation needs for 1 week
- Document pain points and bugs
- Measure actual API usage
- Test in different scenarios (calls, music playing)
- Iterate on UX based on real usage

**Test**: Real-world usage, gather personal feedback

**Commit**: "Refinements based on real-world usage"

---

## Post-MVP Enhancements (Future)

- Add "bring your own API key" support
- Implement voice commands (new line, undo, etc.)
- Add context-aware formatting (LinkedIn, Gmail, Terminal, etc.)
- Add macOS support
- Add Windows support
- Create web distribution site
- Package for AUR, apt repositories
- Add local Whisper option for privacy
- Mobile apps (Android/iOS)

---

## Success Criteria
- ✅ CapsLock press starts recording
- ✅ Release triggers transcription
- ✅ Text appears in <3 seconds
- ✅ Works in any application
- ✅ Visual feedback is clear
- ✅ Survives system reboot
- ✅ Handles errors gracefully
- ✅ Easy installation process