import logging
import time

from app.hooks.base import BaseHook, HookAction, HookMetadata, HookResult, LifecycleEvent

logger = logging.getLogger(__name__)


class LoggingHook(BaseHook):
    def __init__(self, lifecycle_event: LifecycleEvent) -> None:
        label = lifecycle_event.value
        super().__init__(
            HookMetadata(
                name=f"logging_{label}",
                description=f"Logs execution at {label} lifecycle point",
                lifecycle_event=lifecycle_event,
                priority=100,
            )
        )

    async def execute(self, context: dict) -> HookResult:
        logger.debug(
            "LoggingHook: lifecycle=%s context_keys=%s duration_so_far=%.3fs",
            self.metadata.lifecycle_event.value,
            list(context.keys()),
            time.time() - context.get("_start_time", time.time()),
        )
        return HookResult(action=HookAction.CONTINUE)
