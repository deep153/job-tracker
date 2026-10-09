"""Approximate AI cost from token counts."""

# US dollars per million (input, output) tokens, from https://docs.anthropic.com/en/docs/about-claude/pricing.
# Longest matching prefix wins, so dated snapshots ("claude-haiku-4-5-20251001") use their model's price.
_PRICES: dict[str, tuple[float, float]] = {
    "claude-fable-5-1": (10, 50),
    "claude-fable-5": (10, 50),
    "claude-mythos-5": (10, 50),
    "claude-opus-5-5": (4, 20),
    "claude-opus-5": (5, 25),
    "claude-opus-4-8": (5, 25),
    "claude-opus-4-7": (5, 25),
    "claude-opus-4-6": (5, 25),
    "claude-opus-4-5": (5, 25),
    "claude-opus-4-1": (15, 75),
    "claude-opus-4": (15, 75),
    "claude-sonnet-5-5": (2, 10),
    "claude-sonnet-5": (2, 10),
    "claude-sonnet-4": (3, 15),
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-haiku-4-5": (1, 5),
    "claude-3-5-haiku": (0.80, 4),
}
# Haiku 5.5 costs more for prompts over 100,000 tokens.
_LONG_PROMPT_PRICES: dict[str, tuple[int, tuple[float, float]]] = {"claude-haiku-5-5": (100_000, (0.50, 2.50))}
# Unknown models are estimated at their line's current price.
_LINE_PRICES = {"haiku": (0.10, 0.50), "sonnet": (2, 10), "opus": (4, 20), "fable": (10, 50), "mythos": (10, 50)}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Approximate cost of one call in US dollars."""
    known = sorted((key for key in _PRICES if model.startswith(key)), key=len, reverse=True)
    if known:
        prices = _PRICES[known[0]]
        if known[0] in _LONG_PROMPT_PRICES and input_tokens > _LONG_PROMPT_PRICES[known[0]][0]:
            prices = _LONG_PROMPT_PRICES[known[0]][1]
    else:
        prices = next((p for line, p in _LINE_PRICES.items() if line in model), _LINE_PRICES["sonnet"])
    return (input_tokens * prices[0] + output_tokens * prices[1]) / 1_000_000
