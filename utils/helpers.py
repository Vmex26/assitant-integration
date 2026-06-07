"""
Utility helpers for the AI assistant application.

Provides common functions for formatting, file handling,
and system interaction.
"""

import os
import re
from pathlib import Path


def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """Truncate text to a maximum length with a suffix."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def safe_filename(name: str) -> str:
    """Convert a string to a safe filename."""
    safe = re.sub(r"[^\w\-_. ]", "_", name)
    return safe.strip() or "untitled"


def format_file_size(size_bytes: float) -> str:
    """Format a file size in human-readable format."""
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def get_supported_image_extensions() -> list[str]:
    """Get list of supported image file extensions."""
    return [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]


def get_supported_file_extensions() -> list[str]:
    """Get list of supported document file extensions."""
    return [
        ".txt",
        ".md",
        ".py",
        ".js",
        ".ts",
        ".html",
        ".css",
        ".json",
        ".xml",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
        ".ps1",
        ".bat",
        ".cmd",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".java",
        ".kt",
        ".swift",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".pl",
        ".lua",
        ".r",
        ".sql",
        ".pdf",
        ".csv",
        ".tsv",
    ]


def is_image_file(file_path: str) -> bool:
    """Check if a file is a supported image."""
    ext = Path(file_path).suffix.lower()
    return ext in get_supported_image_extensions()


def is_text_file(file_path: str) -> bool:
    """Check if a file is likely a text file."""
    ext = Path(file_path).suffix.lower()
    # Common text extensions
    text_extensions = set(get_supported_file_extensions()) - {".pdf"}
    if ext in text_extensions:
        return True
    # Try to detect by reading
    try:
        with open(file_path, encoding="utf-8") as f:
            f.read(1024)
        return True
    except OSError, UnicodeDecodeError:
        return False


def format_api_error(error_text: str, provider: str = "API") -> str:
    """Translate raw API errors into user-friendly messages."""
    error_lower = error_text.lower()

    if "429" in error_text or "resource_exhausted" in error_lower or "quota" in error_lower:
        return (
            f"**{provider} - Quota exceeded**\n\n"
            "You have reached the rate or daily limit for this API. "
            "Possible solutions:\n"
            "- Wait a few minutes and try again\n"
            "- Check your usage at the provider's dashboard\n"
            "- Upgrade to a paid plan if available\n"
            "- Switch to a different model in Settings"
        )
    if "403" in error_text or "permission_denied" in error_lower:
        return (
            f"**{provider} - Access denied**\n\n"
            "The API key does not have permission for this operation. "
            "Check your API key and permissions in Settings (Ctrl+,)."
        )
    if (
        "401" in error_text
        or "unauthenticated" in error_lower
        or ("invalid" in error_lower and "key" in error_lower)
    ):
        return (
            f"**{provider} - Invalid credentials**\n\n"
            "The API key is missing or invalid. "
            "Go to Settings (Ctrl+,) and configure a valid API key."
        )
    if "404" in error_text or "not found" in error_lower and "model" in error_lower:
        return (
            f"**{provider} - Model not found**\n\n"
            "The selected model is not available. "
            "Check the model name in Settings (Ctrl+,) or switch to a different model."
        )
    if "timeout" in error_lower or "timed out" in error_lower:
        return (
            f"**{provider} - Request timed out**\n\n"
            "The request took too long to complete. Try again or send a shorter message."
        )
    if "connection" in error_lower and (
        "refused" in error_lower or "reset" in error_lower or "error" in error_lower
    ):
        return (
            f"**{provider} - Connection failed**\n\n"
            "Could not connect to the API. Check your internet connection "
            "and if the service is available."
        )
    if "500" in error_text or "503" in error_text or "server error" in error_lower:
        return (
            f"**{provider} - Server error**\n\n"
            "The API server encountered an error. Try again later."
        )

    # Generic fallback
    # Extract just the first line or short message
    first_line = error_text.split("\\n")[0].split("\n")[0][:150]
    return f"**{provider} - Error**\n\n{first_line}"


def find_project_root(path: str | None = None) -> Path:
    """Find the project root by looking for common markers."""
    start = Path(path or os.getcwd()).resolve()
    markers = [".git", "README.md", "setup.py", "pyproject.toml", "package.json"]
    for parent in [start] + list(start.parents):
        for marker in markers:
            if (parent / marker).exists():
                return parent
    return start
