import json
from pathlib import Path

from core.config import Config


def test_defaults_without_file(tmp_config_path: Path):
    config = Config(config_path=tmp_config_path)
    assert config.active_provider == "openai"
    assert config.theme == "dark"
    assert config.font_size == 13
    assert config.language == "es"
    assert config.verbose is False
    assert config.whisper_model_size == "small"
    assert config.max_history == 100


def test_merge_with_partial_file(tmp_config_path: Path, sample_config_data: dict):
    tmp_config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(tmp_config_path, "w") as f:
        json.dump(sample_config_data, f)

    config = Config(config_path=tmp_config_path)
    assert config.active_provider == "gemini"
    assert config.theme == "light"
    assert config.font_size == 14
    assert config.language == "en"
    assert config.verbose is False
    assert config.provider_config("gemini")["api_key"] == "test-key"


def test_set_nested_value(tmp_config_path: Path):
    config = Config(config_path=tmp_config_path)
    config.set("providers", "openai", "api_key", "sk-test")
    assert config.get("providers", "openai", "api_key") == "sk-test"


def test_properties_persist(tmp_config_path: Path):
    config = Config(config_path=tmp_config_path)
    config.theme = "light"
    config.font_size = 16

    config2 = Config(config_path=tmp_config_path)
    assert config2.theme == "light"
    assert config2.font_size == 16


def test_verbose_toggle(tmp_config_path: Path):
    config = Config(config_path=tmp_config_path)
    assert config.verbose is False
    config.verbose = True
    assert config.verbose is True


def test_provider_config_fallback(tmp_config_path: Path):
    config = Config(config_path=tmp_config_path)
    cfg = config.provider_config("nonexistent")
    assert cfg == {}


def test_is_tool_enabled(tmp_config_path: Path):
    config = Config(config_path=tmp_config_path)
    assert config.is_tool_enabled("read_file") is True
    assert config.is_tool_enabled("nonexistent") is True


def test_save_creates_parent_dir(tmp_config_path: Path):
    config = Config(config_path=tmp_config_path)
    config.save()
    assert tmp_config_path.exists()


def test_get_returns_default_for_missing_key(tmp_config_path: Path):
    config = Config(config_path=tmp_config_path)
    assert config.get("nonexistent", default="fallback") == "fallback"
