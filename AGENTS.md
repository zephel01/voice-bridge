# Voice Bridge - Agent Guide

## Project Overview

Real-time English-to-Japanese voice translation desktop application for macOS and Windows. Captures system audio from YouTube videos, transcribes English speech, translates to Japanese, and plays back synthesized Japanese audio.

**Technology Stack:**
- Python 3.9+
- tkinter for GUI
- faster-whisper (speech recognition)
- deep-translator (Google Translate)
- VOICEVOX (primary TTS, local server)
- edge-tts (fallback TTS, Microsoft Edge)
- sounddevice (audio capture, macOS)
- PyAudioWPatch (audio capture, Windows WASAPI loopback)
- pygame (audio playback)

## Essential Commands

### Running the Application

```bash
# GUI mode (default)
python main.py

# CLI mode (debug)
python main.py --cli

# List available audio devices
python main.py --list-devices

# With custom parameters
python main.py --device "BlackHole 2ch" --model small --chunk 4.0

# CLI with specific VOICEVOX speaker
python main.py --cli --speaker-id 3
```

### Environment Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### Development

```bash
# Test individual modules
python audio_capture.py     # List audio devices
python transcriber.py       # Test Whisper model loading
python translator.py        # Test translation
python tts_engine.py        # Test Edge TTS synthesis
python tts_voicevox.py      # Test VOICEVOX connection & list speakers
```

## Project Structure

```
voice-bridge/
├── main.py              # Entry point, VoiceBridge orchestrator class
├── audio_capture.py     # AudioCapture class - macOS system audio (BlackHole + sounddevice)
├── audio_capture_win.py # WindowsAudioCapture class - Windows system audio (WASAPI loopback)
├── transcriber.py       # Transcriber class - Whisper speech recognition
├── translator.py        # Translator class - English→Japanese translation
├── tts_voicevox.py      # VoicevoxTTS class - VOICEVOX TTS (primary)
├── tts_engine.py        # TTSEngine class - Edge TTS (fallback)
├── player.py            # AudioPlayer class - Queued audio playback
├── gui.py               # VoiceBridgeGUI class - Tkinter GUI
├── requirements.txt     # Python dependencies
├── setup_guide.md       # User setup guide (Japanese)
└── AGENTS.md            # This file
```

## Architecture

### Core Pipeline (VoiceBridge class)

The application follows a threaded pipeline pattern:

```
Audio Capture → Transcription → Translation → TTS → Playback
     (Thread)      (Thread)       (Thread)    (Sync)  (Thread)
```

1. **AudioCapture** (`audio_capture.py` / `audio_capture_win.py`):
   - **macOS** (`audio_capture.py`): Captures audio from BlackHole device via sounddevice
   - **Windows** (`audio_capture_win.py`): Captures audio via WASAPI loopback (PyAudioWPatch)
   - OS detection in `main.py` selects the appropriate class at import time
   - Both share the same interface: `start()`, `stop()`, `get_chunk()`, `list_devices()`, `on_level`
   - Buffers audio in chunks (default 4 seconds)
   - Filters silence using RMS threshold
   - Queues audio chunks via `queue.Queue`
   - Reports RMS level via `on_level` callback for GUI display

2. **Transcriber** (`transcriber.py`):
   - Uses faster-whisper for speech recognition
   - Supports models: tiny, base, small, medium (default: small)
   - VAD (Voice Activity Detection) filters silence
   - Loads model lazily on first use

3. **Translator** (`translator.py`):
   - Uses deep-translator (Google Translate API)
   - Source: English → Target: Japanese
   - Built-in retry logic (max 3 retries with exponential backoff)

4. **TTS** (`tts_voicevox.py` / `tts_engine.py`):
   - **Primary: VoicevoxTTS** - Uses local VOICEVOX engine (`http://localhost:50021`)
     - 2-step API: `/audio_query` → `/synthesis`
     - Generates WAV files in temporary directory
     - Supports 50+ voices (ずんだもん, 四国めたん, etc.)
     - Speaker list fetched dynamically from VOICEVOX engine
     - Auto-recreates temp directory if deleted
   - **Fallback: TTSEngine** - Uses edge-tts (Microsoft Edge TTS)
     - Generates MP3 files in temporary directory
     - Supports voices: nanami (female), keita (male)
     - Async event loop for synthesis
   - TTS engine is selected automatically at startup based on VOICEVOX availability

5. **AudioPlayer** (`player.py`):
   - Uses pygame.mixer for playback (supports both WAV and MP3)
   - Queue-based audio sequencing
   - Deletes played files automatically
   - Prevents audio overlap by blocking until playback completes

### Threading Model

- **Main thread**: GUI event loop (or CLI main loop)
- **Pipeline thread**: Runs the capture→transcribe→translate→TTS pipeline
- **Audio capture thread**: sounddevice callback (managed by sounddevice)
- **Player thread**: pygame.mixer playback loop

All components communicate via thread-safe queues and callbacks.

### Monitoring Features

- **Audio Level Monitor**: RMS level displayed as a bar in GUI. Red threshold line shows silence cutoff
- **Latency Monitor**: Each pipeline step (transcription, translation, TTS) is timed. Total latency (including chunk accumulation) is displayed in GUI and logged to console

## Code Patterns

### Class Structure

All components follow similar patterns:

```python
class ComponentName:
    def __init__(self, config_params):
        # Initialize state, queues, config

    def start(self):
        # Start background threads

    def stop(self):
        # Cleanup, stop threads

    # Core functionality
    def process(self):
        # Main work
```

### Callback Pattern

VoiceBridge uses callbacks for GUI integration:

```python
bridge = VoiceBridge(...)
bridge.on_english_text = gui.add_english_text    # Callback for transcribed text
bridge.on_japanese_text = gui.add_japanese_text  # Callback for translated text
bridge.on_status_change = gui.set_status         # Callback for status updates
bridge.on_level = gui.set_level                  # Callback for audio level
bridge.on_latency = gui.set_latency              # Callback for latency info
```

### Thread-Safe Communication

GUI uses message queue pattern for thread-safe updates:

```python
# From worker thread (pipeline)
self._message_queue.put(("en", text))
self._message_queue.put(("ja", text))
self._message_queue.put(("status", "キャプチャ中..."))
self._message_queue.put(("level", (rms, is_active)))
self._message_queue.put(("latency", (total_sec, stage_detail)))

# In main thread (GUI)
def _process_messages(self):
    while not self._message_queue.empty():
        msg_type, data = self._message_queue.get_nowait()
        # Update UI
```

### Error Handling

- Each pipeline stage wraps operations in try/except
- Errors are logged but don't crash the pipeline (continues to next chunk)
- Translation has explicit retry logic for network failures
- VoicevoxTTS auto-recreates temp directory if it was deleted

## Configuration

### Audio Device Configuration

Platform-specific audio capture:

```python
# macOS: Requires BlackHole virtual audio device
DEFAULT_DEVICE = "BlackHole 2ch"  # sounddevice

# Windows: Uses WASAPI loopback (no extra software needed)
DEFAULT_DEVICE = "default"  # PyAudioWPatch auto-detects loopback device

# Available devices can be listed with:
python main.py --list-devices
```

### Whisper Model Configuration

```python
# Available models (trade speed vs accuracy)
model_size = "tiny"    # Fastest, lowest accuracy
model_size = "base"    # Fast
model_size = "small"   # Balanced (default)
model_size = "medium"  # Slower, higher accuracy
model_size = "large-v2" # Slowest, highest accuracy
```

### TTS Configuration

```python
# VOICEVOX (primary - requires VOICEVOX app running)
# Speaker list is fetched dynamically from http://localhost:50021/speakers
# Common speaker IDs:
#   3 = ずんだもん（ノーマル）
#   2 = 四国めたん（ノーマル）
#   8 = 春日部つむぎ

# Edge TTS (fallback - requires internet)
voice = "nanami"  # Female voice (default)
voice = "keita"   # Male voice
```

### Audio Chunk Configuration

```python
# Chunk duration in seconds
chunk_duration = 4.0  # Default
# Shorter chunks = less latency but more processing overhead
# Longer chunks = more context but higher latency
```

## Naming Conventions

- **Files**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions/Methods**: `snake_case`
- **Private members**: `_leading_underscore`
- **Constants**: `UPPER_SNAKE_CASE` or just capitalized within classes
- **Comments and docstrings**: Japanese (target audience is Japanese speakers)

## Important Gotchas

### macOS-Specific Requirements

1. **BlackHole Installation**: Required for system audio capture
   - Install via Homebrew: `brew install blackhole-2ch`
   - Must create a "composite device" with BlackHole + speakers in Audio MIDI Setup

2. **Audio Device Selection**: macOS sound output must be set to the composite device (not BlackHole alone)

### Windows-Specific Requirements

1. **WASAPI Loopback**: No extra software needed for audio capture
   - PyAudioWPatch automatically detects the default loopback device
   - Device name "default" uses `get_default_wasapi_loopback()`

2. **Resampling**: Windows audio devices may run at 44100Hz or 48000Hz
   - `audio_capture_win.py` auto-resamples to 16000Hz for Whisper
   - Multi-channel audio is mixed down to mono

### VOICEVOX Integration

- VOICEVOX app must be running before Voice Bridge startup for auto-detection
- If VOICEVOX is not running, Edge TTS is used automatically (no error)
- VOICEVOX speaker list is fetched once at startup via `/speakers` endpoint
- Changing voice in GUI sends speaker_id to VoicevoxTTS via `set_speaker()`
- VOICEVOX outputs WAV files; Edge TTS outputs MP3 files. Both are handled by pygame.mixer
- Temp directory auto-recreates if deleted by OS or cleanup

### VOICEVOX 利用表記（クレジット）

VOICEVOX の利用規約 (https://voicevox.hiroshiba.jp/term/) に基づき、クレジット表記が必要:
- GUI 下部に `VOICEVOX:キャラクター名` を自動表示（`gui.py` の `_credit_label`）
- 声の切り替え時にキャラクター名を動的に更新（`main.py` の `on_voice_change`）
- `gui.set_credit(text)` で表記テキストを設定
- 配信・動画利用時は概要欄等にも `VOICEVOX:キャラクター名` の記載が必要

### Model Loading

- Whisper models are loaded **lazily** on first transcription call
- Changing model size sets `_model = None` to trigger reload on next use
- First transcription after model change will be slow (download + load)

### Temporary Files

- VoicevoxTTS creates WAV files in `tempfile.mkdtemp(prefix="voice_bridge_vv_")`
- TTSEngine creates MP3 files in `tempfile.mkdtemp(prefix="voice_bridge_")`
- Files are automatically deleted after playback
- Cleanup is called on `bridge.stop()`
- If temp dir is deleted externally, VoicevoxTTS recreates it on next synthesize call

### Audio Overlap Prevention

- AudioPlayer blocks on playback to prevent overlapping audio
- This can cause queue buildup if processing is faster than playback
- Long translated text = longer playback = potential queue delay

### Silence Detection

- AudioCapture uses RMS threshold to filter silence
- Default threshold: `silence_threshold = 0.01`
- Chunks below threshold are discarded (not queued for processing)
- RMS level is reported to GUI via `on_level` callback

## Testing

No test suite exists. Manual testing approach:

```bash
# Test each module individually
python audio_capture.py     # Verify device detection
python transcriber.py       # Verify model loads
python translator.py        # Verify translation works
python tts_engine.py        # Verify Edge TTS generates files
python tts_voicevox.py      # Verify VOICEVOX connection & speaker list

# Full integration test
python main.py --cli        # Run with console output
```

## Debugging

### Enable Debug Output

The CLI mode provides verbose console output:

```bash
python main.py --cli
```

Shows:
- `[EN]` recognized English text
- `[JA]` translated Japanese text
- `[Latency]` per-stage timing breakdown (認識=Xs 翻訳=Xs TTS=Xs 処理計=Xs 実質遅延=Xs)
- `[Pipeline]` pipeline status/errors
- `[AudioCapture]` device status and errors
- `[VoicevoxTTS]` / `[TTSEngine]` TTS status
- Component lifecycle messages (start/stop, model load, etc.)

### GUI Debugging

- **Input Level bar**: Shows real-time RMS. Red line = silence threshold (0.01)
  - No movement → audio not reaching BlackHole (macOS) or WASAPI loopback (Windows)
  - Movement but below red line → audio too quiet
  - Green bar past red line → audio being processed
- **Latency display**: Shows total delay and per-stage breakdown

### Common Issues

**Audio not captured (macOS):**
- Verify BlackHole is installed: `brew list | grep blackhole`
- Check macOS sound output is set to composite device
- Run `python main.py --list-devices` to verify device detection
- Check GUI level bar for any movement

**Audio not captured (Windows):**
- Run `python main.py --list-devices` to check for WASAPI loopback devices
- Ensure audio is playing through the default output device
- Check that PyAudioWPatch is installed: `pip show PyAudioWPatch`

**Poor transcription accuracy:**
- Try larger model: `--model medium`
- Ensure clear speech, minimal background noise

**High latency:**
- Try smaller model: `--model tiny` or `--model base`
- Reduce chunk size: `--chunk 2.0`
- Check latency display for per-stage breakdown

**Translation errors:**
- Check internet connection (Google Translate API)
- Watch console for retry messages

**VOICEVOX not detected:**
- Ensure VOICEVOX app is running before starting Voice Bridge
- Test: `curl http://localhost:50021/version`
- Check firewall settings for localhost:50021

**VOICEVOX synthesis errors:**
- Check VOICEVOX app is still running (may disconnect after sleep)
- Temp directory auto-recreates if deleted

**TTS fails (Edge TTS fallback):**
- Check internet connection (Edge TTS requires internet)
- Verify voice name is valid

## Dependencies

| Package | Purpose |
|---------|---------|
| faster-whisper | Whisper speech recognition (CPU/GPU) |
| deep-translator | Google Translate API wrapper |
| edge-tts | Microsoft Edge TTS API (fallback) |
| sounddevice | Audio input via PortAudio (macOS) |
| PyAudioWPatch | WASAPI loopback audio capture (Windows) |
| pygame | Audio playback (pygame.mixer) |
| numpy | Audio data processing |
| requests | HTTP requests for VOICEVOX API |

All dependencies are listed in `requirements.txt`. No version constraints specified. Platform-specific packages use environment markers (`sys_platform`).

## Adding Features

### Adding a New Audio Source

1. Create a new `audio_capture_*.py` module matching the `AudioCapture` interface (see `audio_capture.py` or `audio_capture_win.py`)
2. Required interface: `start()`, `stop()`, `get_chunk(timeout)`, `list_devices()` (static), `on_level` callback
3. Add OS/platform detection in `main.py` to import the new module
4. Add configuration option to `VoiceBridge.__init__()`

### Adding a New TTS Engine

1. Create a new `tts_*.py` module with `synthesize()` and `cleanup()` methods
2. Add detection logic in `main.py` (similar to VOICEVOX auto-detection)
3. Update `VoiceBridge.__init__()` to support the new engine
4. Update GUI voice dropdown population in `run_gui()`

### Adding a New Whisper Model

1. Add to `Transcriber.AVAILABLE_MODELS` list
2. Update GUI dropdown in `gui.py`
3. Add to CLI argument choices in `main.py`

### Changing Translation Language

1. Modify `Translator.__init__(source, target)` defaults
2. Update documentation and comments

## Performance Considerations

### Pipeline Bottlenecks

1. **Chunk accumulation** (fixed):
   - Default: 4.0 seconds of audio buffered before processing

2. **Whisper transcription** (slowest):
   - Small model: ~1-2 seconds per 4-second chunk
   - Medium model: ~2-4 seconds per 4-second chunk

3. **Translation** (fast):
   - Google Translate: ~0.3-1 second

4. **TTS synthesis** (medium):
   - VOICEVOX: ~0.3-1 second (local, no network)
   - Edge TTS: ~0.5-1 second (network dependent)

5. **Playback** (variable):
   - Depends on text length and speech rate

### Typical Total Latency

- With `small` model + VOICEVOX: ~6-8 seconds from speech to Japanese audio
- With `tiny` model + VOICEVOX: ~5-6 seconds

### Optimization Strategies

- Use smaller Whisper models for lower latency
- Reduce chunk size for faster response (but more context lost)
- Use VOICEVOX (local) instead of Edge TTS (network) for faster TTS
- Disable silence filtering for more aggressive capture

## Code Style

- Type hints used throughout
- Japanese docstrings and comments
- Clear separation of concerns (one responsibility per class)
- Thread-safe patterns (queues, locks)
- Clean error handling (try/except with logging)

## Notes for Agents

- **Language**: All user-facing text, docstrings, and comments are in Japanese. Preserve this when making changes.
- **Platform**: Supports macOS (BlackHole + sounddevice) and Windows (WASAPI loopback + PyAudioWPatch). Audio capture is the only platform-specific component; all other modules are cross-platform.
- **Dependencies**: Don't add new dependencies without justification. Keep the stack lightweight.
- **Testing**: No automated tests exist. Manual testing is required for changes.
- **GUI**: Uses tkinter with custom dark theme colors (#1e1e2e, #cdd6f4, etc.). Maintain the theme consistency.
- **Threading**: All audio processing is threaded. Be careful with shared state - use queues for communication.
- **TTS Engine Selection**: VOICEVOX is primary (auto-detected at startup). Edge TTS is fallback. Both produce audio files consumed by the same AudioPlayer.
