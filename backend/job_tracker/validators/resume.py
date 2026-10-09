from pydantic import BaseModel, Field


class ResumeMappingIn(BaseModel):
    summary: list[int] = Field(max_length=500)
    skills: list[int] = Field(max_length=500)


class ResumeSkillsIn(BaseModel):
    skills: list[str] = Field(max_length=500)
