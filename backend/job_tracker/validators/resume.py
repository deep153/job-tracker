from pydantic import BaseModel, Field


class ResumeMappingIn(BaseModel):
    summary: list[int] = Field(max_length=500)
    skills: list[int] = Field(max_length=500)
    bullets: list[int] | None = Field(default=None, max_length=500)  # None: not chosen yet


class ResumeSkillsIn(BaseModel):
    skills: list[str] = Field(max_length=500)
