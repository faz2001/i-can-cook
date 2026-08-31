from pydantic import BaseModel


class RecommendationQuery(BaseModel):
    query: str
    use_pantry: bool = False
    top_n: int = 5


class RecommendedRecipe(BaseModel):
    id: str
    name_en: str
    cuisine: str
    course: str | None
    tags: list[str]
    score: float


class RecommendationResult(BaseModel):
    query: str
    extracted_tags: dict[str, list[str]]
    tier_used: str
    tier_confidence: float
    results: list[RecommendedRecipe]
