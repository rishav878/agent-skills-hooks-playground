import json
import time
import asyncio
from typing import Any

import streamlit as st
import api

try:
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False


def _run_async(coro: Any) -> Any:
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    if loop.is_running():
        return coro
    return loop.run_until_complete(coro)


def show() -> None:
    st.title("Playground")
    st.markdown("Run an agent and watch its execution in real time.")

    task = st.text_area(
        "Task",
        placeholder="e.g. research artificial intelligence safety",
        height=100,
    )

    col1, col2 = st.columns([1, 5])
    run_clicked = col1.button("Run Agent", type="primary", use_container_width=True)
    clear_clicked = col2.button("Clear", use_container_width=True)

    if clear_clicked:
        for key in list(st.session_state.keys()):
            if key.startswith("pg_"):
                del st.session_state[key]
        st.rerun()

    if run_clicked and not task.strip():
        st.warning("Please enter a task.")
        return

    if run_clicked:
        st.session_state.pg_task = task
        st.session_state.pg_running = True
        st.session_state.pg_run_id = None
        st.session_state.pg_result = None
        st.session_state.pg_events = []
        st.session_state.pg_error = None
        st.rerun()

    if not st.session_state.get("pg_running"):
        return

    task = st.session_state.pg_task
    status_placeholder = st.empty()

    if st.session_state.pg_run_id is None:
        with status_placeholder.container():
            st.info("Sending request to agent runtime...")
        try:
            result = api.run_agent(task)
            st.session_state.pg_run_id = result.get("run_id")
            st.session_state.pg_result = result
            if result.get("events"):
                st.session_state.pg_events = result["events"]
            st.session_state.pg_running = False
        except Exception as exc:
            st.session_state.pg_error = str(exc)
            st.session_state.pg_running = False
            status_placeholder.error(f"Run failed: {exc}")
            return

    run_id = st.session_state.pg_run_id
    result = st.session_state.pg_result

    if run_id is None:
        return

    # Display results
    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    col1.metric("Run ID", run_id[:8] + "...", help=run_id)
    col2.metric("Status", result.get("status", "unknown"))
    col3.metric("Skill", result.get("skill_used", "none") or "none")

    if result.get("retry_count", 0) > 0:
        st.warning(f"Retries: {result['retry_count']}")

    if result.get("error"):
        st.error(f"Error: {result['error']}")

    # Approval dialog for human-in-the-loop
    if result.get("status") == "waiting_approval":
        st.markdown("---")
        st.warning("⏳ **Approval Required** — A high-risk tool is waiting for your decision.")

        col_a, col_b, _ = st.columns([1, 1, 4])
        if col_a.button("✅ Approve", type="primary", use_container_width=True):
            try:
                approve_result = api.approve_run(run_id)
                st.session_state.pg_result = approve_result
                st.rerun()
            except Exception as exc:
                st.error(f"Approval failed: {exc}")

        if col_b.button("❌ Deny", use_container_width=True):
            try:
                cancel_result = api.cancel_run(run_id)
                st.session_state.pg_result = cancel_result
                st.rerun()
            except Exception as exc:
                st.error(f"Cancel failed: {exc}")

    # Execution Timeline
    st.markdown("---")
    st.subheader("Execution Timeline")

    events = st.session_state.pg_events
    if events:
        event_types_seen = set()
        for i, ev in enumerate(events):
            et = ev.get("event_type", "?")
            comp = ev.get("component", "?")
            status = ev.get("status", "?")
            ts = ev.get("timestamp", "")[11:19] if ev.get("timestamp") else ""

            icon = {
                "running": "",
                "completed": "✅",
                "failed": "❌",
                "blocked": "🚫",
                "skipped": "⏭️",
                "waiting_approval": "⏳",
                "approved": "👍",
            }.get(status, "")

            is_new = et not in event_types_seen
            event_types_seen.add(et)

            prefix = "**→** " if is_new else "  "
            st.markdown(f"{prefix}{icon} `{ts}` **{et}** — {comp} ({status})")

        st.markdown("---")
        st.subheader("Event Details")

        selected_idx = st.selectbox(
            "Select event to inspect",
            options=range(len(events)),
            format_func=lambda i: f"{events[i].get('event_type', '?')} — {events[i].get('status', '?')}",
        )
        if selected_idx is not None:
            ev = events[selected_idx]
            with st.expander("Full Event", expanded=True):
                st.json(ev)
    else:
        st.info("No events captured.")

    # Final Response
    st.markdown("---")
    st.subheader("Response")

    resp_result = result.get("result")
    if resp_result:
        if isinstance(resp_result, str):
            st.text(resp_result)
        else:
            st.json(resp_result)
    else:
        st.info("No result returned.")

    # Trace ID
    trace_id = result.get("trace_id")
    if trace_id:
        st.caption(f"Trace ID: `{trace_id}`")
