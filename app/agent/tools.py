import os
import sys
import subprocess
import httpx
import json
import webbrowser
import fnmatch
import platform
import shutil
from typing import Dict, Any, Callable, List, Optional


class ToolRegistry:
    """Registry of tools available to the Sazon Autonomous Agent."""

    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._register_default_tools()

    def register(self, name: str, func: Callable, description: str):
        self._tools[name] = {
            "func": func,
            "description": description
        }

    def get_tool(self, name: str) -> Optional[Callable]:
        tool = self._tools.get(name)
        return tool["func"] if tool else None

    def list_tools(self) -> List[Dict[str, str]]:
        return [
            {"name": name, "description": data["description"]}
            for name, data in self._tools.items()
        ]

    def execute(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        tool_data = self._tools.get(tool_name)
        if not tool_data:
            return f"Error: Tool '{tool_name}' not found. Available tools: {list(self._tools.keys())}"
        try:
            result = tool_data["func"](**tool_input)
            if isinstance(result, (dict, list)):
                return json.dumps(result, indent=2)
            return str(result)
        except Exception as e:
            return f"Error executing tool '{tool_name}': {str(e)}"

    def _register_default_tools(self):
        # File Read Tool
        def file_read(filepath: str) -> str:
            if not os.path.exists(filepath):
                return f"Error: File '{filepath}' does not exist."
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

        self.register("file_read", file_read, "Read contents of a local file. Args: filepath (str)")

        # File Write Tool
        def file_write(filepath: str, content: str) -> str:
            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote {len(content)} characters to '{filepath}'."

        self.register("file_write", file_write, "Write text content to a local file. Args: filepath (str), content (str)")

        # File List Tool
        def file_list(directory: str = ".") -> str:
            if not os.path.exists(directory):
                return f"Error: Directory '{directory}' does not exist."
            items = os.listdir(directory)
            return json.dumps({"directory": os.path.abspath(directory), "items": items})

        self.register("file_list", file_list, "List files and subdirectories. Args: directory (str, default '.')")

        # File Search Tool
        def file_search(pattern: str, directory: str = ".") -> str:
            matches = []
            for root, dirnames, filenames in os.walk(directory):
                for filename in fnmatch.filter(filenames, pattern):
                    matches.append(os.path.join(root, filename))
                if len(matches) >= 50:
                    break
            return json.dumps({"pattern": pattern, "found_count": len(matches), "files": matches[:50]})

        self.register("file_search", file_search, "Search for files matching a pattern (e.g. '*.py', 'notes*'). Args: pattern (str), directory (str)")

        # Create Folder Tool
        def create_folder(folder_path: str) -> str:
            os.makedirs(folder_path, exist_ok=True)
            return f"Folder '{folder_path}' created or verified successfully."

        self.register("create_folder", create_folder, "Create a folder/directory. Args: folder_path (str)")

        # Open App or URL Tool
        def open_app_or_url(target: str) -> str:
            try:
                if target.startswith("http://") or target.startswith("https://"):
                    webbrowser.open(target)
                    return f"Opened URL '{target}' in default browser."
                else:
                    if sys.platform == "win32":
                        os.startfile(target)
                    else:
                        subprocess.Popen([target])
                    return f"Opened application or path '{target}'."
            except Exception as e:
                return f"Failed to open '{target}': {e}"

        self.register("open_app_or_url", open_app_or_url, "Open a web URL or launch a local application/file. Args: target (str)")

        # System Diagnostics Tool
        def system_status() -> str:
            disk = shutil.disk_usage(os.getcwd())
            info = {
                "platform": platform.platform(),
                "system": platform.system(),
                "processor": platform.processor(),
                "python_version": sys.version.split()[0],
                "cwd": os.getcwd(),
                "disk_free_gb": round(disk.free / (1024**3), 2),
                "disk_total_gb": round(disk.total / (1024**3), 2)
            }
            return json.dumps(info, indent=2)

        self.register("system_status", system_status, "Get laptop hardware & OS diagnostic status.")

        # HTTP GET Tool
        def http_get(url: str) -> str:
            try:
                with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                    resp = client.get(url)
                    return f"Status: {resp.status_code}\nContent Snippet:\n{resp.text[:2000]}"
            except Exception as e:
                return f"HTTP request failed: {e}"

        self.register("http_get", http_get, "Fetch web page content via HTTP GET. Args: url (str)")

        # Shell Command Execution Tool
        def shell_run(command: str) -> str:
            allow_shell = os.getenv("ALLOW_SHELL_EXECUTION", "true").lower() == "true"
            if not allow_shell:
                return "Error: Shell execution is disabled by security policy."
            try:
                res = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=os.getcwd()
                )
                output = res.stdout if res.returncode == 0 else f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
                return output[:3000] if output else "Command executed with no output."
            except Exception as e:
                return f"Shell execution error: {e}"

        self.register("shell_run", shell_run, "Execute shell command on laptop. Args: command (str)")

        # Legacy alias for system_info
        self.register("system_info", system_status, "Get system environment information.")

# Global instance of tool registry
default_registry = ToolRegistry()
