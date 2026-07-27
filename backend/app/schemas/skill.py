from pydantic import BaseModel


class SkillMetadataResponse(BaseModel):
    name: str
    description: str
    version: str
    input_schema: dict | None = None
    output_schema: dict | None = None
    allowed_tools: list[str] | None = None
    enabled: bool = True


class SkillResponse(BaseModel):
    id: str
    metadata: SkillMetadataResponse


class SkillListResponse(BaseModel):
    skills: list[SkillResponse]
    total: int
