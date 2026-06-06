"""
Web interaction tools for the AI agent.

Allows the AI to fetch web content, search the web, and
interact with HTTP APIs.
"""

from typing import Any, Dict, Optional
from urllib.parse import quote

import httpx

from .base import BaseTool


class WebFetchTool(BaseTool):
    """Fetch content from a URL."""

    @property
    def name(self) -> str:
        return "web_fetch"

    @property
    def description(self) -> str:
        return "Fetch and retrieve the content of a URL. Use this to read web pages, API responses, or documentation."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch content from",
                },
                "format": {
                    "type": "string",
                    "enum": ["text", "markdown", "html"],
                    "description": "Preferred response format",
                    "default": "text",
                },
            },
            "required": ["url"],
        }

    async def execute(self, url: str, format: str = "text") -> str:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; AIAssistant/1.0)",
                })
                response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            if "text/" in content_type or "application/json" in content_type:
                text = response.text
                if len(text) > 50000:
                    text = text[:50000] + "\n... [truncated at 50000 characters]"
                return f"URL: {url}\nStatus: {response.status_code}\nContent-Type: {content_type}\n\n{text}"
            else:
                return f"URL: {url}\nStatus: {response.status_code}\nContent-Type: {content_type}\n(Content is binary, not displayed)"

        except httpx.TimeoutException:
            return f"Error: Request timed out: {url}"
        except httpx.HTTPStatusError as e:
            return f"Error: HTTP {e.response.status_code} fetching {url}"
        except Exception as e:
            return f"Error fetching {url}: {e}"


class WebSearchTool(BaseTool):
    """Search the web using a search engine."""

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Search the web for information. Use this to find recent news, documentation, or any online information."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query string",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of search results to return (default: 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        }

    async def execute(self, query: str, num_results: int = 5) -> str:
        search_url = f"https://html.duckduckgo.com/html/?q={quote(query)}"

        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(search_url, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; AIAssistant/1.0)",
                })
                response.raise_for_status()

            # Simple extraction of search results from DuckDuckGo HTML
            html = response.text
            results = []
            import re

            # Find result blocks
            blocks = re.findall(
                r'<a rel="nofollow" class="result__a" href="(.*?)".*?>(.*?)</a>.*?'
                r'<a class="result__snippet".*?>(.*?)</a>',
                html, re.DOTALL
            )

            for i, (url, title, snippet) in enumerate(blocks[:num_results], 1):
                title_clean = re.sub(r'<.*?>', '', title).strip()
                snippet_clean = re.sub(r'<.*?>', '', snippet).strip()
                results.append(f"{i}. {title_clean}\n   {url}\n   {snippet_clean}")

            if not results:
                return f"No results found for '{query}'"

            return f"Search results for '{query}':\n\n" + "\n\n".join(results)

        except Exception as e:
            return f"Error searching for '{query}': {e}"


class DownloadFileTool(BaseTool):
    """Download a file from a URL to the local filesystem."""

    @property
    def name(self) -> str:
        return "download_file"

    @property
    def description(self) -> str:
        return "Download a file from a URL and save it to the specified local path."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL of the file to download",
                },
                "destination": {
                    "type": "string",
                    "description": "Absolute path where to save the file",
                },
            },
            "required": ["url", "destination"],
        }

    async def execute(self, url: str, destination: str) -> str:
        from pathlib import Path

        dest = Path(destination).expanduser().resolve()
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return f"Error creating directory: {e}"

        try:
            async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()

            with open(dest, "wb") as f:
                f.write(response.content)

            size = len(response.content)
            return f"Downloaded {size} bytes from {url} to {dest}"

        except Exception as e:
            return f"Error downloading {url}: {e}"
