import copy
import logging
from typing import Any

from app.hooks.base import BaseHook, HookAction, HookResult, LifecycleEvent

logger = logging.getLogger(__name__)

TERMINAL_ACTIONS = {HookAction.BLOCK, HookAction.APPROVAL_REQUIRED}


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


class HookExecutor:
    def __init__(self, registry: "HookRegistry | None" = None) -> None:
        from app.hooks.registry import HookRegistry

        self._registry = registry or HookRegistry()

    async def run_pipeline(
        self, event: LifecycleEvent, context: dict[str, Any]
    ) -> HookResult:
        hooks = self._get_sorted_hooks(event)
        if not hooks:
            return HookResult(action=HookAction.CONTINUE, reason="No hooks registered")

        cumulative_modifications: dict[str, Any] = {}
        final_action: HookAction = HookAction.CONTINUE
        final_reason = ""

        for hook in hooks:
            hook_context = copy.deepcopy(context)
            if cumulative_modifications:
                hook_context = deep_merge(hook_context, cumulative_modifications)

            try:
                result = await hook.execute(hook_context)
            except Exception as exc:
                logger.exception("Hook '%s' raised an exception", hook.metadata.name)
                return HookResult(
                    action=HookAction.BLOCK,
                    reason=f"Hook '{hook.metadata.name}' failed: {exc!s}",
                )

            logger.debug(
                "Hook '%s' returned %s on event %s",
                hook.metadata.name,
                result.action.value,
                event.value,
            )

            if result.action == HookAction.MODIFY and result.modifications:
                cumulative_modifications = deep_merge(
                    cumulative_modifications, result.modifications
                )
                final_action = HookAction.MODIFY
                final_reason = result.reason or final_reason

            elif result.action in TERMINAL_ACTIONS:
                return HookResult(
                    action=result.action,
                    modifications=cumulative_modifications,
                    reason=result.reason or f"Terminated by hook '{hook.metadata.name}'",
                )

            elif result.action == HookAction.RETRY:
                final_action = HookAction.RETRY
                final_reason = result.reason or final_reason

        return HookResult(
            action=final_action,
            modifications=cumulative_modifications,
            reason=final_reason,
        )

    def _get_sorted_hooks(self, event: LifecycleEvent) -> list[BaseHook]:
        hooks = self._registry.get_for_event(event)
        hooks.sort(key=lambda h: h.metadata.priority)
        return hooks
