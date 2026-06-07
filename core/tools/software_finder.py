from .base import BaseTool
from typing import Any

class SoftwareFinderTool(BaseTool):
    """Find and suggest software packages based on a category."""

    @property
    def name(self) -> str:
        return "find_software"

    @property
    def description(self) -> str:
        return "Find and suggest software packages based on a category (e.g., 'text editor', 'web browser')."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "The category or type of software requested."
                }
            },
            "required": ["category"]
        }

    async def execute(self, category: str) -> str:
        # Simple mapping for beginners
        mapping = {
            "web browser": "firefox or chromium",
            "text editor": "gedit or kate",
            "media player": "vlc",
            "office suite": "libreoffice",
            "image editor": "gimp",
            "terminal": "gnome-terminal or konsole",
        }
        
        suggestion = mapping.get(category.lower())
        if suggestion:
            return f"For '{category}', I recommend: {suggestion}. Would you like me to install one of these for you?"
        else:
            return f"I'm not sure about '{category}'. You might want to search online or ask me to search the package database."
