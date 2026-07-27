import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from app.core.events import AgentEvent, Component, EventType, Status
from app.skills.base import SkillInput, SkillOutput
from app.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


class SkillExecutor:
    def __init__(
        self,
        registry: SkillRegistry,
        event_emitter: object | None = None,
        hook_manager: object | None = None,
    ) -> None:
        self._registry = registry
        self._emitter = event_emitter
        self._hooks = hook_manager

    async def execute(
        self,
        skill_name: str,
        task: str,
        run_id: str = "",
        trace_id: str = "",
        parameters: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> SkillOutput:
        skill = self._registry.get_by_name(skill_name)
        if skill is None:
            raise ValueError(f"Skill '{skill_name}' not found in registry")

        if not skill.metadata.enabled:
            raise ValueError(f"Skill '{skill_name}' is disabled")

        skill_input = SkillInput(
            task=task,
            parameters=parameters or {},
            context=context or {},
        )

        await self._emit_event(
            run_id, trace_id, EventType.skill_started, Status.running,
            component=Component.skill,
            metadata={"skill": skill.metadata.name, "version": skill.metadata.version},
        )

        if self._hooks is not None:
            try:
                if hasattr(self._hooks, "run_pipeline"):
                    hook_result = await self._hooks.run_pipeline(
                        "before_skill", {"skill": skill, "input": skill_input}
                    )
                    if getattr(hook_result, "action", None) == "BLOCK":
                        return SkillOutput(
                            result=None,
                            summary=f"Blocked by hook: {getattr(hook_result, 'reason', 'unknown')}",
                            metadata={"blocked": True},
                        )
            except Exception as exc:
                logger.warning("Before-skill hooks failed: %s", exc)

        try:
            output = await skill.execute(skill_input)
        except Exception as exc:
            logger.exception("Skill '%s' execution failed", skill_name)
            await self._emit_event(
                run_id, trace_id, EventType.error, Status.failed,
                component=Component.skill,
                error={"message": str(exc), "skill": skill_name},
            )
            return SkillOutput(
                result=None,
                summary=f"Execution failed: {exc!s}",
                metadata={"error": str(exc)},
            )

        if self._hooks is not None:
            try:
                if hasattr(self._hooks, "run_pipeline"):
                    await self._hooks.run_pipeline(
                        "after_skill", {"skill": skill, "input": skill_input, "output": output}
                    )
            except Exception as exc:
                logger.warning("After-skill hooks failed: %s", exc)

        await self._emit_event(
            run_id, trace_id, EventType.skill_completed, Status.completed,
            component=Component.skill,
            metadata={"skill": skill.metadata.name},
        )

        return output

    async def _emit_event(
        self,
        run_id: str,
        trace_id: str,
        event_type: EventType,
        status: Status,
        component: Component = Component.skill,
        metadata: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
    ) -> None:
        if self._emitter is None:
            return
        event = AgentEvent(
            event_id=str(uuid.uuid4()),
            run_id=run_id,
            trace_id=trace_id,
            timestamp=datetime.now(UTC),
            event_type=event_type,
            component=component,
            status=status,
            metadata=metadata or {},
            error=error,
        )
        try:
            await self._emitter.emit(event)
        except Exception as exc:
            logger.debug("Failed to emit event: %s", exc)
