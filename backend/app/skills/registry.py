from app.skills.base import BaseSkill


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, BaseSkill] = {}
        self._skills_by_name: dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill) -> None:
        self._skills[skill.metadata.name] = skill
        self._skills_by_name[skill.metadata.name.lower()] = skill

    def get(self, skill_id: str) -> BaseSkill | None:
        return self._skills.get(skill_id)

    def get_by_name(self, name: str) -> BaseSkill | None:
        return self._skills_by_name.get(name.lower())

    def list_all(self) -> list[BaseSkill]:
        return list(self._skills.values())

    def list_enabled(self) -> list[BaseSkill]:
        return [s for s in self._skills.values() if s.metadata.enabled]

    def remove(self, skill_id: str) -> bool:
        skill = self._skills.pop(skill_id, None)
        if skill is not None:
            self._skills_by_name.pop(skill.metadata.name.lower(), None)
            return True
        return False

    def clear(self) -> None:
        self._skills.clear()
        self._skills_by_name.clear()

    @property
    def count(self) -> int:
        return len(self._skills)
