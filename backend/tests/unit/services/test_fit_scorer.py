from typing import Any

import pytest

from job_tracker.clients.claude import LLMError
from job_tracker.models.job import Job
from job_tracker.models.resume import MasterResume
from job_tracker.models.search_settings import SearchSettings
from job_tracker.services.fit_scorer import FitScorer
from tests.support.builders import posting
from tests.support.fake_llm import FakeLLM

RESUME = MasterResume(version=3, text="Backend engineer, 6 years of Python.", skills=["Python", "Go"])
SETTINGS = SearchSettings(roles=["Backend Engineer"], seniority="senior", needs_sponsorship=True)
JOB = Job(id=1, posting=posting(), content_hash="h", closed=False, rejection=None)


def score(llm: FakeLLM) -> Any:
    return FitScorer(llm).score("key", "claude-haiku-5-5", RESUME, SETTINGS, JOB)


def test_the_prompt_has_my_resume_preferences_and_the_job() -> None:
    llm = FakeLLM()

    score(llm)

    [call] = llm.calls
    for expected in [RESUME.text, "Skills: Python, Go", "Roles I want: Backend Engineer", "My level: senior"]:
        assert expected in call.prompt
    for expected in ["I need visa sponsorship: yes", "Title: Backend Engineer", "Company: acme"]:
        assert expected in call.prompt
    assert (call.api_key, call.model) == ("key", "claude-haiku-5-5")


def test_the_answer_is_tidied() -> None:
    llm = FakeLLM()
    llm.answer(
        "Backend Engineer",
        {
            "score": 88.0,
            "reasons": [f"Reason {n}." for n in range(8)],
            "matched_keywords": ["Python", " python ", "Go", ""],
            "missing_keywords": ["Kafka"],
        },
    )

    result = score(llm)

    assert result.score == 88
    assert result.reasons == [f"Reason {n}." for n in range(5)]
    assert result.matched_keywords == ["Python", "Go"]
    assert (result.input_tokens, result.output_tokens) == (FakeLLM.INPUT_TOKENS, FakeLLM.OUTPUT_TOKENS)


@pytest.mark.parametrize(
    "answer",
    [
        {"score": 150, "reasons": [], "matched_keywords": [], "missing_keywords": []},
        {"score": True, "reasons": [], "matched_keywords": [], "missing_keywords": []},
        {"score": 50, "reasons": "fine", "matched_keywords": [], "missing_keywords": []},
        {"score": 50, "reasons": [], "matched_keywords": [1], "missing_keywords": []},
    ],
)
def test_answers_that_dont_make_sense_are_errors(answer: dict[str, Any]) -> None:
    llm = FakeLLM()
    llm.answer("Backend Engineer", answer)

    with pytest.raises(LLMError):
        score(llm)
