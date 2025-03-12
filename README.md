# Aiden : An LM Studio Chatbot,Capable of Dynamic Tool Execution

## Overview

This is an AI chatbot that leverages the [LM Studio](https://lmstudio.ai/) platform. The main purpose of this assistant is to facilitate interactions by dynamically discovering tools defined as methods in classes that inherit from `ToolBase`. These tools are built with their JSON schema generated automatically using type hints and docstrings.

The assistant operates via a command-line interface, where it can execute commands based on user input or predefined scenarios. It communicates with the LM Studio API to process messages and manage interactions dynamically.

## Features

### Dynamic Tool Discovery

- **Automatically Loads Tools**: The assistant can load tools from specified directories without manual intervention. It inspects Python modules within these directories for classes that inherit from `ToolBase`.

- **Builds Specifications Dynamically**: For each discovered tool, the assistant constructs a specification dictionary including:
  - Name
  - Description
  - Parameters
  - Function

### Dynamic Execution of Tools

- **Executes on Demand**: The assistant can execute any discovered tool dynamically by matching its name to an available tool function. This is done based on user input or AI-generated commands.

- **Streams Responses**: After a command that involves tools, the assistant streams back responses from LM Studio in real-time for more natural interaction.

### User Interaction

- **Command-Line Interface**: Users interact with the assistant via command-line inputs. The system can process various types of input and provide appropriate outputs or actions based on available tools.

- **Graceful Exit**: Users can type 'quit' to exit the interactive session gracefully without any issues.

## Technical Setup

### Dependencies

The script relies on several Python packages including `openai`, for interacting with LM Studio, and other utilities like `itertools` for looping operations and `json` for handling JSON data. Ensure these dependencies are installed in your environment using pip:

```bash
pip install openai
```

### Running the Assistant

To run this assistant, make sure you have the necessary setup (such as having LM Studio server running on `127.0.0.1:1234` with a specific model like 'qwen2.5-7b-instruct-1m' loaded). Then execute:

```bash
python main.py
```

This command starts the chat loop, where you can interact with the assistant through the command line.

## Contributing

If you're interested in contributing to this project or have suggestions for improvement, feel free to open an issue or submit a pull request. Your contributions are highly valued!

---

### *This README.md content has been generated using this tool, by "qwen2.5-7b-instruct-1m".*