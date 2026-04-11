from pydantic import BaseModel


class ThemeResult(BaseModel):
    paper_id: str
    name: str
    description: str = ""
    positions: list[dict] = []


class ClaimResult(BaseModel):
    paper_id: str
    theme_id: str = ""
    theme_name: str = ""
    text: str
    page: int = 0
    paragraph: int = 0
    deep: str = ""
    summary: str = ""
    source: dict = {}


class ClaimSearchResult(BaseModel):
    claim: ClaimResult
    score: float


class ThemeMapEntry(BaseModel):
    name: str
    description: str = ""
    paper_ids: list[str] = []
    aliases: list[str] = []


class ThemeReviewResult(BaseModel):
    theme_id: str
    label: str = ""
    review: str = ""
    consensus: list[str] = []
    disagreements: list[str] = []
    gaps: list[str] = []
    key_claims: list[dict] = []


class ReviewSection(BaseModel):
    title: str = ""
    theme_id: str
    label: str = ""
    content: str = ""
    claim_ids: list[str] = []
