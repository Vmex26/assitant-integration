"""
Configuration manager for the AI assistant application.

Handles loading, saving, and accessing application settings
such as API keys, model preferences, and UI settings.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_CONFIG_PATH = Path.home() / ".ai_assistant" / "config.json"


class Config:
    """Manages application configuration with JSON persistence."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self._data: Dict[str, Any] = self._defaults()
        self._load()

    @staticmethod
    def _defaults() -> Dict[str, Any]:
        return {
            "providers": {
                "openai": {
                    "api_key": "",
                    "model": "gpt-4o",
                    "temperature": 0.7,
                    "max_tokens": 4096,
                },
                "anthropic": {
                    "api_key": "",
                    "model": "claude-sonnet-4-20250514",
                    "temperature": 0.7,
                    "max_tokens": 4096,
                },
                "ollama": {
                    "base_url": "http://localhost:11434",
                    "model": "llama3",
                    "temperature": 0.7,
                    "max_tokens": 4096,
                },
                "gemini": {
                    "api_key": "",
                    "model": "gemini-2.0-flash",
                    "temperature": 0.7,
                    "max_tokens": 4096,
                },
                "openai_compatible": {
                    "api_key": "",
                    "base_url": "https://api.deepseek.com/v1",
                    "model": "deepseek-chat",
                    "temperature": 0.7,
                    "max_tokens": 4096,
                },
            },
            "active_provider": "openai",
            "theme": "dark",
            "font_size": 13,
            "language": "es",
            "max_history": 100,
            "tools_enabled": {
                "read_file": True,
                "write_file": True,
                "list_directory": True,
                "execute_command": True,
                "execute_python": True,
                "glob_search": True,
                "content_search": True,
                "web_fetch": True,
                "web_search": True,
                "download_file": True,
            },
        }

    def _load(self) -> None:
        """Load configuration from disk, merging with defaults."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    loaded = json.load(f)
                self._deep_merge(self._data, loaded)
            except (json.JSONDecodeError, IOError):
                pass

    def save(self) -> None:
        """Persist configuration to disk."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self._data, f, indent=2)

    @staticmethod
    def _deep_merge(base: Dict, override: Dict) -> None:
        """Recursively merge override dict into base dict."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                Config._deep_merge(base[key], value)
            else:
                base[key] = value

    def get(self, *keys: str, default: Any = None) -> Any:
        """Get a nested config value by key path."""
        current = self._data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    def set(self, *args: Any) -> None:
        """Set a nested config value.

        Usage: set('providers', 'openai', 'api_key', 'sk-...')
        The last argument is the value, all preceding are keys.
        """
        if len(args) < 2:
            return
        *keys, value = args
        current = self._data
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
        self.save()

    @property
    def active_provider(self) -> str:
        return self._data.get("active_provider", "openai")

    @active_provider.setter
    def active_provider(self, name: str) -> None:
        self._data["active_provider"] = name
        self.save()

    def provider_config(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Get configuration for a specific provider."""
        provider = name or self.active_provider
        return self._data.get("providers", {}).get(provider, {})

    @property
    def theme(self) -> str:
        return self._data.get("theme", "dark")

    @theme.setter
    def theme(self, value: str) -> None:
        self._data["theme"] = value
        self.save()

    @property
    def font_size(self) -> int:
        return self._data.get("font_size", 13)

    @font_size.setter
    def font_size(self, value: int) -> None:
        self._data["font_size"] = value
        self.save()

    @property
    def language(self) -> str:
        return self._data.get("language", "es")

    @language.setter
    def language(self, value: str) -> None:
        self._data["language"] = value
        self.save()

    @property
    def max_history(self) -> int:
        return self._data.get("max_history", 100)

    @property
    def tools_enabled(self) -> Dict[str, bool]:
        return self._data.get("tools_enabled", {})

    def is_tool_enabled(self, tool_name: str) -> bool:
        return self.tools_enabled.get(tool_name, True)
