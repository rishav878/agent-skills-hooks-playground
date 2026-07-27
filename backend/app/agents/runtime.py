import logging
from typing import Any

from app.agents.events import EventEmitter
from app.agents.graph import build_graph
from app.agents.state import AgentState
from app.hooks.manager import HookManager
from app.skills.loader import SkillLoader
from app.tools.executor import ToolExecutor

logger = logging.getLogger(__name__)


class AgentRuntime:
    def __init__(
        self,
        skill_loader: SkillLoader,
        hook_manager: HookManager,
        tool_executor: ToolExecutor,
        llm_provider: Any | None = None,
    ) -> None:
        self._skill_loader = skill_loader
        self._hook_manager = hook_manager
        self._tool_executor = tool_executor
        self._llm_provider = llm_provider
        self._graph: Any | None = None

    def _get_graph(self) -> Any:
        if self._graph is None:
            workflow = build_graph()
            self._graph = workflow.compile()
        return self._graph

    async def run(
        self,
        payload: dict[str, Any],
        event_emitter: EventEmitter | None = None,
        event_service: Any = None,
    ) -> dict[str, Any]:
        emitter = event_emitter or EventEmitter()

        initial_state = AgentState(
            run_id=payload.pop("run_id", None),
            trace_id=payload.pop("trace_id", None),
            request_payload=payload,
            skill_loader=self._skill_loader,
            hook_manager=self._hook_manager,
            tool_executor=self._tool_executor,
            llm_provider=self._llm_provider,
            event_emitter=emitter,
            event_service=event_service,
        )

        return await self._invoke(initial_state, emitter)

    async def resume(
        self,
        state: AgentState,
        event_emitter: EventEmitter | None = None,
    ) -> dict[str, Any]:
        emitter = event_emitter or EventEmitter()
        state.event_emitter = emitter
        state.resumed = True
        state.approval_granted = True

        if state.skill_loader is None:
            state.skill_loader = self._skill_loader
        if state.hook_manager is None:
            state.hook_manager = self._hook_manager
        if state.tool_executor is None:
            state.tool_executor = self._tool_executor
        if state.llm_provider is None:
            state.llm_provider = self._llm_provider

        return await self._invoke(state, emitter)

    async def _invoke(
        self, initial_state: AgentState, emitter: EventEmitter
    ) -> dict[str, Any]:
        graph = self._get_graph()
        try:
            final = await graph.ainvoke(initial_state)
        except Exception as exc:
            logger.exception("Agent run failed")
            return {
                "run_id": initial_state.run_id or "",
                "error": str(exc),
                "status": "failed",
                "events": [],
            }

        error = final.get("error") if isinstance(final, dict) else getattr(final, "error", None)
        run_id = final.get("run_id", "") if isinstance(final, dict) else getattr(final, "run_id", "")
        trace_id = final.get("trace_id", "") if isinstance(final, dict) else getattr(final, "trace_id", "")
        task = final.get("task", "") if isinstance(final, dict) else getattr(final, "task", "")
        retry_count = final.get("retry_count", 0) if isinstance(final, dict) else getattr(final, "retry_count", 0)

        skill_selection = final.get("skill_selection") if isinstance(final, dict) else final.skill_selection

        response_val = final.get("response") if isinstance(final, dict) else final.response

        events_data = [
            {
                "event_id": e.event_id,
                "event_type": e.event_type.value,
                "component": e.component.value,
                "status": e.status.value,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in emitter.events
        ]

        if error:
            return {
                "run_id": run_id,
                "trace_id": trace_id,
                "error": error,
                "status": "failed",
                "retry_count": retry_count,
                "events": events_data,
            }

        # Check if run is waiting for approval
        approval_required = (
            isinstance(final, dict)
            and final.get("approval_required")
            and not final.get("approval_granted")
        )
        if not isinstance(final, dict):
            approval_required = final.approval_required and not final.approval_granted

        if approval_required:
            return {
                "run_id": run_id,
                "trace_id": trace_id,
                "status": "waiting_approval",
                "events": events_data,
            }

        skill_name = (
            skill_selection.get("skill_name")
            if isinstance(skill_selection, dict)
            else (skill_selection.skill_name if skill_selection else None)
        )
        response_result = (
            response_val.get("result")
            if isinstance(response_val, dict)
            else (response_val.result if response_val else None)
        )
        return {
            "run_id": run_id,
            "trace_id": trace_id,
            "task": task,
            "skill_used": skill_name,
            "result": response_result,
            "status": "completed",
            "retry_count": retry_count,
            "events": events_data,
        }
