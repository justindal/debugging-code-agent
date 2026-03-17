# Self Debugging Code Agent

A Python code agent built with LangGraph that writes solutions for specific LeetCode problems, runs test cases, and self-corrects its solutions.

## Data

This project uses the Hugging Face dataset [`newfacade/LeetCodeDataset`](https://huggingface.co/datasets/newfacade/LeetCodeDataset) as the source for the problems including the starter code, entry points, and tests.

- Problems are loaded from the `test` split.

## Requirements

- Python 3.12+
- Ollama
- Some model (default: `llama3.1:8b`)

Example:

```bash
ollama pull llama3.1
```

## Installation

Using `uv`:

```bash
uv sync
```

Or using `pip`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

Run:

```bash
python main.py
```

Set attempts (default is 5):

```bash
debugging-code-agent --max-attempts 5
```
## Frameworks Used

- [LangGraph](https://langchain-ai.github.io/langgraph/) — agent graph and state management
- [Ollama](https://ollama.com) — local LLM inference
- [Textual](https://textual.textualize.io/) — terminal UI for problem selection
- [Hugging Face Datasets](https://huggingface.co/docs/datasets) — problem source