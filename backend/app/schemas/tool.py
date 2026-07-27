from pydantic import BaseModel

from app.tools.base import RiskLevel, ToolPermission


class ToolMetadataResponse(BaseModel):
    name: str
    description: str
    version: str
    risk_level: RiskLevel
    permission: ToolPermission
    timeout_seconds: int
    enabled: bool
    input_schema: dict | None
    output_schema: dict | None
    metadata: dict


class ToolResponse(BaseModel):
    id: str
    metadata: ToolMetadataResponse


class ToolListResponse(BaseModel):
    tools: list[ToolResponse]
    total: int
