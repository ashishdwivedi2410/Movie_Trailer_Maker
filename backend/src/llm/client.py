"""LLM client wrapper: primary model -> fallback model -> replay cache, with
a basic circuit breaker. This is the single choke point all agents call
through, which is what makes the 'preferred model becomes unavailable'
surprise event a one-place fix. See ARCHITECTURE.md section 8."""
from src.config import settings


class LLMClient:
    def __init__(self):
        self.consecutive_failures = 0
        self.circuit_open = False

    def call(self, prompt: str) -> str:
        if settings.mock_mode:
            from src.llm.replay import get_cached_response
            return get_cached_response(prompt)

        # TODO:
        #  1. try settings.model_primary via the Anthropic API
        #  2. on failure, increment consecutive_failures; if above a threshold,
        #     open the circuit and go straight to settings.model_fallback
        #  3. record actual token/dollar cost against settings.budget_usd
        #     (see src/observability/decision_log.py)
        raise NotImplementedError