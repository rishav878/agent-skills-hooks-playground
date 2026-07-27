import pytest

from app.skills.base import BaseSkill, SkillInput, SkillMetadata, SkillOutput
from app.skills.executor import SkillExecutor
from app.skills.loader import SkillLoader
from app.skills.registry import SkillRegistry
from app.skills.selector import SkillSelector
from app.skills.skills.code_review import CodeReviewSkill
from app.skills.skills.data_analysis import DataAnalysisSkill
from app.skills.skills.research import ResearchSkill


class TestSkillMetadata:
    def test_minimal_metadata(self) -> None:
        meta = SkillMetadata(
            name="test", description="test skill", version="1.0.0", instructions="do stuff"
        )
        assert meta.name == "test"
        assert meta.version == "1.0.0"
        assert meta.enabled is True
        assert meta.allowed_tools is None

    def test_full_metadata(self) -> None:
        meta = SkillMetadata(
            name="full",
            description="full skill",
            version="2.0.0",
            instructions="do full stuff",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            allowed_tools=["tool1", "tool2"],
            metadata={"key": "value"},
            enabled=False,
        )
        assert meta.allowed_tools == ["tool1", "tool2"]
        assert meta.enabled is False


class TestSkillRegistry:
    def test_register_and_get(self) -> None:
        registry = SkillRegistry()
        skill = _create_test_skill("skill_a")
        registry.register(skill)
        assert registry.get("skill_a") is skill
        assert registry.get_by_name("skill_a") is skill

    def test_get_nonexistent(self) -> None:
        registry = SkillRegistry()
        assert registry.get("nonexistent") is None

    def test_list_all(self) -> None:
        registry = SkillRegistry()
        registry.register(_create_test_skill("a"))
        registry.register(_create_test_skill("b"))
        assert registry.count == 2
        assert len(registry.list_all()) == 2

    def test_list_enabled(self) -> None:
        registry = SkillRegistry()
        s1 = _create_test_skill("enabled_a")
        s2_meta = SkillMetadata(
            name="disabled_b",
            description="disabled",
            version="1.0",
            instructions="test",
            enabled=False,
        )
        s2 = _create_test_skill_from_meta(s2_meta)
        registry.register(s1)
        registry.register(s2)
        enabled = registry.list_enabled()
        assert len(enabled) == 1
        assert enabled[0].metadata.name == "enabled_a"

    def test_remove(self) -> None:
        registry = SkillRegistry()
        registry.register(_create_test_skill("x"))
        assert registry.remove("x") is True
        assert registry.get("x") is None
        assert registry.remove("x") is False

    def test_clear(self) -> None:
        registry = SkillRegistry()
        registry.register(_create_test_skill("a"))
        registry.register(_create_test_skill("b"))
        registry.clear()
        assert registry.count == 0


class TestSkillLoader:
    def test_load_builtins(self) -> None:
        loader = SkillLoader()
        skills = loader.load_builtins()
        assert len(skills) == 3
        names = {s.metadata.name for s in skills}
        assert names == {"research", "data_analysis", "code_review"}

    def test_load_twice_does_not_duplicate(self) -> None:
        loader = SkillLoader()
        loader.load_builtins()
        loader.load_builtins()
        assert loader.registry.count == 3


class TestBaseSkill:
    @pytest.mark.asyncio
    async def test_research_skill_execute(self) -> None:
        skill = ResearchSkill()
        result = await skill.execute(SkillInput(task="test research topic"))
        assert result.result["summary"].startswith("Research summary")
        assert len(result.result["key_findings"]) == 2

    @pytest.mark.asyncio
    async def test_data_analysis_skill_execute(self) -> None:
        skill = DataAnalysisSkill()
        result = await skill.execute(
            SkillInput(
                task="analyze data",
                parameters={"analysis_type": "trend", "data_path": "/data/test.csv"},
            )
        )
        assert "trend" in result.result["summary"]
        assert result.result["statistics"]["row_count"] == 100

    @pytest.mark.asyncio
    async def test_code_review_skill_execute(self) -> None:
        skill = CodeReviewSkill()
        result = await skill.execute(
            SkillInput(
                task="review code",
                parameters={"language": "python", "file_path": "/src/main.py", "focus": "all"},
            )
        )
        assert len(result.result["issues"]) == 2
        assert result.result["score"] == 75

    def test_skill_metadata_property(self) -> None:
        skill = ResearchSkill()
        assert skill.metadata.name == "research"
        assert skill.metadata.version == "1.0.0"


class TestSkillSelector:
    @pytest.mark.asyncio
    async def test_keyword_select_research(self) -> None:
        registry = SkillRegistry()
        registry.register(ResearchSkill())
        registry.register(DataAnalysisSkill())
        selector = SkillSelector(registry)
        selection = await selector.select("research AI frameworks")
        assert selection.skill_name == "research"
        assert selection.confidence > 0

    @pytest.mark.asyncio
    async def test_keyword_select_analysis(self) -> None:
        registry = SkillRegistry()
        registry.register(ResearchSkill())
        registry.register(DataAnalysisSkill())
        selector = SkillSelector(registry)
        selection = await selector.select("analyze this csv data")
        assert selection.skill_name == "data_analysis"
        assert selection.confidence > 0

    @pytest.mark.asyncio
    async def test_empty_registry(self) -> None:
        registry = SkillRegistry()
        selector = SkillSelector(registry)
        selection = await selector.select("anything")
        assert selection.confidence == 0.0
        assert selection.reasoning == "No skills available"

    @pytest.mark.asyncio
    async def test_single_skill_always_selected(self) -> None:
        registry = SkillRegistry()
        registry.register(ResearchSkill())
        selector = SkillSelector(registry)
        selection = await selector.select("random text")
        assert selection.skill_name == "research"


class TestSkillExecutor:
    @pytest.mark.asyncio
    async def test_execute_existing_skill(self) -> None:
        registry = SkillRegistry()
        registry.register(ResearchSkill())
        executor = SkillExecutor(registry)
        result = await executor.execute("research", "test topic")
        assert result.result is not None
        assert "Research summary" in result.result["summary"]

    @pytest.mark.asyncio
    async def test_execute_nonexistent_skill(self) -> None:
        registry = SkillRegistry()
        executor = SkillExecutor(registry)
        with pytest.raises(ValueError, match="not found"):
            await executor.execute("nonexistent", "task")

    @pytest.mark.asyncio
    async def test_execute_disabled_skill(self) -> None:
        registry = SkillRegistry()
        meta = SkillMetadata(
            name="disabled",
            description="disabled skill",
            version="1.0",
            instructions="test",
            enabled=False,
        )
        skill = _create_test_skill_from_meta(meta)
        registry.register(skill)
        executor = SkillExecutor(registry)
        with pytest.raises(ValueError, match="disabled"):
            await executor.execute("disabled", "task")


@pytest.mark.asyncio
async def test_list_skills_via_api(client: pytest.FixtureRequest) -> None:
    response = await client.get("/api/v1/skills")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 3
    names = {s["id"] for s in data["skills"]}
    assert "research" in names
    assert "data_analysis" in names
    assert "code_review" in names


@pytest.mark.asyncio
async def test_get_skill_by_name_via_api(client: pytest.FixtureRequest) -> None:
    response = await client.get("/api/v1/skills/research")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "research"
    assert data["metadata"]["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_get_skill_not_found_via_api(client: pytest.FixtureRequest) -> None:
    response = await client.get("/api/v1/skills/nonexistent")
    assert response.status_code == 404


def _create_test_skill(name: str) -> BaseSkill:
    meta = SkillMetadata(
        name=name, description=f"skill {name}", version="1.0", instructions="test"
    )
    return _create_test_skill_from_meta(meta)


def _create_test_skill_from_meta(meta: SkillMetadata) -> BaseSkill:
    class TestSkillImpl(BaseSkill):
        async def execute(self, input_data: SkillInput) -> SkillOutput:
            return SkillOutput(result={"name": self.metadata.name})

    return TestSkillImpl(meta)
