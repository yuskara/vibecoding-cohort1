import json
import os
import subprocess
from typing import Iterator

from llm import client
from backend.tools.search_onenote import SEARCH_ONENOTE_TOOL, _search_onenote

AGENT_WORKSPACE = "/tmp/agent_workspace"

TOOLS = [
    SEARCH_ONENOTE_TOOL,
    {
        "type": "function",
        "function": {
            "name": "terminal",
            "description": (
                "Runs a shell command in the terminal and returns the output. "
                f"Working directory: {AGENT_WORKSPACE}"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to execute"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "file_read",
            "description": "Reads the content of a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "file_write",
            "description": "Writes content to a file; creates the file if it doesn't exist, overwrites if it does.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "content": {"type": "string", "description": "Content to write to the file"},
                },
                "required": ["path", "content"],
            },
        },
    },
]


def _terminal(command: str) -> str:
    os.makedirs(AGENT_WORKSPACE, exist_ok=True)
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=AGENT_WORKSPACE,
        )
        output = (result.stdout + result.stderr).strip()
        return output or "(command produced no output)"
    except subprocess.TimeoutExpired:
        return "Error: Command did not complete within 30 seconds."
    except Exception as e:
        return f"Error: {e}"


def _file_read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error: {e}"


def _file_write(path: str, content: str) -> str:
    try:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully written: {path}"
    except Exception as e:
        return f"Error: {e}"


_TOOL_MAP = {
    "terminal":       lambda a: _terminal(a["command"]),
    "file_read":      lambda a: _file_read(a["path"]),
    "file_write":     lambda a: _file_write(a["path"], a["content"]),
    "search_onenote": lambda a: _search_onenote(a["query"], a.get("max_results", 5)),
}


class Agent:
    """
    Tool-calling agentic loop for wellness analysis. Each turn calls the model; if the model requests a tool,
    executes it and adds to history, continuing the loop. When the model provides plain text response, the loop ends.

    calistir() is a Generator that yields a dict for each event:
      {"type": "step_start", "step": int}
      {"type": "thinking",   "content": str}   — model text before tool call
      {"type": "tool_call",  "name": str, "args": dict}
      {"type": "tool_result","name": str, "result": str}
      {"type": "text",       "content": str}   — final response
      {"type": "done"}
    """

    def __init__(self, system_instructions: str, model: str = "llama2"):
        self.model = model
        self.history: list[dict] = [
            {"role": "system", "content": system_instructions}
        ]

    def calistir(self, user_prompt: str) -> Iterator[dict]:
        self.history.append({"role": "user", "content": user_prompt})
        step = 0

        while True:
            step += 1
            yield {"type": "step_start", "step": step}

            response = client.chat.completions.create(
                model=self.model,
                messages=self.history,
                tools=TOOLS,
                tool_choice="auto",
            )

            msg = response.choices[0].message

            # Assistant message to add to history
            history_msg: dict = {"role": "assistant"}
            if msg.content:
                history_msg["content"] = msg.content
            if msg.tool_calls:
                history_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ]
            self.history.append(history_msg)

            if msg.content:
                # If there are tool calls, this text reflects the "thinking" process
                kind = "thinking" if msg.tool_calls else "text"
                yield {"type": kind, "content": msg.content}

            if not msg.tool_calls:
                yield {"type": "done"}
                return

            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                yield {"type": "tool_call", "name": name, "args": args}

                fn = _TOOL_MAP.get(name)
                result = fn(args) if fn else f"Unknown tool: {name}"

                yield {"type": "tool_result", "name": name, "result": result}

                self.history.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
