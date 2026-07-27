import logging
from difflib import SequenceMatcher

from app.skills.base import BaseSkill, SkillSelection
from app.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


class SkillSelector:
    def __init__(
        self,
        registry: SkillRegistry,
        llm_provider: object | None = None,
        embedding_provider: object | None = None,
        confidence_threshold: float = 0.4,
    ) -> None:
        self._registry = registry
        self._llm = llm_provider
        self._embedding = embedding_provider
        self._threshold = confidence_threshold

    async def select(self, task: str) -> SkillSelection:
        skills = self._registry.list_enabled()
        if not skills:
            return SkillSelection(
                skill_id="", skill_name="", confidence=0.0, reasoning="No skills available"
            )

        if self._llm is not None:
            selection = await self._llm_select(task, skills)
            if selection.confidence >= self._threshold:
                return selection

        if self._embedding is not None:
            selection = await self._embedding_select(task, skills)
            if selection.confidence >= self._threshold:
                return selection

        return self._keyword_select(task, skills)

    async def _llm_select(
        self, task: str, skills: list[BaseSkill]
    ) -> SkillSelection:
        try:
            skill_descriptions = "\n".join(
                f"- {s.metadata.name}: {s.metadata.description}"
                for s in skills
            )

            if hasattr(self._llm, "generate_chat"):
                try:
                    from langchain.prompts import ChatPromptTemplate

                    prompt = ChatPromptTemplate.from_messages([
                        ("system", "You are a skill selector. Select the most appropriate skill for the task."),
                        ("human", "Task: {task}\n\nAvailable skills:\n{skill_descriptions}\n\nReturn only the skill name."),  # noqa: E501
                    ])
                    messages = prompt.format_messages(
                        task=task, skill_descriptions=skill_descriptions
                    )
                    response = await self._llm.generate_chat(
                        [{"role": m.type, "content": m.content} for m in messages]
                    )
                    content = str(response)
                except ImportError:
                    prompt_text = (
                        f"Given this task: '{task}'\n"
                        f"Available skills:\n{skill_descriptions}\n"
                        "Return the name of the single most appropriate skill."
                    )
                    response = await self._llm.generate_chat(
                        [{"role": "user", "content": prompt_text}]
                    )
                    content = str(response)
                chosen_name = content.strip().split("\n")[0].strip("- ").strip()
                for s in skills:
                    if s.metadata.name.lower() in chosen_name.lower():
                        return SkillSelection(
                            skill_id=s.metadata.name,
                            skill_name=s.metadata.name,
                            confidence=0.9,
                            reasoning=f"LLM selected: {chosen_name}",
                        )
            elif hasattr(self._llm, "generate"):
                prompt_text = (
                    f"Given this task: '{task}'\n"
                    f"Available skills:\n{skill_descriptions}\n"
                    "Return the name of the single most appropriate skill."
                )
                response = await self._llm.generate(
                    messages=[{"role": "user", "content": prompt_text}]
                )
                content = getattr(response, "content", str(response))
                chosen_name = content.strip().split("\n")[0].strip("- ").strip()
                for s in skills:
                    if s.metadata.name.lower() in chosen_name.lower():
                        return SkillSelection(
                            skill_id=s.metadata.name,
                            skill_name=s.metadata.name,
                            confidence=0.9,
                            reasoning=f"LLM selected: {chosen_name}",
                        )
        except Exception as exc:
            logger.debug("LLM skill selection failed: %s", exc)

        return SkillSelection(
            skill_id="", skill_name="", confidence=0.0, reasoning="LLM selection failed"
        )

    async def _embedding_select(
        self, task: str, skills: list[BaseSkill]
    ) -> SkillSelection:
        try:
            if hasattr(self._embedding, "embed"):
                task_emb = await self._embedding.embed(task)
                best_score = 0.0
                best_skill = skills[0]
                for s in skills:
                    desc_emb = await self._embedding.embed(
                        f"{s.metadata.name}: {s.metadata.description}"
                    )
                    score = self._cosine_similarity(task_emb, desc_emb)
                    if score > best_score:
                        best_score = score
                        best_skill = s

                return SkillSelection(
                    skill_id=best_skill.metadata.name,
                    skill_name=best_skill.metadata.name,
                    confidence=best_score,
                    reasoning=f"Embedding similarity: {best_score:.2f}",
                )
        except Exception as exc:
            logger.debug("Embedding skill selection failed: %s", exc)

        return SkillSelection(
            skill_id="",
            skill_name="",
            confidence=0.0,
            reasoning="Embedding selection failed",
        )

    def _keyword_select(self, task: str, skills: list[BaseSkill]) -> SkillSelection:
        task_lower = task.lower()
        best_score = 0.0
        best_skill = skills[0]

        for s in skills:
            score = SequenceMatcher(
                None,
                task_lower,
                f"{s.metadata.name} {s.metadata.description}".lower(),
            ).ratio()
            for keyword in s.metadata.name.lower().split():
                if keyword in task_lower:
                    score += 0.2
            for keyword in s.metadata.description.lower().split():
                if keyword in task_lower:
                    score += 0.1

            if score > best_score:
                best_score = score
                best_skill = s

        return SkillSelection(
            skill_id=best_skill.metadata.name,
            skill_name=best_skill.metadata.name,
            confidence=min(best_score, 1.0),
            reasoning=f"Keyword match: {best_score:.2f}",
        )

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b, strict=False))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
