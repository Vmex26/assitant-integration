# AI Assistant Integrer

A modular, multi-provider AI assistant desktop GUI built with Python and PyQt6. Execute tools (files, commands, web), attach multimodal content, and persist conversations — all from a chat interface.

## Features

- **Multi-provider support** — OpenAI, Anthropic (Claude), Google Gemini, and local models via Ollama
- **Tool execution** — read/write files, run shell commands, search files, fetch web pages, search the web
- **Multimodal attachments** — paste or attach images and files; sent to the model when supported
- **Streaming responses** — see the AI reply token by token
- **Command confirmation** — explicit user approval before running shell commands
- **Sudo support** — KDE-native password dialog (`kdialog`) for `sudo` commands
- **Conversation persistence** — automatic save/restore via SQLite
- **Stop generation** — cancel the AI mid-response
- **Dark theme** — eye-friendly dark interface
- **System-aware prompt** — the AI knows your OS, CPU, memory, and desktop environment

## Requirements

- Python 3.11+
- PyQt6
- A supported AI provider (at least one):
  - OpenAI API key
  - Anthropic API key
  - Google Gemini API key
  - Ollama (local)

## Installation

### 1. Clone the repository
```bash
git clone git@github.com:Vmex26/assitant-integration.git
cd assitant-integration
```

### 2. Create a virtual environment (recommended)
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the application
```bash
./run.sh
```
Or directly:
```bash
source venv/bin/activate && python3 main.py
```

## Configuration

On first launch, open **Settings** (`Ctrl+,` or `Edit > Settings...`) and configure at least one provider:

| Provider | API Key Required | Notes |
|----------|-----------------|-------|
| OpenAI   | Yes             | `gpt-4o`, `gpt-4o-mini`, etc. |
| Anthropic | Yes            | `claude-sonnet-4`, `claude-haiku-3`, etc. |
| Gemini   | Yes             | `gemini-2.5-flash`, `gemini-2.5-pro`, etc. |
| Ollama   | No              | Runs local models, configure base URL and model name |

You can also enable/disable individual tools and change the appearance theme.

## Usage

1. Type a message in the input box and press **Enter** (or click **Send**)
2. The AI can use tools to read/write files, execute commands, search the web, etc.
3. Commands with `sudo` will trigger a KDE password dialog
4. Click **Stop** (red button) to cancel the AI mid-generation
5. Switch between conversations in the left sidebar
6. Attach files with the paperclip button or paste images from clipboard

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
│   └── providers/
│       ├── base.py          # Abstract provider interface
│       ├── openai_provider.py
│       ├── anthropic_provider.py
│       ├── ollama_provider.py
│       └── gemini_provider.py
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
