import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def tmp_config_path(tmp_path: Path) -> Path:
    return tmp_path / ".ai_assistant" / "config.json"


@pytest.fixture
def sample_config_data() -> dict:
    return {
        "active_provider": "gemini",
        "theme": "light",
        "font_size": 14,
        "language": "en",
        "providers": {
            "gemini": {
                "api_key": "test-key",
                "model": "gemini-2.0-flash",
            },
        },
    }


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


@pytest.fixture
def sample_entry_data() -> dict:
    return {
        "role": "user",
        "content": "Hello",
        "tool_calls": None,
        "tool_call_id": None,
        "files": [],
    }
