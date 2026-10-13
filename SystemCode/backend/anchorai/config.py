from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM: any OpenAI-compatible endpoint (Ollama, OpenAI, vLLM, LM Studio, ...)
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "ollama"
    llm_model: str = "qwen2.5:7b-instruct"
    llm_temperature: float = 0.1
    llm_tool_calling: bool = False

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "anchorai-dev"

    anchorai_data_dir: Path = Path("SystemCode/data")
    anchorai_seed: int = 42


@lru_cache
def get_settings() -> Settings:
    return Settings()
