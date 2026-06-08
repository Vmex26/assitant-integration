# AI Assistant Integrer

A desktop AI assistant for **Linux beginners and power users alike** — chat with an AI that can read/write files, run commands, search the web, talk to you by voice, and explain what's happening on your system. Think of it as a friendly system administrator that lives in your taskbar.

## Philosophy

This project is built for people who use Linux and sometimes get stuck. Whether you hit a cryptic error, need to understand why a command works (or doesn't), or just want to explore what your system can do — the assistant is here to help in plain language.

- **Beginner-friendly, not condescending** — a Linux beginner is not a computer beginner. The assistant uses common sense: safe actions (reading files, listing directories) run directly; risky actions require confirmation.
- **Risk-based confirmation**:
  - **Low risk** (read files, list directories, create new files in user space) — proceeds directly, informs you after
  - **Medium risk** (modify existing files, install packages) — explains and asks before proceeding
  - **High risk** (sudo, destructive commands, system files) — detailed explanation + explicit confirmation required
- **System-aware** — knows your OS, kernel, CPU, memory, desktop environment, and shell
- **Safe by default** — commands with `sudo` require explicit user confirmation (Smart Sudo protocol)
- **Privacy-conscious** — run local models via Ollama, no data leaves your machine unless you choose an API provider

## Features

- **Multi-provider** — OpenAI, Anthropic (Claude), Google Gemini, Ollama (local), and OpenAI-Compatible endpoints
- **Voice Call Mode** — press `Ctrl+Shift+Space` to start a hands-free conversation with speech recognition (faster-whisper) and text-to-speech (edge-tts)
- **System interaction** — read/write files, run shell commands, search files, install packages, fetch web pages, search the web
- **Smart Sudo** — detects `sudo` usage, requires explicit user confirmation for privileged commands
- **Software Assistant** — ask for any application in natural language, get Linux alternatives with install guidance
- **AUR Audit** — shows PKGBUILD and package info before suggesting AUR installations
- **System Health Panel** — real-time CPU, memory, disk, and service status sidebar
- **Sudo support** — KDE-native password dialog (`kdialog`) for privileged commands
- **Multimodal attachments** — paste or attach images and files (sent to the model when supported)
- **Streaming responses** — see the AI reply token by token
- **Conversation persistence** — automatic save/restore via SQLite
- **Conversation management** — rename, delete, and switch between conversations; auto-generated titles
- **Stop generation** — cancel the AI mid-response
- **Dark theme** — easy on the eyes
- **Suggestion chips** — quick prompts to start a conversation
- **System-aware prompt** — the AI automatically knows your hardware and software environment

## Requirements

- Python 3.11+
- PyQt6
- A supported AI provider (at least one):
  - OpenAI API key
  - Anthropic API key
  - Google Gemini API key
  - Ollama (local, no API key needed)
  - OpenAI-Compatible endpoint (e.g., Groq, OpenRouter, LM Studio)
- For Voice Call Mode:
  - A working microphone
  - Internet access (for edge-tts)

## Installation

```bash
git clone git@github.com:Vmex26/assitant-integration.git
cd assitant-integration
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run

```bash
./run.sh
```

Or directly:

```bash
source venv/bin/activate && python3 main.py
```

## Configuration

On first launch, open **Settings** (`Ctrl+,` or `Edit > Settings...`) and configure at least one provider:

| Provider | API Key | Notes |
|----------|---------|-------|
| OpenAI   | Required | `gpt-4o`, `gpt-4o-mini`, etc. |
| Anthropic | Required | `claude-sonnet-4`, `claude-haiku-3`, etc. |
| Gemini   | Required | `gemini-2.5-flash`, `gemini-2.5-pro`, etc. |
| Ollama   | Not needed | Local models, configure base URL and model name |
| OpenAI-Compatible | Optional | Custom endpoint (Groq, OpenRouter, LM Studio, etc.) |

You can also enable/disable individual tools and change the appearance theme.

## Voice Call Mode

Press **`Ctrl+Shift+Space`** (while the app is focused) or click the **phone icon** in the chat toolbar to start a voice call:

1. The assistant greets you and listens
2. Speak naturally — silence detection automatically ends your turn
3. The AI replies with speech (edge-tts)
4. Say **"termina la llamada"**, **"cuelga"**, **"end the call"**, or **"hang up"** to stop

The AI can still run commands, read files, and use tools during a voice call.

## Usage

1. Type a message in natural language — ask about an error, a command you don't understand, or something about your system
2. The AI reads files, runs commands, and searches the web on its own — it does not ask you to open a terminal
3. Confirmation behavior depends on risk level:
   - **Low risk** (reading files, listing directories) — runs directly, you see the result
   - **Medium risk** (modifying files, installing packages) — the AI explains and asks before proceeding
   - **High risk** (sudo, destructive commands) — detailed explanation + confirmation required
4. Click **Stop** (red button) to cancel the AI mid-generation
5. Switch between conversations in the left sidebar
6. Right-click a conversation to **Rename** or **Delete** it
7. Attach files with the paperclip button or paste images from clipboard
8. Press **`Ctrl+Shift+Space`** to instantly start a voice call

## Project Structure

```
ai-assistant-integrer/
├── main.py                  # Application entry point
├── run.sh                   # Launch script
├── requirements.txt         # Python dependencies
├── core/
│   ├── audio.py             # Voice recording (sounddevice), transcription (whisper), TTS (edge-tts)
│   ├── config.py            # JSON configuration management
│   ├── conversation.py      # Conversation and message models (thread-safe)
│   ├── logger.py            # Logging utilities
│   ├── model_manager.py     # Provider factory/registry
│   ├── storage.py           # SQLite persistence layer
│   ├── providers/
│   │   ├── base.py          # Abstract provider interface
│   │   ├── openai_provider.py
│   │   ├── anthropic_provider.py
│   │   ├── ollama_provider.py
│   │   ├── gemini_provider.py
│   │   └── openai_compatible_provider.py
│   └── tools/
│       ├── base.py          # Abstract tool interface
│       ├── file_tools.py    # read_file, write_file, list_directory
│       ├── command_tools.py # execute_command (with Smart Sudo), execute_python
│       ├── package_tools.py # search_package, show_pkgbuild (AUR audit)
│       ├── search_tools.py  # glob_search, content_search
│       ├── software_assistant.py  # Natural language software search
│       └── web_tools.py     # web_fetch, web_search, download_file
├── gui/
│   ├── main_window.py       # Main window, menus, sidebar, global hotkey
│   ├── chat_widget.py       # Chat interface, input, streaming, voice call UI
│   ├── message_widget.py    # Message bubble with markdown rendering
│   ├── system_panel.py      # Real-time system health display
│   ├── log_dialog.py        # Log viewer dialog
│   ├── service_dialog.py    # Service monitoring dialog
│   └── settings_dialog.py   # Provider and appearance settings
├── utils/
│   └── helpers.py           # Error formatting, markdown rendering, shared utilities
└── tests/
    ├── test_config.py
    ├── test_conversation.py
    ├── test_helpers.py
    ├── test_logger.py
    ├── test_markdown.py
    ├── test_providers_base.py
    ├── test_storage.py
    ├── test_tools_base.py
    └── test_tools_software_assistant.py
```

## Technologies

- **UI Framework:** PyQt6
- **Async:** asyncio (background QThread)
- **Voice:** sounddevice (recording), faster-whisper (speech-to-text), edge-tts (text-to-speech)
- **Storage:** SQLite (via `sqlite3`)
- **Markdown:** Custom HTML converter (regex-based)
- **Audio processing:** numpy, soundfile

## Smart Sudo Protocol

When the assistant needs to run a command with `sudo`:

1. It explains exactly why sudo is needed
2. If you **explicitly** asked for the command, it runs directly with your consent
3. If the assistant inferred sudo is necessary, it asks for confirmation (with a visual dialog)
4. The actual password dialog is handled by the system (kdialog/zenity)

## Software Assistant

Ask about any application in natural language:

- *"How do I edit PDFs?"*
- *"¿Qué programa uso para grabar la pantalla?"*
- *"Find a Spotify client for Linux"*

The assistant searches the web for Linux alternatives, checks if they're available in your repos, shows AUR packages with PKGBUILD info, and guides you through installation.

## License

MIT
