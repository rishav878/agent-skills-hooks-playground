import streamlit as st

import api


def show() -> None:
    st.title("Run History")
    st.markdown("Browse past agent runs and inspect their execution details.")

    try:
        data = api.list_runs(limit=100)
    except Exception as exc:
        st.error(f"Failed to load runs: {exc}")
        return

    runs = data.get("runs", [])
    st.write(f"**{data.get('total', len(runs))}** runs total.")

    if not runs:
        st.info("No runs yet. Go to Playground to run an agent.")
        return

    selected_run_id = None
    for r in runs:
        cols = st.columns([2, 1, 1, 1, 1])
        cols[0].write(f"`{r['id'][:8]}...`")
        cols[1].write(r.get("status", "?"))
        cols[2].write(r.get("selected_skill", "—") or "—")
        cols[3].write(r.get("created_at", "")[11:19] if r.get("created_at") else "")
        if cols[4].button("Details", key=f"detail_{r['id']}"):
            selected_run_id = r["id"]

    if selected_run_id is None:
        return

    st.markdown("---")
    st.subheader(f"Run: `{selected_run_id}`")

    try:
        run_detail = api.get_run(selected_run_id)
    except Exception as exc:
        st.error(f"Failed to load run detail: {exc}")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Status", run_detail.get("status", "?"))
    col2.metric("Skill", run_detail.get("selected_skill", "—") or "—")
    col3.metric("Retries", run_detail.get("retry_count", 0))

    if run_detail.get("error"):
        st.error(f"Error: {run_detail['error']}")

    st.write("**Input:**")
    st.text(run_detail.get("input", ""))

    if run_detail.get("output"):
        st.write("**Output:**")
        try:
            import json
            parsed = json.loads(run_detail["output"])
            st.json(parsed)
        except (json.JSONDecodeError, TypeError):
            st.text(run_detail["output"])

    st.subheader("Events")
    try:
        events_data = api.get_run_events(selected_run_id, limit=500)
        events = events_data.get("events", [])
        if events:
            for ev in events:
                icon = {
                    "running": "",
                    "completed": "✅",
                    "failed": "❌",
                    "blocked": "🚫",
                }.get(ev.get("status", ""), "")
                ts = ev.get("timestamp", "")[11:19] if ev.get("timestamp") else ""
                dur = ev.get("duration_ms")
                dur_str = f" ({dur}ms)" if dur is not None else ""
                st.write(
                    f"{icon} `{ts}` **{ev.get('event_type', '?')}** "
                    f"— {ev.get('component', '?')} ({ev.get('status', '?')}){dur_str}"
                )

            selected_ev_idx = st.selectbox(
                "Inspect event",
                options=range(len(events)),
                format_func=lambda i: f"{events[i].get('event_type', '?')} — {events[i].get('status', '?')}",
                key="history_event_select",
            )
            if selected_ev_idx is not None:
                st.json(events[selected_ev_idx])
        else:
            st.info("No events recorded for this run.")
    except Exception as exc:
        st.warning(f"Could not load events: {exc}")
