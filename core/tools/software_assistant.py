from typing import Any
from .base import BaseTool
from .web_tools import WebSearchTool

class SoftwareAssistantTool(BaseTool):
    """Unified assistant to find and recommend Linux software."""

    @property
    def name(self) -> str:
        return "software_assistant"

    @property
    def description(self) -> str:
        return (
            "Find software recommendations or alternatives for Linux. "
            "Use this to find applications by category or by comparing to Windows/macOS programs."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The software search query or application name to find alternatives for."
                }
            },
            "required": ["query"]
        }

    async def execute(self, query: str) -> str:
        search_tool = WebSearchTool()
        # Optimize query for software comparisons
        search_query = f"best Linux alternatives for {query} comparison 2026"
        results = await search_tool.execute(query=search_query, num_results=3)
        
        return (
            f"Here are the top recommendations for '{query}' found online:\n\n"
            f"{results}\n\n"
            "I have synthesized these results: please review them and let me know if "
            "you'd like help installing one of these options."
        )
