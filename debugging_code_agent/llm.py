from __future__ import annotations

from typing import Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

Provider = Literal["ollama", "server", "mlx"]

_DEFAULT_MLX_BASE_URL = "http://127.0.0.1:8080/v1"
_LOCAL_API_KEY_FALLBACK = "local-server"


def create_chat_model(
    provider: Provider,
    model: str,
    temperature: float,
    base_url: str | None = None,
    api_key: str | None = None,
) -> BaseChatModel:
    if provider == "ollama":
        kwargs: dict[str, object] = {
            "model": model,
            "temperature": temperature,
        }
        if base_url:
            kwargs["base_url"] = base_url
        return ChatOllama(**kwargs)

    resolved_base_url = (base_url or "").strip()
    if provider == "mlx":
        resolved_base_url = resolved_base_url or _DEFAULT_MLX_BASE_URL
    if provider == "server" and not resolved_base_url:
        raise ValueError("--base-url is required when --provider server is used.")

    return ChatOpenAI(
        model=model,
        temperature=temperature,
        base_url=resolved_base_url or None,
        api_key=(api_key or "").strip() or _LOCAL_API_KEY_FALLBACK,
    )
