"""
Central configuration: model names, budget limits, mock mode.
Values are read from environment variables (see .env.example).
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    model_primary: str = os.getenv("MODEL_PRIMARY", "")
    model_fallback: str = os.getenv("MODEL_FALLBACK", "")
    budget_usd: float = float(os.getenv("BUDGET_USD", "5.00"))
    mock_mode: bool = os.getenv("MOCK_MODE", "false").lower() == "true"


settings = Settings()