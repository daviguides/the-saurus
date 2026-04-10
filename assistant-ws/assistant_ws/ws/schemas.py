from pydantic import BaseModel


class IncomingMessage(BaseModel):
    text: str
    session_id: str | None = None


class TokenEvent(BaseModel):
    content: str


class StepEvent(BaseModel):
    step: str
    agent: str | None = None
    tool: str | None = None


class DoneEvent(BaseModel):
    metrics: dict


class ReferenceItem(BaseModel):
    title: str
    authors: list[str] | None = None
    year: int | None = None
    doi: str | None = None
    snippet: str | None = None
    score: float | None = None


class ReferencesEvent(BaseModel):
    references: list[ReferenceItem]
