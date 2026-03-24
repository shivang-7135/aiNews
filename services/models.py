from pydantic import BaseModel, Field

from services.config import TOPICS

try:
    from pydantic import field_validator as pydantic_validator
except ImportError:  # Pydantic v1 fallback
    from pydantic import validator as pydantic_validator


class SubscribeRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    topics: list[str] = Field(default_factory=list)
    country: str = Field(default="GLOBAL", min_length=2, max_length=10)
    language: str = Field(default="en", min_length=2, max_length=5)

    @pydantic_validator("topics")
    def validate_topics(cls, value: list[str]) -> list[str]:
        allowed = {k for k in TOPICS.keys() if k != "all"}
        clean: list[str] = []
        for item in value or []:
            topic = str(item or "").strip().lower()
            if topic in allowed and topic not in clean:
                clean.append(topic)
            if len(clean) >= 8:
                break
        return clean


class ArticleBriefRequest(BaseModel):
    title: str = Field(min_length=1, max_length=220)
    source: str = Field(default="", max_length=120)
    link: str = Field(default="", max_length=1000)
    summary: str = Field(default="", max_length=1800)
    why_it_matters: str = Field(default="", max_length=260)
    topic: str = Field(default="general", max_length=40)
    language: str = Field(default="en", min_length=2, max_length=5)
