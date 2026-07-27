from fastapi import APIRouter, Depends, HTTPException

from app.schemas.skill import SkillListResponse, SkillMetadataResponse, SkillResponse
from app.skills.loader import SkillLoader

router = APIRouter(prefix="/skills", tags=["skills"])

_loader: SkillLoader | None = None


def get_loader() -> SkillLoader:
    global _loader
    if _loader is None:
        _loader = SkillLoader()
        _loader.load_builtins()
    return _loader


@router.get("", response_model=SkillListResponse)
async def list_skills(loader: SkillLoader = Depends(get_loader)) -> SkillListResponse:
    skills = loader.registry.list_all()
    return SkillListResponse(
        skills=[
            SkillResponse(
                id=s.metadata.name,
                metadata=SkillMetadataResponse(
                    name=s.metadata.name,
                    description=s.metadata.description,
                    version=s.metadata.version,
                    input_schema=s.metadata.input_schema,
                    output_schema=s.metadata.output_schema,
                    allowed_tools=s.metadata.allowed_tools,
                    enabled=s.metadata.enabled,
                ),
            )
            for s in skills
        ],
        total=len(skills),
    )


@router.get("/{skill_id}", response_model=SkillResponse)
async def get_skill(
    skill_id: str, loader: SkillLoader = Depends(get_loader)
) -> SkillResponse:
    skill = loader.registry.get(skill_id)
    if skill is None:
        skill = loader.registry.get_by_name(skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")
    return SkillResponse(
        id=skill.metadata.name,
        metadata=SkillMetadataResponse(
            name=skill.metadata.name,
            description=skill.metadata.description,
            version=skill.metadata.version,
            input_schema=skill.metadata.input_schema,
            output_schema=skill.metadata.output_schema,
            allowed_tools=skill.metadata.allowed_tools,
            enabled=skill.metadata.enabled,
        ),
    )
