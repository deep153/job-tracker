import pytest
from pydantic import ValidationError

from job_tracker.validators.settings import ModelsIn


def test_model_names_are_trimmed() -> None:
    body = ModelsIn(scoring_model=" claude-haiku-5-5 ", tailoring_model="claude-sonnet-5-5")

    assert (body.scoring_model, body.tailoring_model) == ("claude-haiku-5-5", "claude-sonnet-5-5")


@pytest.mark.parametrize("name", ["", "claude haiku", "x" * 101, "../etc", "-claude"])
def test_bad_model_names_are_rejected(name: str) -> None:
    with pytest.raises(ValidationError):
        ModelsIn(scoring_model=name, tailoring_model="claude-opus-5-5")
