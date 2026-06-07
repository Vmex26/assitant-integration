"""
File system tools for the AI agent.

Allows the AI to read and write files on the local filesystem.
"""

from pathlib import Path
from typing import Any

from .base import BaseTool


class ReadFileTool(BaseTool):
    """Read the contents of a file."""

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return (
            "Read the contents of a file at the specified path. "
            "Use this to view source code, configuration files, or any text file."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute path to the file to read",
                },
                "offset": {
                    "type": "integer",
                    "description": "Line number to start reading from (1-indexed)",
                    "default": 0,
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of lines to read",
                    "default": 2000,
                },
            },
            "required": ["file_path"],
        }

    async def execute(self, file_path: str, offset: int = 0, limit: int = 2000) -> str:
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            return f"Error: File not found: {file_path}"
        if not path.is_file():
            return f"Error: Not a file: {file_path}"

        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except PermissionError:
            return f"Error: Permission denied reading: {file_path}"

        total_lines = len(lines)
        if offset > 0:
            lines = lines[offset - 1 :]
        if limit > 0:
            lines = lines[:limit]

        content = "".join(lines)
        output = f"File: {path}\n"
        output += f"Size: {total_lines} lines\n"
        if offset > 0 or limit < total_lines:
            start = offset or 1
            end = min(start + len(lines) - 1, total_lines)
            output += f"Showing lines {start}-{end} of {total_lines}\n"
        output += "---\n"
        output += content
        if not content.endswith("\n"):
            output += "\n"
        output += "---"
        return output


class WriteFileTool(BaseTool):
    """Write content to a file."""

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write content to a file. Creates the file and any necessary parent directories."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Absolute path where to write the file",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
            },
            "required": ["file_path", "content"],
        }

    async def execute(self, file_path: str, content: str) -> str:
        path = Path(file_path).expanduser().resolve()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote {len(content)} bytes to: {path}"
        except PermissionError:
            return f"Error: Permission denied writing to: {file_path}"
        except OSError as e:
            return f"Error writing file: {e}"


class ListDirectoryTool(BaseTool):
    """List contents of a directory."""

    @property
    def name(self) -> str:
        return "list_directory"

    @property
    def description(self) -> str:
        return "List files and directories at a given path."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute path to the directory",
                },
            },
            "required": ["path"],
        }

    async def execute(self, path: str) -> str:
        dir_path = Path(path).expanduser().resolve()
        if not dir_path.exists():
            return f"Error: Path not found: {path}"
        if not dir_path.is_dir():
            return f"Error: Not a directory: {path}"

        try:
            entries = sorted(dir_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            return f"Error: Permission denied: {path}"

        lines = [f"Directory: {dir_path}", ""]
        for entry in entries:
            suffix = "/" if entry.is_dir() else ""
            try:
                size = entry.stat().st_size if entry.is_file() else 0
                size_str = f" ({size} bytes)" if size > 0 else ""
                lines.append(f"  {entry.name}{suffix}{size_str}")
            except OSError:
                lines.append(f"  {entry.name}{suffix} [?]")

        return "\n".join(lines)
