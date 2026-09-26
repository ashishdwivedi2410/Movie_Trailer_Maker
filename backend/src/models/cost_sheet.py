"""Cost Sheet - per-resource pricing used by the budget guard described in
ARCHITECTURE.md sections 3.1 and 8. Parsed at pipeline setup alongside
contracts/policies (see src.ingest.cost_sheet) so a trailer plan's segments
can eventually be priced by what they actually consume (LLM calls, music
licensing, editor time, ...), not just by the flat per-call estimate
src.llm.client.LLMClient falls back to when a resource isn't in the sheet.

This is the ingest-layer counterpart to settings.budget_usd (src/config.py):
budget_usd is the total spend ceiling for a run; the cost sheet is what
prices the individual resources a trailer plan draws against that ceiling.
"""
from pydantic import BaseModel


class CostLineItem(BaseModel):
    resource_type: str  # e.g. "llm_call", "music_license", "editor_time"
    resource_id: str
    unit_cost_usd: float
    notes: str | None = None


class CostSheet(BaseModel):
    line_items: list[CostLineItem] = []

    def unit_cost(self, resource_type: str, resource_id: str) -> float | None:
        """Looks up a line item's unit cost, or None if this resource isn't
        priced in the sheet. Callers should treat a miss as 'no sheet price
        available' and fall back to their own estimate (e.g. LLMClient's
        char-based approximation) - never treat a miss as free."""
        for item in self.line_items:
            if item.resource_type == resource_type and item.resource_id == resource_id:
                return item.unit_cost_usd
        return None