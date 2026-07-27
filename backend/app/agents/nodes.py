import json
import logging
import time
import uuid
from typing import Any

from app.agents.state import AgentState
from app.core.events import Component, EventType, Status
from app.hooks.base import HookAction, LifecycleEvent
from app.skills.base import SkillInput
from app.tools.base import ToolInput

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2


async def _emit(
    state: AgentState,
    event_type: EventType,
    component: Component,
    status: Status,
    **extra: Any,
) -> None:
    if state.event_emitter is None:
        return
    await state.event_emitter.emit_event(
        run_id=state.run_id,
        trace_id=state.trace_id,
        event_type=event_type,
        component=component,
        status=status,
        **extra,
    )


def _run_id(state: AgentState) -> str:
    if not state.run_id:
        state.run_id = str(uuid.uuid4())
    return state.run_id


def _trace_id(state: AgentState) -> str:
    if not state.trace_id:
        state.trace_id = str(uuid.uuid4())
    return state.trace_id


async def initialize_run(state: AgentState) -> AgentState:
    if state.resumed:
        return state
    if not state.run_id:
        state.run_id = str(uuid.uuid4())
    if not state.trace_id:
        state.trace_id = str(uuid.uuid4())
    state.task = state.request_payload.get("task", "")
    state.parameters = state.request_payload.get("parameters", {})

    await _emit(
        state,
        EventType.request_received,
        Component.api,
        Status.running,
        input={"task": state.task, "parameters": state.parameters},
        metadata={"run_id": state.run_id, "trace_id": state.trace_id},
    )
    logger.info(
        "Run %s started: task='%s'", state.run_id, state.task[:80]
    )
    return state


async def before_request_hooks(state: AgentState) -> AgentState:
    if state.blocked or state.resumed:
        return state
    hm = state.hook_manager
    if hm is None:
        return state

    start = time.monotonic()
    await _emit(state, EventType.hook_started, Component.hook, Status.running)
    result = await hm.run_pipeline(
        LifecycleEvent.before_request,
        {"payload": state.task, "task": state.task},
    )
    elapsed = int((time.monotonic() - start) * 1000)
    state.hook_results.append(result)
    state.modifications.update(result.modifications)
    await _emit(
        state,
        EventType.hook_completed,
        Component.hook,
        Status.completed if result.action != HookAction.BLOCK else Status.blocked,
        output={"action": result.action.value, "reason": result.reason},
        duration_ms=elapsed,
    )

    if result.action == HookAction.BLOCK:
        state.blocked = True
        state.error = result.reason
        await _emit(
            state,
            EventType.error,
            Component.hook,
            Status.blocked,
            error={"reason": result.reason},
        )
    elif result.action == HookAction.RETRY and state.retry_count < _MAX_RETRIES:
        state.retry_count += 1
        await _emit(state, EventType.retry_started, Component.runtime, Status.running)
    return state


async def classify_request(state: AgentState) -> AgentState:
    if state.blocked or state.resumed:
        return state
    from app.skills.selector import SkillSelector

    if state.skill_loader is None:
        state.error = "No skill loader available"
        await _emit(
            state,
            EventType.error,
            Component.runtime,
            Status.failed,
            error={"message": "No skill loader available"},
        )
        return state

    selector = SkillSelector(state.skill_loader.registry)
    selection = await selector.select(state.task)

    state.skill_selection = selection
    await _emit(
        state,
        EventType.skill_selected,
        Component.skill,
        Status.completed,
        output={"skill_id": selection.skill_id, "confidence": selection.confidence},
    )

    if not selection.skill_id:
        state.error = f"No skill matched task: {state.task}"
        await _emit(
            state,
            EventType.error,
            Component.skill,
            Status.failed,
            error={"message": state.error},
        )
        state.blocked = True
    return state


async def before_skill_hooks(state: AgentState) -> AgentState:
    if state.blocked or state.resumed or state.skill_selection is None:
        return state
    hm = state.hook_manager
    if hm is None:
        return state

    await _emit(state, EventType.hook_started, Component.hook, Status.running)
    start = time.monotonic()
    result = await hm.run_pipeline(
        LifecycleEvent.before_skill,
        {
            "skill_id": state.skill_selection.skill_id,
            "task": state.task,
        },
    )
    elapsed = int((time.monotonic() - start) * 1000)
    state.hook_results.append(result)
    await _emit(
        state,
        EventType.hook_completed,
        Component.hook,
        Status.completed if result.action != HookAction.BLOCK else Status.blocked,
        output={"action": result.action.value},
        duration_ms=elapsed,
    )

    if result.action == HookAction.BLOCK:
        state.blocked = True
        state.error = result.reason
    elif result.action == HookAction.RETRY:
        state.retry_count += 1
    return state


async def execute_skill(state: AgentState) -> AgentState:
    if state.blocked or state.resumed or state.skill_selection is None:
        return state
    skill_name = state.skill_selection.skill_id
    skill = state.skill_loader.registry.get(skill_name)
    if skill is None:
        state.error = f"Skill '{skill_name}' not found"
        await _emit(
            state,
            EventType.error,
            Component.skill,
            Status.failed,
            error={"message": state.error},
        )
        state.blocked = True
        return state

    await _emit(
        state,
        EventType.skill_started,
        Component.skill,
        Status.running,
        metadata={"skill": skill_name},
    )
    start = time.monotonic()

    try:
        skill_context = dict(state.modifications)
        if state.rag_engine is not None:
            skill_context["rag_engine"] = state.rag_engine
        if state.memory_service is not None:
            skill_context["memory_service"] = state.memory_service
        skill_input = SkillInput(
            task=state.task,
            parameters=state.parameters,
            context=skill_context,
        )
        output = await skill.execute(skill_input)
        elapsed = int((time.monotonic() - start) * 1000)
        state.skill_output = output
        await _emit(
            state,
            EventType.skill_completed,
            Component.skill,
            Status.completed,
            duration_ms=elapsed,
        )
    except Exception as exc:
        elapsed = int((time.monotonic() - start) * 1000)
        logger.exception("Skill execution failed for '%s'", skill_name)
        state.error = str(exc)
        await _emit(
            state,
            EventType.error,
            Component.skill,
            Status.failed,
            error={"message": str(exc)},
            duration_ms=elapsed,
        )
        if state.retry_count < _MAX_RETRIES:
            state.retry_count += 1
        else:
            state.blocked = True
    return state


async def tool_router(state: AgentState) -> AgentState:
    if state.blocked or state.resumed:
        return state
    if state.skill_output is None or state.skill_output.result is None:
        await _emit(state, EventType.tool_started, Component.tool, Status.skipped)
        return state

    result = state.skill_output.result
    if isinstance(result, dict):
        state.tool_name = result.get("tool", "")
    if not state.tool_name:
        # Some skills produce results directly without a tool
        return state

    state.tool_input = ToolInput(
        parameters=state.parameters,
        context={
            "skill_output": state.skill_output.result,
            **state.modifications,
        },
    )
    await _emit(
        state,
        EventType.tool_started,
        Component.tool,
        Status.running,
        metadata={"tool": state.tool_name},
    )
    return state


async def before_tool_hooks(state: AgentState) -> AgentState:
    if state.blocked or state.resumed or not state.tool_name:
        return state
    hm = state.hook_manager
    if hm is None:
        return state

    await _emit(state, EventType.hook_started, Component.hook, Status.running)
    start = time.monotonic()
    result = await hm.run_pipeline(
        LifecycleEvent.before_tool,
        {"tool_name": state.tool_name, "tool_inputs": state.tool_input},
    )
    elapsed = int((time.monotonic() - start) * 1000)
    state.hook_results.append(result)
    await _emit(
        state,
        EventType.hook_completed,
        Component.hook,
        Status.completed if result.action != HookAction.BLOCK else Status.blocked,
        output={"action": result.action.value},
        duration_ms=elapsed,
    )

    if result.action == HookAction.BLOCK:
        state.blocked = True
        state.error = result.reason
    elif result.action == HookAction.APPROVAL_REQUIRED:
        state.approval_required = True
        await _emit(
            state,
            EventType.approval_required,
            Component.runtime,
            Status.waiting_approval,
            output={"tool_name": state.tool_name},
        )
    elif result.action == HookAction.RETRY:
        state.retry_count += 1
    return state


async def permission_check(state: AgentState) -> AgentState:
    if state.blocked or not state.tool_name:
        return state
    if state.tool_executor is None:
        state.error = "No tool executor available"
        await _emit(state, EventType.error, Component.tool, Status.failed)
        state.blocked = True
        return state

    tool = state.tool_executor.registry.get(state.tool_name)
    if tool is None:
        state.blocked = True
        state.error = f"Tool '{state.tool_name}' not found"
        return state

    perm = tool.metadata.permission
    from app.tools.base import ToolPermission

    if perm == ToolPermission.DENY:
        state.blocked = True
        state.error = f"Tool '{state.tool_name}' is denied"
    return state


async def approval_check(state: AgentState) -> AgentState:
    if state.blocked or not state.tool_name:
        return state
    if not state.approval_required:
        return state

    if state.approval_granted:
        await _emit(state, EventType.approval_granted, Component.runtime, Status.approved)
    return state


async def pause_for_approval(state: AgentState) -> AgentState:
    if not state.approval_required or state.approval_granted:
        return state

    # Build a serializable snapshot of the current AgentState
    snapshot = {
        "run_id": state.run_id,
        "trace_id": state.trace_id,
        "task": state.task,
        "parameters": state.parameters,
        "request_payload": state.request_payload,
        "skill_selection": {
            "skill_id": state.skill_selection.skill_id,
            "skill_name": state.skill_selection.skill_name,
            "confidence": state.skill_selection.confidence,
            "reasoning": state.skill_selection.reasoning,
        } if state.skill_selection else None,
        "skill_output": {
            "result": state.skill_output.result,
            "summary": state.skill_output.summary,
            "metadata": state.skill_output.metadata,
        } if state.skill_output else None,
        "tool_name": state.tool_name,
        "tool_input": {
            "parameters": state.tool_input.parameters,
            "context": state.tool_input.context,
        } if state.tool_input else None,
        "modifications": state.modifications,
        "retry_count": state.retry_count,
        "approval_required": state.approval_required,
    }

    es = state.event_service
    if es is not None:
        approval_id = str(uuid.uuid4())
        state.approval_id = approval_id
        skill_name = state.skill_selection.skill_name if state.skill_selection else ""
        try:
            await es.create_approval(
                approval_id=approval_id,
                run_id=state.run_id,
                skill_name=skill_name,
                input_summary=f"Tool '{state.tool_name}' requires approval",
                asker="HumanApprovalHook",
                reason=f"High-risk tool '{state.tool_name}' needs human approval",
                state_snapshot=json.dumps(snapshot, default=str),
            )
            await es.update_run(state.run_id, "waiting_approval")
        except Exception:
            logger.exception("Failed to persist approval request for run %s", state.run_id)

    await _emit(
        state,
        EventType.approval_required,
        Component.runtime,
        Status.waiting_approval,
        output={"tool_name": state.tool_name, "approval_id": state.approval_id},
    )
    return state


async def execute_tool(state: AgentState) -> AgentState:
    if state.blocked or not state.tool_name:
        return state
    if state.approval_required and not state.approval_granted:
        return state

    if state.tool_executor is None:
        state.error = "No tool executor available"
        state.blocked = True
        return state

    start = time.monotonic()
    output = await state.tool_executor.execute(state.tool_name, state.tool_input)
    elapsed = int((time.monotonic() - start) * 1000)
    state.tool_output = output

    if output.success:
        await _emit(
            state,
            EventType.tool_completed,
            Component.tool,
            Status.completed,
            output={"result": output.result},
            duration_ms=elapsed,
        )
    else:
        await _emit(
            state,
            EventType.error,
            Component.tool,
            Status.failed,
            error={"message": output.error},
            duration_ms=elapsed,
        )
        if state.retry_count < _MAX_RETRIES:
            state.retry_count += 1
        else:
            state.blocked = True
            state.error = output.error
    return state


async def after_tool_hooks(state: AgentState) -> AgentState:
    if state.blocked or not state.tool_name:
        return state
    hm = state.hook_manager
    if hm is None:
        return state

    result = await hm.run_pipeline(
        LifecycleEvent.after_tool,
        {
            "tool_name": state.tool_name,
            "tool_output": state.tool_output,
        },
    )
    state.hook_results.append(result)
    if result.action == HookAction.BLOCK:
        state.blocked = True
        state.error = result.reason
    return state


async def validate_result(state: AgentState) -> AgentState:
    if state.blocked:
        return state

    if state.hook_manager:
        result = await state.hook_manager.run_pipeline(
            LifecycleEvent.after_response,
            {"output": state.tool_output.result if state.tool_output else state.skill_output},
        )
        state.hook_results.append(result)
        if result.action == HookAction.BLOCK:
            state.blocked = True
            state.error = result.reason
            return state

    if state.tool_output and not state.tool_output.success and state.retry_count < _MAX_RETRIES:
        state.retry_count += 1
        await _emit(state, EventType.retry_started, Component.runtime, Status.running)
    return state


async def retry_or_continue(state: AgentState) -> AgentState:
    if state.blocked:
        return state
    return state


async def after_skill_hooks(state: AgentState) -> AgentState:
    if state.blocked:
        return state
    hm = state.hook_manager
    if hm is None:
        return state

    result = await hm.run_pipeline(
        LifecycleEvent.after_skill,
        {
            "skill_id": state.skill_selection.skill_id if state.skill_selection else "",
            "output": state.skill_output,
        },
    )
    state.hook_results.append(result)
    return state


async def generate_response(state: AgentState) -> AgentState:
    if state.blocked:
        state.response = {"error": state.error, "run_id": state.run_id}
        return state

    result_data = None
    if state.tool_output and state.tool_output.success:
        result_data = state.tool_output.result
    elif state.skill_output:
        result_data = state.skill_output.result

    state.response = {
        "run_id": state.run_id,
        "trace_id": state.trace_id,
        "task": state.task,
        "skill_used": state.skill_selection.skill_name if state.skill_selection else None,
        "result": result_data,
        "status": "completed",
        "retry_count": state.retry_count,
    }

    await _emit(
        state,
        EventType.response_generated,
        Component.agent,
        Status.completed,
        output=state.response,
    )
    return state


async def before_response_hooks(state: AgentState) -> AgentState:
    if state.hook_manager is None:
        return state
    result = await state.hook_manager.run_pipeline(
        LifecycleEvent.before_response,
        {"response": state.response},
    )
    state.hook_results.append(result)
    if result.action == HookAction.MODIFY and result.modifications:
        state.response.update(result.modifications)
    return state


async def after_request_hooks(state: AgentState) -> AgentState:
    if state.hook_manager is None:
        return state
    await state.hook_manager.run_pipeline(
        LifecycleEvent.after_request,
        {"run_id": state.run_id, "response": state.response},
    )
    return state


async def persist_run(state: AgentState) -> AgentState:
    state.completed = True
    status = Status.failed if state.error else Status.completed
    await _emit(
        state,
        EventType.run_completed,
        Component.runtime,
        status,
        output={"run_id": state.run_id, "error": state.error},
    )
    return state
