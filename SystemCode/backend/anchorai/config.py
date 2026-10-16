from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_repo_root() -> Path:
    # Commands run from SystemCode/backend while .env and data/ live at the repo root.
    # The Docker image has no repo, so fall back to the working directory there.
    for parent in Path(__file__).resolve().parents:
        if (parent / "AGENTS.md").is_file() and (parent / "SystemCode").is_dir():
            return parent
    return Path.cwd()


REPO_ROOT = _find_repo_root()
_SQLITE_PREFIX = "sqlite:///"
_DEV_JWT_SECRET = "dev-only-insecure-secret-set-ANCHORAI_JWT_SECRET"
# Published defaults (code and .env.example); anyone could forge tokens with them.
INSECURE_JWT_SECRETS = {_DEV_JWT_SECRET, "change-me-to-a-random-32-byte-hex-string"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    # LLM: any OpenAI-compatible endpoint (Ollama, OpenAI, vLLM, LM Studio, ...)
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "ollama"
    llm_model: str = "qwen2.5:7b-instruct"
    llm_temperature: float = 0.1
    llm_tool_calling: bool = False
    llm_timeout_seconds: float = 30.0
    assistant_embedding_model: str = "all-MiniLM-L6-v2"

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "anchorai-dev"

    anchorai_data_dir: Path = Path("SystemCode/data")
    anchorai_seed: int = 42
    # Empty means <anchorai_data_dir>/app.db.
    anchorai_db_url: str = ""

    anchorai_jwt_secret: str = _DEV_JWT_SECRET
    anchorai_jwt_ttl_minutes: int = 720
    anchorai_demo_password: str = "anchorai"

    @model_validator(mode="after")
    def _anchor_relative_paths(self) -> "Settings":
        if not self.anchorai_data_dir.is_absolute():
            self.anchorai_data_dir = REPO_ROOT / self.anchorai_data_dir
        if not self.anchorai_db_url:
            self.anchorai_db_url = f"{_SQLITE_PREFIX}{self.anchorai_data_dir / 'app.db'}"
        elif self.anchorai_db_url.startswith(_SQLITE_PREFIX):
            db_path = Path(self.anchorai_db_url.removeprefix(_SQLITE_PREFIX))
            if str(db_path) != ":memory:" and not db_path.is_absolute():
                self.anchorai_db_url = f"{_SQLITE_PREFIX}{REPO_ROOT / db_path}"
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
