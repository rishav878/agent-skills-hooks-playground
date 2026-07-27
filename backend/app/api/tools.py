from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.tool import ToolListResponse, ToolMetadataResponse, ToolResponse
from app.tools.loader import ToolLoader

router = APIRouter(prefix="/tools", tags=["tools"])

_loader: ToolLoader | None = None


def get_loader() -> ToolLoader:
    global _loader
    if _loader is None:
        _loader = ToolLoader()
        _loader.load_builtins()
    return _loader


def _to_response(tool: Any) -> ToolResponse:
    return ToolResponse(
        id=tool.metadata.name,
        metadata=ToolMetadataResponse(
            name=tool.metadata.name,
            description=tool.metadata.description,
            version=tool.metadata.version,
            risk_level=tool.metadata.risk_level,
            permission=tool.metadata.permission,
            timeout_seconds=tool.metadata.timeout_seconds,
            enabled=tool.metadata.enabled,
            input_schema=tool.metadata.input_schema,
            output_schema=tool.metadata.output_schema,
            metadata=dict(tool.metadata.metadata),
        ),
    )


@router.get("", response_model=ToolListResponse)
async def list_tools(loader: ToolLoader = Depends(get_loader)) -> ToolListResponse:
    tools = loader.registry.list_all()
    return ToolListResponse(
        tools=[_to_response(t) for t in tools],
        total=len(tools),
    )


@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(
    tool_id: str, loader: ToolLoader = Depends(get_loader)
) -> ToolResponse:
    tool = loader.registry.get(tool_id)
    if tool is None:
        tool = loader.registry.get_by_name(tool_id)
    if tool is None:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_id}' not found")
    return _to_response(tool)
