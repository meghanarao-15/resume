from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Job:
    id: str
    source: str
    title: str
    company: str
    url: str
    location: str = ""
    description: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def blob(self) -> str:
        return " ".join(
            [
                self.title,
                self.company,
                self.location,
                self.description,
                " ".join(str(v) for v in self.extra.values()),
            ]
        ).lower()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Job:
        return cls(
            id=data["id"],
            source=data["source"],
            title=data["title"],
            company=data["company"],
            url=data["url"],
            location=data.get("location", ""),
            description=data.get("description", ""),
            extra=data.get("extra") or {},
        )


@dataclass
class Match:
    job: Job
    score: float
    reasons: list[str]
    skill_hits: list[str]
    title_fit: bool
    location_fit: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.job.id,
            "source": self.job.source,
            "title": self.job.title,
            "company": self.job.company,
            "url": self.job.url,
            "location": self.job.location,
            "score": round(self.score, 2),
            "reasons": self.reasons,
            "skill_hits": self.skill_hits,
            "title_fit": self.title_fit,
            "location_fit": self.location_fit,
        }
