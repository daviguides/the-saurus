from pydantic import BaseModel


class SearchResultWithReference(BaseModel):
    content: str
    score: float
    rank: int
    title: str
    authors: list[str] = []
    year: int | None = None
    doi: str | None = None
    journal: str | None = None
    abstract: str = ""
    section_title: str | None = None

    def to_result_dict(self) -> dict:
        return {
            "content": self.content,
            "score": self.score,
            "rank": self.rank,
            "source": f"{self.title} ({self.year})" if self.year else self.title,
        }

    def to_reference_dict(self) -> dict:
        return {
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "doi": self.doi,
            "journal": self.journal,
            "abstract": self.abstract,
            "section_title": self.section_title,
            "content": self.content,
            "score": self.score,
        }
