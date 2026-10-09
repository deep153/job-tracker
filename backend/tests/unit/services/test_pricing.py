import pytest

from job_tracker.services.pricing import estimate_cost


def test_prices_follow_the_model() -> None:
    assert estimate_cost("claude-haiku-5-5", 1000, 200) == pytest.approx((1000 * 0.10 + 200 * 0.50) / 1_000_000)
    assert estimate_cost("claude-sonnet-5-5", 1_000_000, 1_000_000) == pytest.approx(12)


def test_dated_snapshots_use_their_models_price() -> None:
    assert estimate_cost("claude-haiku-4-5-20251001", 1_000_000, 0) == pytest.approx(1)


def test_long_prompts_cost_more_on_haiku_5_5() -> None:
    assert estimate_cost("claude-haiku-5-5", 100_000, 0) == pytest.approx(0.01)
    assert estimate_cost("claude-haiku-5-5", 200_000, 0) == pytest.approx(0.10)


def test_unknown_models_are_priced_as_their_line() -> None:
    assert estimate_cost("claude-opus-9", 1_000_000, 0) == pytest.approx(4)
    assert estimate_cost("some-new-model", 1_000_000, 0) == pytest.approx(2)  # sonnet
