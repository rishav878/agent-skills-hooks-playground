from collections import defaultdict

from app.hooks.base import BaseHook, LifecycleEvent


class HookRegistry:
    def __init__(self) -> None:
        self._hooks: dict[str, BaseHook] = {}
        self._hooks_by_event: dict[LifecycleEvent, list[BaseHook]] = defaultdict(list)

    def register(self, hook: BaseHook) -> None:
        self._hooks[hook.metadata.name] = hook
        self._hooks_by_event[hook.metadata.lifecycle_event].append(hook)

    def get(self, hook_id: str) -> BaseHook | None:
        return self._hooks.get(hook_id)

    def get_by_name(self, name: str) -> BaseHook | None:
        return self._hooks.get(name)

    def list_all(self) -> list[BaseHook]:
        return list(self._hooks.values())

    def list_enabled(self) -> list[BaseHook]:
        return [h for h in self._hooks.values() if h.metadata.enabled]

    def get_for_event(self, event: LifecycleEvent) -> list[BaseHook]:
        return [
            h
            for h in self._hooks_by_event.get(event, [])
            if h.metadata.enabled
        ]

    def remove(self, hook_id: str) -> bool:
        hook = self._hooks.pop(hook_id, None)
        if hook is not None:
            event_list = self._hooks_by_event.get(hook.metadata.lifecycle_event, [])
            if hook in event_list:
                event_list.remove(hook)
            return True
        return False

    def clear(self) -> None:
        self._hooks.clear()
        self._hooks_by_event.clear()

    @property
    def count(self) -> int:
        return len(self._hooks)
