# AI Assistant Integrer

A desktop AI assistant for **Linux beginners and power users alike** — chat with an AI that can read/write files, run commands, search the web, and explain what's happening on your system. Think of it as a friendly system administrator that lives in your taskbar.

## Philosophy

This project is built for people who use Linux and sometimes get stuck. Whether you hit a cryptic error, need to understand why a command works (or doesn't), or just want to explore what your system can do — the assistant is here to help in plain language.

- **Beginner-friendly, not condescending** — a Linux beginner is not a computer beginner. The assistant uses common sense: safe actions (reading files, listing directories) run directly; risky actions require confirmation.
- **Risk-based confirmation**:
  - **Low risk** (read files, list directories, create new files in user space) — proceeds directly, informs you after
  - **Medium risk** (modify existing files, install packages) — explains and asks before proceeding
  - **High risk** (sudo, destructive commands, system files) — detailed explanation + explicit confirmation required
- **System-aware** — knows your OS, kernel, CPU, memory, desktop environment, and shell
- **Safe by default** — commands with `sudo` trigger a graphical password dialog
- **Privacy-conscious** — run local models via Ollama, no data leaves your machine unless you choose an API provider

## Features

- **Multi-provider** — OpenAI, Anthropic (Claude), Google Gemini, or local models via Ollama
- **System interaction** — read/write files, run shell commands, search files, fetch web pages, search the web
- **Command confirmation** — low-risk actions run directly, medium-risk asks, high-risk requires explicit approval
- **Sudo support** — KDE-native password dialog (`kdialog`) for privileged commands
- **Multimodal attachments** — paste or attach images and files (sent to the model when supported)
- **Streaming responses** — see the AI reply token by token
- **Conversation persistence** — automatic save/restore via SQLite
- **Stop generation** — cancel the AI mid-response
- **Dark theme** — easy on the eyes
- **System-aware prompt** — the AI automatically knows your hardware and software environment
- **Conversation management** — rename, delete, and switch between conversations

## Requirements

- Python 3.11+
- PyQt6
- A supported AI provider (at least one):
  - OpenAI API key
  - Anthropic API key
  - Google Gemini API key
  - Ollama (local, no API key needed)

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

You can also enable/disable individual tools and change the appearance theme.

## Usage

1. Type a message in natural language — ask about an error, a command you don't understand, or something about your system
2. The AI reads files, runs commands, and searches the web on its own — it does not ask you to open a terminal
3. Confirmation behavior depends on risk level:
   - **Low risk** (reading files, listing directories) — runs directly, you see the result
   - **Medium risk** (modifying files, installing packages) — the AI explains and asks before proceeding
   - **High risk** (sudo, destructive commands) — detailed explanation + password dialog required
4. Click **Stop** (red button) to cancel the AI mid-generation
5. Switch between conversations in the left sidebar
6. Right-click a conversation to **Rename** or **Delete** it
7. Attach files with the paperclip button or paste images from clipboard

## Project Structure

```
ai-assistant-integrer/
├── main.py                  # Application entry point
├── run.sh                   # Launch script
├── requirements.txt         # Python dependencies
├── core/
│   ├── config.py            # JSON configuration management
│   ├── conversation.py      # Conversation and message models
│   ├── model_manager.py     # Provider factory/registry
│   ├── storage.py           # SQLite persistence layer
│   ├── providers/
│   │   ├── base.py          # Abstract provider interface
│   │   ├── openai_provider.py
│   │   ├── anthropic_provider.py
│   │   ├── ollama_provider.py
│   │   └── gemini_provider.py
│   └── tools/
│       ├── base.py          # Abstract tool interface
│       ├── file_tools.py    # read_file, write_file, list_directory
│       ├── command_tools.py # execute_command, execute_python
│       ├── search_tools.py  # glob_search, content_search
│       └── web_tools.py     # web_fetch, web_search, download_file
├── gui/
│   ├── main_window.py       # Main window, menus, sidebar
│   ├── chat_widget.py       # Chat interface, input, streaming
│   ├── message_widget.py    # Message bubble with markdown rendering
│   └── settings_dialog.py   # Provider and appearance settings
└── utils/
    └── helpers.py           # Error formatting, shared utilities
```

## Technologies

- **Framework:** PyQt6
- **Async:** asyncio (background QThread)
- **Storage:** SQLite (via `sqlite3`)
- **Markdown:** Custom HTML converter (regex-based)

## License

MIT
