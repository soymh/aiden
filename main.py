#!/usr/bin/env python3
"""
LM Studio Chatbot with Dynamic Tool Discovery and Dynamic Tool Specifications

This chatbot automatically discovers tools defined as methods in tool classes (which inherit from ToolBase),
builds their JSON schema from type hints and docstrings, and dynamically executes them when requested by the API.
It also streams responses from the LM Studio endpoint.
"""

import itertools
import importlib.util
import inspect
import json
import os
import shutil
import sys
import threading
import time

from openai import OpenAI
from tools.base_tool import ToolBase

# ANSI color codes for beautiful output
COLOR_BLUE = "\033[1;34m"
COLOR_GREEN = "\033[1;32m"
COLOR_RED = "\033[1;31m"
COLOR_MAGENTA = "\033[1;35m"
COLOR_YELLOW = "\033[1;33m"
COLOR_CYAN = "\033[1;36m"
COLOR_RESET = "\033[0m"

# Initialize LM Studio client
client = OpenAI(base_url="http://127.0.0.1:1234/v1", api_key="lm-studio")
MODEL = "qwen2.5-7b-instruct-1m"


def load_tools() -> dict:
    """
    Dynamically loads tool classes from the 'tools' directory.
    It instantiates each tool class (inheriting from ToolBase) and collects the tool specifications
    by calling the instance's get_tool_spec() method.
    Returns a dictionary mapping tool name to a dict with name, description, parameters, and function.
    """
    tools = {}
    tools_dir = os.path.join(os.path.dirname(__file__), "tools")
    if not os.path.isdir(tools_dir):
        print(f"{COLOR_RED}Tools directory not found: {tools_dir}{COLOR_RESET}")
        return tools

    for filename in os.listdir(tools_dir):
        # Skip __init__.py and base_tool.py (which defines the parent class)
        if filename.endswith(".py") and filename not in ["__init__.py", "base_tool.py"]:
            module_name = filename[:-3]
            file_path = os.path.join(tools_dir, filename)
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Look for classes that inherit from ToolBase (but not ToolBase itself)
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if inspect.isclass(attr) and issubclass(attr, ToolBase) and attr is not ToolBase:
                    instance = attr()
                    for tool_spec in instance.get_tool_spec():
                        # Save the tool specification in a dictionary.
                        # Include the tool's name for later lookup.
                        tools[tool_spec["name"]] = {
                            "name": tool_spec["name"],
                            "description": tool_spec["description"],
                            "parameters": tool_spec["parameters"],
                            "function": getattr(instance, tool_spec["name"]),
                        }
    return tools


# Load all tools dynamically
TOOLS = load_tools()

def get_tools_spec_list(tools_dict: dict) -> list:
    """
    Returns a list of tool specifications suitable for sending to the LM Studio API.
    Each specification is an object with keys:
      - "type": "function"
      - "function": an object with keys "name", "description", and "parameters"
    """
    tools_spec = []
    for tool in tools_dict.values():
        spec = {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"],
            }
        }
        tools_spec.append(spec)
    return tools_spec

def print_fancy_section(header: str, content: str, header_color: str):
    """Prints a section with a colored header and border."""
    terminal_width = shutil.get_terminal_size().columns
    border = "=" * terminal_width
    print(f"\n{border}")
    print(f"{header_color}{header}{COLOR_RESET}".center(terminal_width))
    print("-" * terminal_width)
    print(content)
    print(f"{border}\n")


class Spinner:
    """Simple terminal spinner to indicate processing."""
    def __init__(self, message="Processing..."):
        self.spinner = itertools.cycle(["-", "/", "|", "\\"])
        self.busy = False
        self.delay = 0.1
        self.message = message
        self.thread = None

    def write(self, text):
        sys.stdout.write(text)
        sys.stdout.flush()

    def _spin(self):
        while self.busy:
            self.write(f"\r{self.message} {next(self.spinner)}")
            time.sleep(self.delay)
        self.write("\r\033[K")  # Clear the line

    def __enter__(self):
        self.busy = True
        self.thread = threading.Thread(target=self._spin)
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.busy = False
        time.sleep(self.delay)
        if self.thread:
            self.thread.join()
        self.write("\r")


def chat_loop():
    """
    Main chat loop:
     - Sends user messages (and tool call instructions) to LM Studio.
     - Dynamically executes any tool call by matching the tool name.
     - Streams the assistant's response.
    """
    messages = [
        {
            "role": "system",
            "content": (
                "You are an assistant that can execute various tools. "
                "The available tools have been dynamically loaded from the system. "
                "When you need to call a tool, include its name and parameters."
            ),
        }
    ]

    print(
        f"{COLOR_GREEN}Assistant:{COLOR_RESET} Hi! I can use dynamically discovered tools to help you. "
        "Type 'quit' to exit."
    )

    while True:
        user_input = input(f"\n{COLOR_CYAN}You:{COLOR_RESET} ").strip()
        if user_input.lower() == "quit":
            break

        messages.append({"role": "user", "content": user_input})
        try:
            with Spinner("Thinking..."):
                # Build JSON serializable tools spec (with proper nesting)
                tools_spec = get_tools_spec_list(TOOLS)
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    tools=tools_spec,
                )

            # If the response includes tool calls, process each one dynamically.
            if response.choices[0].message.tool_calls:
                tool_calls = response.choices[0].message.tool_calls
                messages.append({
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": tool_call.type,
                            "function": tool_call.function,
                        }
                        for tool_call in tool_calls
                    ],
                })

                for tool_call in tool_calls:
                    tool_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    if tool_name in TOOLS:
                        tool_function = TOOLS[tool_name]["function"]
                        result = tool_function(**args)
                    else:
                        result = {"status": "error", "message": "Unknown tool call."}

                    # Print the result in a generic fancy section.
                    print_fancy_section(f"Tool Execution Result: {tool_name}", json.dumps(result, indent=2), COLOR_CYAN)
                    messages.append({
                        "role": "tool",
                        "content": json.dumps(result),
                        "tool_call_id": tool_call.id,
                    })

                # Stream the post-tool-call assistant response
                print(f"\n{COLOR_GREEN}Assistant:{COLOR_RESET} ", end="", flush=True)
                stream_response = client.chat.completions.create(
                    model=MODEL, messages=messages, stream=True
                )
                collected_content = ""
                for chunk in stream_response:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        print(content, end="", flush=True)
                        collected_content += content
                print()  # New line after streaming completes
                messages.append({"role": "assistant", "content": collected_content})
            else:
                # Stream a regular response if no tool call was made.
                print(f"\n{COLOR_GREEN}Assistant:{COLOR_RESET} ", end="", flush=True)
                stream_response = client.chat.completions.create(
                    model=MODEL, messages=messages, stream=True
                )
                collected_content = ""
                for chunk in stream_response:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        print(content, end="", flush=True)
                        collected_content += content
                print()
                messages.append({"role": "assistant", "content": collected_content})
        except Exception as e:
            error_message = (
                f"\n{COLOR_RED}Error communicating with the LM Studio server!{COLOR_RESET}\n\n"
                "Ensure that:\n"
                "1. LM Studio server is running at 127.0.0.1:1234\n"
                f"2. Model '{MODEL}' is downloaded and loaded\n"
                f"Error details: {str(e)}\n"
                "See https://lmstudio.ai/docs/basics/server for more information."
            )
            print(error_message)
            exit(1)


if __name__ == "__main__":
    chat_loop()
