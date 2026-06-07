"""
Command execution tools for the AI agent.

Allows the AI to execute shell commands, run scripts, and interact
with the terminal environment.
"""

import asyncio
import shlex
from typing import Any

from .base import BaseTool


class ExecuteCommandTool(BaseTool):
    """Execute a shell command and capture its output."""

    @property
    def name(self) -> str:
        return "execute_command"

    @property
    def description(self) -> str:
        return (
            "Execute a shell command and return its stdout and stderr. "
            "Use this to run scripts, compile code, or interact with the system. "
            "IMPORTANT: If launching a GUI application (e.g., 'firefox'), "
            "you MUST use: 'command > /dev/null 2>&1 & disown' "
            "to prevent blocking the assistant and detach the app properly."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute",
                },
                "workdir": {
                    "type": "string",
                    "description": "Working directory (default: current directory)",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Maximum execution time in seconds (default: 60)",
                    "default": 60,
                },
            },
            "required": ["command"],
        }

    @staticmethod
    async def _get_sudo_password(command: str) -> str | None:
        """Show a KDE password dialog and return the password, or None if cancelled."""
        for dialog_cmd in ("kdialog", "zenity"):
            try:
                args = []
                if dialog_cmd == "kdialog":
                    args = ["kdialog", "--password", f"Sudo password needed for:\n{command}"]
                else:
                    args = [
                        "zenity",
                        "--entry",
                        "--hide-text",
                        "--title",
                        "Sudo Password",
                        "--text",
                        f"Sudo password needed for:\n{command}",
                    ]
                process = await asyncio.create_subprocess_exec(
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=120)
                if process.returncode == 0 and stdout:
                    pw = stdout.decode().strip()
                    if pw:
                        return pw
            except TimeoutError, FileNotFoundError:
                continue
        return None

    async def execute(self, command: str, workdir: str = "", timeout: int = 60) -> str:
        cwd = workdir if workdir else None
        is_sudo = command.strip().startswith("sudo ") or command.strip() == "sudo"
        sudo_password = None

        if is_sudo:
            sudo_password = await self._get_sudo_password(command)
            if sudo_password is None:
                return (
                    "[The sudo password prompt was cancelled or no password dialog tool "
                    "(kdialog/zenity) is installed.]\n\n"
                    "The user did not provide the sudo password."
                )
            actual_cmd = command.strip()
            for prefix in ("sudo ", "sudo"):
                if actual_cmd.startswith(prefix):
                    actual_cmd = actual_cmd[len(prefix) :].strip()
                    break
            command = f"sudo -S {actual_cmd}"

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdin=asyncio.subprocess.PIPE if sudo_password else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )

            try:
                stdin_data = (sudo_password + "\n").encode() if sudo_password else None
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=stdin_data), timeout=timeout
                )
            except TimeoutError:
                process.kill()
                await process.wait()
                return f"Error: Command timed out after {timeout} seconds:\n```\n{command}\n```"

            output = ""
            if stdout:
                output += stdout.decode("utf-8", errors="replace")
            if stderr:
                if output:
                    output += "\n[stderr]\n"
                output += stderr.decode("utf-8", errors="replace")

            exit_code = process.returncode
            result = f"Exit code: {exit_code}\n"
            if output:
                result += f"Output:\n```\n{output}\n```"
            else:
                result += "(no output)"

            return result

        except FileNotFoundError:
            return f"Error: Command not found: {shlex.split(command)[0]}"
        except Exception as e:
            return f"Error executing command: {e}"


class ExecutePythonTool(BaseTool):
    """Execute Python code in an isolated environment."""

    @property
    def name(self) -> str:
        return "execute_python"

    @property
    def description(self) -> str:
        return (
            "Execute Python code and return its output. "
            "Use this for quick calculations, data analysis, or testing snippets."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute",
                },
            },
            "required": ["code"],
        }

    async def execute(self, code: str) -> str:
        try:
            process = await asyncio.create_subprocess_exec(
                "python3",
                "-c",
                code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
            except TimeoutError:
                process.kill()
                await process.wait()
                return "Error: Python execution timed out after 30 seconds"

            output = ""
            if stdout:
                output += stdout.decode("utf-8", errors="replace")
            if stderr:
                if output:
                    output += "\n[stderr]\n"
                output += stderr.decode("utf-8", errors="replace")

            if not output:
                output = "(no output)"

            return f"Exit code: {process.returncode}\nOutput:\n```\n{output}\n```"

        except FileNotFoundError:
            return "Error: python3 not found in PATH"
        except Exception as e:
            return f"Error executing Python: {e}"
