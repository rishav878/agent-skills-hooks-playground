import importlib
import inspect
import logging
import pkgutil

from app.skills.base import BaseSkill
from app.skills.registry import SkillRegistry
from app.skills.skills.code_review import CodeReviewSkill
from app.skills.skills.data_analysis import DataAnalysisSkill
from app.skills.skills.research import ResearchSkill

logger = logging.getLogger(__name__)

BUILTIN_SKILLS: list[type[BaseSkill]] = [
    ResearchSkill,
    DataAnalysisSkill,
    CodeReviewSkill,
]


class SkillLoader:
    def __init__(self, registry: SkillRegistry | None = None) -> None:
        self._registry = registry or SkillRegistry()

    @property
    def registry(self) -> SkillRegistry:
        return self._registry

    def load_builtins(self) -> list[BaseSkill]:
        loaded: list[BaseSkill] = []
        for skill_cls in BUILTIN_SKILLS:
            try:
                skill = skill_cls()
                self._registry.register(skill)
                loaded.append(skill)
                logger.info("Loaded builtin skill: %s v%s", skill.metadata.name, skill.metadata.version)
            except Exception as exc:
                logger.error("Failed to load skill %s: %s", skill_cls.__name__, exc)
        return loaded

    def discover_package(self, package_name: str) -> list[BaseSkill]:
        discovered: list[BaseSkill] = []
        try:
            package = importlib.import_module(package_name)
        except ImportError:
            logger.warning("Package %s not found for skill discovery", package_name)
            return discovered

        for _importer, modname, _ispkg in pkgutil.walk_packages(
            path=getattr(package, "__path__", []),
            prefix=f"{package_name}.",
        ):
            try:
                module = importlib.import_module(modname)
                for _name, obj in inspect.getmembers(module, inspect.isclass):
                    if (
                        issubclass(obj, BaseSkill)
                        and obj is not BaseSkill
                        and obj not in BUILTIN_SKILLS
                    ):
                        instance = obj()
                        self._registry.register(instance)
                        discovered.append(instance)
                        logger.info("Discovered skill: %s", instance.metadata.name)
            except Exception as exc:
                logger.debug("Skipping module %s: %s", modname, exc)

        return discovered
