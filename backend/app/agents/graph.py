import logging
from typing import Literal

from langgraph.graph import END, StateGraph

from app.agents.nodes import (
    after_request_hooks,
    after_skill_hooks,
    after_tool_hooks,
    approval_check,
    before_request_hooks,
    before_response_hooks,
    before_skill_hooks,
    before_tool_hooks,
    classify_request,
    execute_skill,
    execute_tool,
    generate_response,
    initialize_run,
    pause_for_approval,
    permission_check,
    persist_run,
    retry_or_continue,
    tool_router,
    validate_result,
)
from app.agents.state import AgentState

logger = logging.getLogger(__name__)


def _needs_tool(state: AgentState) -> Literal["before_tool_hooks", "after_skill_hooks"]:
    if state.blocked or not state.tool_name:
        return "after_skill_hooks"
    return "before_tool_hooks"


def _check_approval(state: AgentState) -> Literal["execute_tool", "waiting"]:
    if state.approval_required and not state.approval_granted:
        return "waiting"
    return "execute_tool"


def _should_retry(state: AgentState) -> Literal["before_skill_hooks", "persist_run"]:
    if state.error and state.retry_count > 0 and not state.blocked:
        return "before_skill_hooks"
    return "persist_run"


def _validate_retry(state: AgentState) -> Literal["retry_or_continue", "persist_run"]:
    return "persist_run"


def build_graph() -> StateGraph:
    workflow = StateGraph(AgentState)

    workflow.add_node("initialize_run", initialize_run)
    workflow.add_node("before_request_hooks", before_request_hooks)
    workflow.add_node("classify_request", classify_request)
    workflow.add_node("before_skill_hooks", before_skill_hooks)
    workflow.add_node("execute_skill", execute_skill)
    workflow.add_node("tool_router", tool_router)
    workflow.add_node("before_tool_hooks", before_tool_hooks)
    workflow.add_node("permission_check", permission_check)
    workflow.add_node("approval_check", approval_check)
    workflow.add_node("pause_for_approval", pause_for_approval)
    workflow.add_node("execute_tool", execute_tool)
    workflow.add_node("after_tool_hooks", after_tool_hooks)
    workflow.add_node("validate_result", validate_result)
    workflow.add_node("retry_or_continue", retry_or_continue)
    workflow.add_node("after_skill_hooks", after_skill_hooks)
    workflow.add_node("generate_response", generate_response)
    workflow.add_node("before_response_hooks", before_response_hooks)
    workflow.add_node("after_request_hooks", after_request_hooks)
    workflow.add_node("persist_run", persist_run)

    workflow.set_entry_point("initialize_run")

    workflow.add_edge("initialize_run", "before_request_hooks")
    workflow.add_edge("before_request_hooks", "classify_request")
    workflow.add_edge("classify_request", "before_skill_hooks")
    workflow.add_edge("before_skill_hooks", "execute_skill")
    workflow.add_edge("execute_skill", "tool_router")

    workflow.add_conditional_edges(
        "tool_router",
        _needs_tool,
        {
            "before_tool_hooks": "before_tool_hooks",
            "after_skill_hooks": "after_skill_hooks",
        },
    )

    workflow.add_edge("before_tool_hooks", "permission_check")
    workflow.add_edge("permission_check", "approval_check")

    workflow.add_conditional_edges(
        "approval_check",
        _check_approval,
        {
            "execute_tool": "execute_tool",
            "waiting": "pause_for_approval",
        },
    )

    workflow.add_edge("pause_for_approval", END)
    workflow.add_edge("execute_tool", "after_tool_hooks")
    workflow.add_edge("after_tool_hooks", "validate_result")
    workflow.add_edge("validate_result", "retry_or_continue")
    workflow.add_edge("retry_or_continue", "after_skill_hooks")
    workflow.add_edge("after_skill_hooks", "generate_response")
    workflow.add_edge("generate_response", "before_response_hooks")
    workflow.add_edge("before_response_hooks", "after_request_hooks")
    workflow.add_edge("after_request_hooks", "persist_run")
    workflow.add_edge("persist_run", END)

    return workflow
