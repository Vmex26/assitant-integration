"""
Package management tools for the AI agent.

Allows searching, inspecting, installing, and removing system packages.
For AUR packages, provides PKGBUILD inspection before installation.
"""

from typing import Any, Dict, Optional

from .base import BaseTool


class SearchPackageTool(BaseTool):
    """Search for packages using the system package manager."""

    name = "search_package"
    description = "Search for available packages using pacman, apt, or dnf"
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search term for package name or description",
            },
            "manager": {
                "type": "string",
                "description": "Package manager to use (auto-detect if not specified)",
                "enum": ["auto", "pacman", "apt", "dnf"],
            },
        },
        "required": ["query"],
    }

    async def execute(self, query: str, manager: str = "auto", **kwargs) -> str:
        pm = self._detect_pm() if manager == "auto" else manager
        if pm == "pacman":
            return self._search_pacman(query)
        elif pm == "apt":
            return self._search_apt(query)
        elif pm == "dnf":
            return self._search_dnf(query)
        return f"Unknown package manager: {pm}"

    def _detect_pm(self) -> str:
        for pm in ["pacman", "apt", "dnf"]:
            if subprocess.run(["which", pm], capture_output=True).returncode == 0:
                return pm
        return "apt"

    def _search_pacman(self, query: str) -> str:
        try:
            result = subprocess.run(
                ["pacman", "-Ss", query],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                return f"Search failed: {result.stderr.strip()}"
            output = result.stdout.strip()
            if not output:
                return "No packages found."
            lines = output.split("\n")
            entries = []
            i = 0
            while i < len(lines):
                if lines[i].startswith(" ") or not lines[i].strip():
                    i += 1
                    continue
                name_line = lines[i]
                desc_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
                repo_pkg = name_line.split()[0] if name_line.split() else name_line
                version = name_line.split()[1] if len(name_line.split()) > 1 else "?"
                entries.append(f"- **{repo_pkg}** ({version})\n  {desc_line}")
                i += 2
            return f"Found {len(entries)} package(s):\n\n" + "\n".join(entries[:30])
        except subprocess.TimeoutExpired:
            return "Search timed out."
        except FileNotFoundError:
            return "pacman not found."

    def _search_apt(self, query: str) -> str:
        try:
            result = subprocess.run(
                ["apt-cache", "search", query],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                return f"Search failed: {result.stderr.strip()}"
            output = result.stdout.strip()
            if not output:
                return "No packages found."
            lines = output.split("\n")[:30]
            return "Found packages:\n\n" + "\n".join(f"- {line}" for line in lines)
        except subprocess.TimeoutExpired:
            return "Search timed out."
        except FileNotFoundError:
            return "apt-cache not found."

    def _search_dnf(self, query: str) -> str:
        try:
            result = subprocess.run(
                ["dnf", "search", query],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                return f"Search failed: {result.stderr.strip()}"
            output = result.stdout.strip()
            if not output:
                return "No packages found."
            lines = output.split("\n")[:30]
            return "Found packages:\n\n" + "\n".join(f"- {line}" for line in lines)
        except subprocess.TimeoutExpired:
            return "Search timed out."
        except FileNotFoundError:
            return "dnf not found."


class ShowPKGBUILDTool(BaseTool):
    """Fetch and display a PKGBUILD from the AUR."""

    name = "show_pkgbuild"
    description = "Fetch and display the PKGBUILD of an AUR package. Only works for AUR packages (not official repos). Always use this before installing AUR packages."
    parameters = {
        "type": "object",
        "properties": {
            "package": {
                "type": "string",
                "description": "Name of the AUR package",
            },
        },
        "required": ["package"],
    }

    async def execute(self, package: str, **kwargs) -> str:
        import httpx
        rpc_url = f"https://aur.archlinux.org/rpc/v5/info/{package}"
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(rpc_url)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            return f"Error fetching AUR info: {e}"

        if data.get("type") != "multiinfo" or not data.get("results"):
            return (
                f"Package '{package}' not found in AUR.\n\n"
                "(It may exist in the official repositories — try search_package instead.)"
            )

        info = data["results"][0]
        lines = [
            f"# PKGBUILD info for **{info.get('Name')}** ({info.get('Version')})",
            f"# Description: {info.get('Description', 'N/A')}",
            f"# Maintainer: {info.get('Maintainer', 'N/A')}",
            f"# License: {', '.join(info.get('License', [])) or 'N/A'}",
            f"# Votes: {info.get('NumVotes', 0)} | Popularity: {info.get('Popularity', 0):.2f}",
            f"# URL: {info.get('URL', 'N/A')}",
            f"# Dependencies: {', '.join(info.get('Depends', [])) or 'none'}",
            f"# Make deps: {', '.join(info.get('MakeDepends', [])) or 'none'}",
            "",
            "## PKGBUILD source",
        ]

        snaphot_url = f"https://aur.archlinux.org/cgit/aur.git/plain/PKGBUILD?h={package}"
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(snaphot_url)
                if resp.status_code == 200:
                    pkgbuild = resp.text
                    lines.append(f"```bash\n{pkgbuild}\n```")
                else:
                    lines.append(f"(could not fetch PKGBUILD source)")
        except Exception as e:
            lines.append(f"(error fetching PKGBUILD: {e})")

        if info.get("URL"):
            lines.append(f"\n## Homepage: {info['URL']}")

        return "\n".join(lines)
