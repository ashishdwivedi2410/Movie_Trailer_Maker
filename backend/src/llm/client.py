"""LLM client wrapper: primary model -> fallback model -> replay cache, with
a basic circuit breaker. This is the single choke point all agents call
through, which is what makes the 'preferred model becomes unavailable'
surprise event a one-place fix. See ARCHITECTURE.md section 8.

This is also the single choke point for cost tracking (section 8's budget
guard): every call, mock or real, is priced and accumulated here so that
node_finalize (src/graph/pipeline.py) can read back how much of a run's
budget a given trailer actually consumed.
"""
from src.config import settings

# Rough, deterministic per-call pricing used until real token/dollar usage
# comes back from the Anthropic API (see the TODO in call() below): tokens
# are approximated from character count and priced at a flat blended rate.
# This is intentionally conservative-simple rather than model-specific -
# swap in real `usage` accounting from the API response once the primary
# call path is implemented, without changing anything that reads
# total_cost_usd downstream.
CHARS_PER_TOKEN = 4
COST_PER_1K_TOKENS_USD = 0.01


class LLMClient:
    def __init__(self):
        self.consecutive_failures = 0
        self.circuit_open = False
        self.total_cost_usd = 0.0

    def call(self, prompt: str) -> str:
        if settings.mock_mode:
            from src.llm.replay import get_cached_response
            response = get_cached_response(prompt)
            self._record_cost(prompt, response)
            return response

        # TODO:
        #  1. try settings.model_primary via the Anthropic API
        #  2. on failure, increment consecutive_failures; if above a threshold,
        #     open the circuit and go straight to settings.model_fallback
        #  3. once real usage is available on the response, price it properly
        #     and call self._record_cost with the real token counts instead
        #     of the char-based estimate
        raise NotImplementedError

    def _record_cost(self, prompt: str, response: str) -> None:
        """Accumulates estimated spend into total_cost_usd against
        settings.budget_usd. Counts mock/replay calls too, since replay is
        also the fallback path for the 'model unavailable' surprise event
        and should still count against budget the same way a real call
        would - a run that's over budget shouldn't look cheap just because
        it fell back to the cache."""
        approx_tokens = (len(prompt) + len(response)) / CHARS_PER_TOKEN
        self.total_cost_usd += (approx_tokens / 1000) * COST_PER_1K_TOKENS_USD

    def over_budget(self) -> bool:
        return self.total_cost_usd > settings.budget_usd