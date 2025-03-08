"""
LM Studio Tool Use Demo: Wikipedia Querying and Shell Command Execution Chatbot
Demonstrates how an LM Studio model can query Wikipedia or run shell commands after user confirmation.
"""

# Standard library imports
import itertools
import json
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request

# Third-party imports
from openai import OpenAI

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


def fetch_wikipedia_content(search_query: str) -> dict:
    """Fetches Wikipedia content for a given search_query"""
    try:
        # Search for most relevant article
        search_url = "https://en.wikipedia.org/w/api.php"
        search_params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": search_query,
            "srlimit": 1,
        }
        url = f"{search_url}?{urllib.parse.urlencode(search_params)}"
        with urllib.request.urlopen(url) as response:
            search_data = json.loads(response.read().decode())

        if not search_data["query"]["search"]:
            return {
                "status": "error",
                "message": f"No Wikipedia article found for '{search_query}'",
            }

        # Get the normalized title from search results
        normalized_title = search_data["query"]["search"][0]["title"]

        # Now fetch the actual content with the normalized title
        content_params = {
            "action": "query",
            "format": "json",
            "titles": normalized_title,
            "prop": "extracts",
            "exintro": "true",
            "explaintext": "true",
            "redirects": 1,
        }
        url = f"{search_url}?{urllib.parse.urlencode(content_params)}"
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())

        pages = data["query"]["pages"]
        page_id = list(pages.keys())[0]

        if page_id == "-1":
            return {
                "status": "error",
                "message": f"No Wikipedia article found for '{search_query}'",
            }

        content = pages[page_id]["extract"].strip()
        return {
            "status": "success",
            "content": content,
            "title": pages[page_id]["title"],
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


def run_shell_command(command: str) -> dict:
    """
    Executes a shell command on the local machine after obtaining user verification.
    Asks the user to verify before executing the command.
    """
    print(f"\n{COLOR_CYAN}Shell Command Execution Request:{COLOR_RESET} {command}")
    user_confirm = input("Do you want to execute this shell command? (yes/no): ").strip().lower()
    if user_confirm not in ["yes", "y"]:
        return {"status": "aborted", "message": "Command execution aborted by user."}
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return {
            "status": "success",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# Define tool for Wikipedia queries
WIKI_TOOL = {
    "type": "function",
    "function": {
        "name": "fetch_wikipedia_content",
        "description": (
            "Search Wikipedia and fetch the introduction of the most relevant article. "
            "Always use this if the user is asking for something that is likely on Wikipedia. "
            "If the user has a typo in their search query, correct it before searching."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "search_query": {
                    "type": "string",
                    "description": "Search query for finding the Wikipedia article",
                },
            },
            "required": ["search_query"],
        },
    },
}

# Define tool for executing shell commands
SHELL_TOOL = {
    "type": "function",
    "function": {
        "name": "run_shell_command",
        "description": (
            "Execute a shell command on the local machine after obtaining user verification. "
            "Ask the user to confirm the execution before running the command."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to be executed on the host machine",
                },
            },
            "required": ["command"],
        },
    },
}


# Class for displaying the state of model processing
class Spinner:
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
        self.write("\r")  # Move cursor to beginning of line


def print_fancy_section(header: str, content: str, header_color: str):
    """
    Prints a section with a colored header and a border.
    """
    terminal_width = shutil.get_terminal_size().columns
    border = "=" * terminal_width
    print(f"\n{border}")
    print(f"{header_color}{header}{COLOR_RESET}".center(terminal_width))
    print("-" * terminal_width)
    print(content)
    print(f"{border}\n")


def chat_loop():
    """
    Main chat loop that processes user input and handles tool calls.
    """
    messages = [
        {
            "role": "system",
            "content": (
                "You are an assistant that can retrieve Wikipedia articles and execute shell commands. "
                "When asked about a topic, you can retrieve Wikipedia articles and cite information from them, "
                "or if necessary, execute shell commands after obtaining user confirmation."
            ),
        }
    ]

    print(
        f"{COLOR_GREEN}Assistant:{COLOR_RESET} Hi! I can access Wikipedia to help answer your questions about history, science, "
        "people, places, or concepts - and I can also execute shell commands if needed (with your confirmation)."
    )
    print("(Type 'quit' to exit)")

    while True:
        user_input = input(f"\n{COLOR_CYAN}You:{COLOR_RESET} ").strip()
        if user_input.lower() == "quit":
            break

        messages.append({"role": "user", "content": user_input})
        try:
            with Spinner("Thinking..."):
                # Pass both tools to the model
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    tools=[WIKI_TOOL, SHELL_TOOL],
                )

            if response.choices[0].message.tool_calls:
                # Log tool call details in the conversation
                tool_calls = response.choices[0].message.tool_calls
                messages.append(
                    {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": tool_call.id,
                                "type": tool_call.type,
                                "function": tool_call.function,
                            }
                            for tool_call in tool_calls
                        ],
                    }
                )

                # Process each tool call and add results
                for tool_call in tool_calls:
                    args = json.loads(tool_call.function.arguments)
                    if tool_call.function.name == "fetch_wikipedia_content":
                        result = fetch_wikipedia_content(args["search_query"])
                        if result["status"] == "success":
                            header = f"Wikipedia Article: {result['title']}"
                            print_fancy_section(header, result["content"], COLOR_BLUE)
                        else:
                            header = "Wikipedia Query Error"
                            print_fancy_section(header, result["message"], COLOR_RED)
                    elif tool_call.function.name == "run_shell_command":
                        result = run_shell_command(args["command"])
                        if result["status"] == "success":
                            output = f"{COLOR_GREEN}Return Code:{COLOR_RESET} {result['returncode']}\n"
                            if result["stdout"]:
                                output += f"{COLOR_GREEN}Standard Output:{COLOR_RESET}\n{result['stdout']}\n"
                            if result["stderr"]:
                                output += f"{COLOR_RED}Standard Error:{COLOR_RESET}\n{result['stderr']}\n"
                            header = "Shell Command Execution Result"
                            print_fancy_section(header, output, COLOR_MAGENTA)
                        elif result["status"] == "aborted":
                            header = "Shell Command Aborted"
                            print_fancy_section(header, result["message"], COLOR_YELLOW)
                        else:
                            header = "Shell Command Error"
                            print_fancy_section(header, result["message"], COLOR_RED)
                    else:
                        result = {"status": "error", "message": "Unknown tool call."}
                        header = "Unknown Tool Call"
                        print_fancy_section(header, result["message"], COLOR_RED)

                    messages.append(
                        {
                            "role": "tool",
                            "content": json.dumps(result),
                            "tool_call_id": tool_call.id,
                        }
                    )

                # Stream the post-tool-call response
                print(f"\n{COLOR_GREEN}Assistant:{COLOR_RESET}", end=" ", flush=True)
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
                messages.append(
                    {
                        "role": "assistant",
                        "content": collected_content,
                    }
                )
            else:
                # Handle regular response
                print(f"\n{COLOR_GREEN}Assistant:{COLOR_RESET} {response.choices[0].message.content}")
                messages.append(
                    {
                        "role": "assistant",
                        "content": response.choices[0].message.content,
                    }
                )

        except Exception as e:
            error_message = (
                f"\n{COLOR_RED}Error chatting with the LM Studio server!{COLOR_RESET}\n\n"
                "Please ensure:\n"
                "1. LM Studio server is running at 127.0.0.1:1234 (hostname:port)\n"
                f"2. Model '{MODEL}' is downloaded\n"
                f"3. Model '{MODEL}' is loaded, or that just-in-time model loading is enabled\n\n"
                f"Error details: {str(e)}\n"
                "See https://lmstudio.ai/docs/basics/server for more information"
            )
            print(error_message)
            exit(1)


if __name__ == "__main__":
    chat_loop()

