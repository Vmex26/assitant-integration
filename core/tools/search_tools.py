"""
Code search tools for the AI agent.

Allows the AI to search through codebases using glob patterns
and content search (grep-like functionality).
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseTool


class GlobSearchTool(BaseTool):
    """Search for files by glob pattern."""

    @property
    def name(self) -> str:
        return "glob_search"

    @property
    def description(self) -> str:
        return "Search for files matching a glob pattern. Use this to find files by name or extension."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to match (e.g. 'src/**/*.py', '*.tsx')",
                },
                "path": {
                    "type": "string",
                    "description": "Root directory to search in (default: current directory)",
                },
            },
            "required": ["pattern"],
        }

    async def execute(self, pattern: str, path: str = "") -> str:
        search_path = Path(path).expanduser().resolve() if path else Path.cwd()
        if not search_path.exists():
            return f"Error: Path not found: {path}"
        if not search_path.is_dir():
            return f"Error: Not a directory: {path}"

        try:
            matches = sorted(search_path.rglob(pattern))
        except (PermissionError, OSError) as e:
            return f"Error searching: {e}"

        if not matches:
            return f"No files matching '{pattern}' found in {search_path}"

        # Limit output to prevent large responses
        max_results = 100
        total = len(matches)
        if total > max_results:
            matches = matches[:max_results]

        lines = [f"Found {total} files matching '{pattern}' in {search_path}:"]
        for m in matches:
            try:
                rel = m.relative_to(search_path)
                lines.append(f"  {rel}")
            except ValueError:
                lines.append(f"  {m}")

        if total > max_results:
            lines.append(f"... and {total - max_results} more")

        return "\n".join(lines)


class ContentSearchTool(BaseTool):
    """Search file contents using regex patterns."""

    @property
    def name(self) -> str:
        return "content_search"

    @property
    def description(self) -> str:
        return "Search file contents using a regular expression. Use this to find code patterns, function definitions, or specific text across files."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regular expression pattern to search for",
                },
                "include": {
                    "type": "string",
                    "description": "File glob pattern to include (e.g. '*.py', '*.{ts,tsx}')",
                },
                "path": {
                    "type": "string",
                    "description": "Root directory to search in (default: current directory)",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 50)",
                    "default": 50,
                },
            },
            "required": ["pattern"],
        }

    async def execute(self, pattern: str, include: str = "", path: str = "", max_results: int = 50) -> str:
        search_path = Path(path).expanduser().resolve() if path else Path.cwd()
        if not search_path.exists():
            return f"Error: Path not found: {path}"

        try:
            compiled = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            return f"Error: Invalid regex pattern: {e}"

        results: List[str] = []
        total_files = 0

        if include:
            from glob import iglob
            file_iter = iglob(include, root_dir=search_path, recursive=True)
        else:
            file_iter = (str(p.relative_to(search_path)) for p in search_path.rglob("*") if p.is_file())

        for rel_path in file_iter:
            if len(results) >= max_results:
                break

            full_path = search_path / rel_path
            if not full_path.is_file():
                continue

            try:
                if full_path.stat().st_size > 1024 * 1024:  # Skip files > 1MB
                    continue
                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    for i, line in enumerate(f, 1):
                        if compiled.search(line):
                            results.append(f"{rel_path}:{i}: {line.rstrip()[:200]}")
                            if len(results) >= max_results:
                                break
                    total_files += 1
            except (PermissionError, OSError):
                continue

        if not results:
            return f"No matches for '{pattern}' in {search_path}"

        output = f"Found {len(results)} matches for '{pattern}' in {search_path}:\n"
        output += "\n".join(results)
        return output
