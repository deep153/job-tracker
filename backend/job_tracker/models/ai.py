from dataclasses import dataclass

DEFAULT_SCORING_MODEL = "claude-haiku-5-5"
DEFAULT_TAILORING_MODEL = "claude-sonnet-5-5"

SUGGESTED_MODELS = ["claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5", "claude-fable-5-1"]


@dataclass(frozen=True)
class AiSettings:
    anthropic_api_key: str | None
    scoring_model: str
    tailoring_model: str


@dataclass(frozen=True)
class UsageByKind:
    kind: str
    calls: int
    cost_usd: float
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class RunCost:
    run_id: int
    started_at: str
    scored_jobs: int
    ai_cost_usd: float


@dataclass(frozen=True)
class CostSummary:
    by_kind: list[UsageByKind]
    recent_runs: list[RunCost]

    @property
    def total_usd(self) -> float:
        return sum(usage.cost_usd for usage in self.by_kind)
