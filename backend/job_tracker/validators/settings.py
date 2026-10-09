import re

from pydantic import BaseModel, Field, field_validator

_MODEL_NAME = re.compile(r"^[a-z0-9][a-z0-9.\-]{1,99}$", re.I)


class ApiKeyIn(BaseModel):
    """An API key; a blank key clears the stored one."""

    key: str = Field(max_length=500)


class ModelsIn(BaseModel):
    scoring_model: str
    tailoring_model: str

    @field_validator("scoring_model", "tailoring_model")
    @classmethod
    def _model_name(cls, value: str) -> str:
        name = value.strip()
        if not _MODEL_NAME.match(name):
            raise ValueError("Enter a Claude model name, like claude-haiku-5-5.")
        return name
