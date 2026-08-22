from pydantic import BaseModel, ConfigDict, Field


class GeneratedSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1)
    possible_cause: str | None = None
    uncertainty: str = Field(min_length=1)
