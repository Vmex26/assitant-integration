"""
Model manager - factory and registry for AI providers.

Handles provider instantiation, switching, and lifecycle.
"""

import traceback
from typing import Any, Dict, Optional, Tuple, Type

from core.config import Config
from core.providers.base import BaseProvider
from core.providers.openai_provider import OpenAIProvider
from core.providers.anthropic_provider import AnthropicProvider
from core.providers.ollama_provider import OllamaProvider
from core.providers.gemini_provider import GeminiProvider
from core.providers.openai_compatible_provider import OpenAICompatibleProvider


class ProviderError(Exception):
    """Raised when a provider fails to initialize or operate."""
    pass


class ModelManager:
    """Manages AI model provider instances."""

    _providers: Dict[str, Type[BaseProvider]] = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "ollama": OllamaProvider,
        "gemini": GeminiProvider,
        "openai_compatible": OpenAICompatibleProvider,
    }

    def __init__(self, config: Config):
        self.config = config
        self._instances: Dict[str, BaseProvider] = {}

    @classmethod
    def register_provider(cls, name: str, provider_cls: Type[BaseProvider]) -> None:
        """Register a new provider type (plugin system)."""
        cls._providers[name] = provider_cls

    @classmethod
    def available_providers(cls) -> Dict[str, Type[BaseProvider]]:
        """Get all registered provider types."""
        return dict(cls._providers)

    def get_provider(self, name: Optional[str] = None) -> Tuple[Optional[BaseProvider], Optional[str]]:
        """Get or create a provider instance by name.

        Returns (provider, None) on success, or (None, error_message) on failure.
        """
        provider_name = name or self.config.active_provider
        if provider_name not in self._instances:
            provider_cls = self._providers.get(provider_name)
            if not provider_cls:
                return None, f"Unknown provider: {provider_name}. Available: {list(self._providers.keys())}"
            provider_config = self.config.provider_config(provider_name)
            try:
                self._instances[provider_name] = provider_cls(provider_config)
            except Exception as e:
                error_msg = f"Failed to initialize {provider_name}: {e}"
                print(f"Provider init error: {error_msg}\n{traceback.format_exc()}")
                return None, error_msg
        return self._instances[provider_name], None

    def switch_provider(self, name: str) -> Tuple[Optional[BaseProvider], Optional[str]]:
        """Switch the active provider and return its instance.

        Returns (provider, None) on success, or (None, error_message) on failure.
        """
        if name not in self._providers:
            return None, f"Unknown provider: {name}. Available: {list(self._providers.keys())}"
        self.config.active_provider = name
        return self.get_provider(name)

    def reload_provider(self, name: Optional[str] = None) -> Tuple[Optional[BaseProvider], Optional[str]]:
        """Force reload a provider's configuration."""
        provider_name = name or self.config.active_provider
        self._instances.pop(provider_name, None)
        return self.get_provider(provider_name)

    def refresh_all(self) -> None:
        """Re-create all provider instances with current config."""
        self._instances.clear()
