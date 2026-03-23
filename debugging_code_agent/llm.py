from __future__ import annotations

from typing import Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

Provider = Literal["ollama", "server", "mlx"]

_DEFAULT_MLX_BASE_URL = "http://127.0.0.1:8080/v1"
_LOCAL_API_KEY_FALLBACK = "local-server"
_DEFAULT_TOP_P = 0.9
_DEFAULT_TOP_K = 40
_DEFAULT_MIN_P = 0.0
_DEFAULT_REPEAT_PENALTY = 1.05
_DEFAULT_SEED = 42


def create_chat_model(
    provider: Provider,
    model: str,
    temperature: float,
    base_url: str | None = None,
    api_key: str | None = None,
    top_p: float = _DEFAULT_TOP_P,
    top_k: int = _DEFAULT_TOP_K,
    min_p: float = _DEFAULT_MIN_P,
    repeat_penalty: float = _DEFAULT_REPEAT_PENALTY,
    seed: int | None = _DEFAULT_SEED,
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

    extra_body: dict[str, object] = {
        "top_k": top_k,
        "repeat_penalty": repeat_penalty,
    }
    if min_p > 0:
        extra_body["min_p"] = min_p

    return ChatOpenAI(
        model=model,
        temperature=temperature,
        top_p=top_p,
        seed=seed,
        extra_body=extra_body,
        base_url=resolved_base_url or None,
        api_key=(api_key or "").strip() or _LOCAL_API_KEY_FALLBACK,
    )
