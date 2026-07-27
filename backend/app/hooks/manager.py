import logging
from typing import Any

from app.hooks.base import HookAction, HookResult, LifecycleEvent
from app.hooks.executor import HookExecutor
from app.hooks.registry import HookRegistry

logger = logging.getLogger(__name__)


class HookManager:
    def __init__(
        self,
        registry: HookRegistry | None = None,
        executor: HookExecutor | None = None,
    ) -> None:
        self._registry = registry or HookRegistry()
        self._executor = executor or HookExecutor(self._registry)

    @property
    def registry(self) -> HookRegistry:
        return self._registry

    async def run_pipeline(
        self, event: LifecycleEvent, context: dict[str, Any] | None = None
    ) -> HookResult:
        if context is None:
            context = {}

        logger.debug("Running hook pipeline for event: %s", event.value)
        result = await self._executor.run_pipeline(event, context)

        if result.action == HookAction.BLOCK:
            logger.info("Hook pipeline BLOCKED at %s: %s", event.value, result.reason)
        elif result.action == HookAction.APPROVAL_REQUIRED:
            logger.info("Hook pipeline paused for APPROVAL at %s", event.value)
        elif result.action == HookAction.RETRY:
            logger.info("Hook pipeline requested RETRY at %s", event.value)
        elif result.action == HookAction.MODIFY:
            logger.debug("Hook pipeline MODIFIED at %s", event.value)

        return result
