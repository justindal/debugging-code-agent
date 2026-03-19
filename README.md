# Self Debugging Code Agent

A Python code agent built with LangGraph that writes solutions for specific LeetCode problems, runs test cases, and self-corrects its solutions.

## Data

This project uses the Hugging Face dataset [`newfacade/LeetCodeDataset`](https://huggingface.co/datasets/newfacade/LeetCodeDataset) as the source for the problems including the starter code, entry points, and tests.

- Problems are loaded from the `test` split.

## Requirements

- Python 3.12+
- One provider:
  - [Ollama](https://ollama.com)
  - OpenAI-compatible local server
  - MLX LM server (`mlx_lm.server`)
- A model supported by the chosen provider (default: `llama3.1`)

Example for Ollama:

```bash
ollama pull llama3.1
```

Example for MLX:

```bash
pip install mlx-lm
mlx_lm.server --model mlx-community/Llama-3.1-8B-Instruct
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
debugging-code-agent
```

Or with the module:

```bash
python -m debugging_code_agent
```

### Provider examples

Ollama (default):

```bash
debugging-code-agent --provider ollama --model llama3.1
```

OpenAI-compatible local server:

```bash
debugging-code-agent --provider server --base-url http://localhost:8000/v1 --model Qwen/Qwen2.5-Coder-7B-Instruct
```

MLX LM server (defaults to `http://127.0.0.1:8080/v1`):

```bash
debugging-code-agent --provider mlx --model mlx-community/Llama-3.1-8B-Instruct
```

### All options

```
--provider {ollama,server,mlx}   LLM provider (default: ollama)
--model MODEL                    Model name for the selected provider (default: llama3.1)
--temperature TEMPERATURE        Sampling temperature (default: 0.1)
--base-url BASE_URL              Base URL for server/mlx providers
--api-key API_KEY                Optional API key for server/mlx providers
--max-attempts MAX_ATTEMPTS      Maximum solve attempts per problem (default: 5)
```

## Frameworks Used

- [LangGraph](https://langchain-ai.github.io/langgraph/) — agent graph and state management
- [Ollama](https://ollama.com) — local LLM inference
- [LangChain Chat](https://python.langchain.com/docs/integrations/chat/openai/) — OpenAI-compatible server support
- [Textual](https://textual.textualize.io/) — terminal UI for problem selection
- [Hugging Face Datasets](https://huggingface.co/docs/datasets) — problem source
