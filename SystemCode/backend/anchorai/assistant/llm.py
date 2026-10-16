# Ollama, OpenAI and most self-hosted servers speak the OpenAI API, so one client covers all.
from openai import OpenAI

from anchorai.config import get_settings


def get_client() -> OpenAI:
    s = get_settings()
    # One retry and a timeout, so a slow or dead endpoint degrades the assistant instead of hanging it.
    return OpenAI(
        base_url=s.llm_base_url,
        api_key=s.llm_api_key,
        timeout=s.llm_timeout_seconds,
        max_retries=1,
    )


def chat(messages: list[dict], **kwargs) -> str:
    s = get_settings()
    resp = get_client().chat.completions.create(
        model=s.llm_model,
        messages=messages,
        temperature=kwargs.pop("temperature", s.llm_temperature),
        **kwargs,
    )
    return resp.choices[0].message.content or ""
