import streamlit as st

import api


def show() -> None:
    st.title("Dashboard")
    st.markdown("Agent Skills & Hooks Playground — real-time agent execution visualization.")

    try:
        info = api.health()
        st.success(f"Backend status: **{info.get('status', 'unknown')}** — v{info.get('version', '?')}")
    except Exception as exc:
        st.error(f"Cannot reach backend: {exc}")
        return

    col1, col2, col3, col4 = st.columns(4)

    try:
        skills_data = api.list_skills()
        col1.metric("Skills", skills_data.get("total", 0))
    except Exception:
        col1.metric("Skills", "?")

    try:
        hooks_data = api.list_hooks()
        col2.metric("Hooks", hooks_data.get("total", 0))
    except Exception:
        col2.metric("Hooks", "?")

    try:
        tools_data = api.list_tools()
        col3.metric("Tools", tools_data.get("total", 0))
    except Exception:
        col3.metric("Tools", "?")

    try:
        runs_data = api.list_runs(limit=5)
        col4.metric("Recent Runs", runs_data.get("total", 0))
    except Exception:
        col4.metric("Recent Runs", "?")

    st.markdown("---")

    st.subheader("Skills")
    try:
        skills = skills_data.get("skills", [])
        for s in skills:
            m = s.get("metadata", {})
            with st.expander(f"{m.get('name', '?')} v{m.get('version', '?')}"):
                st.write(m.get("description", "No description"))
                if m.get("allowed_tools"):
                    st.write(f"**Allowed tools:** {', '.join(m['allowed_tools'])}")
                st.code(s.get("id", ""), language="text")
    except Exception:
        st.warning("Could not load skills")

    st.subheader("Hooks")
    try:
        hooks = hooks_data.get("hooks", [])
        event_groups: dict[str, list[dict]] = {}
        for h in hooks:
            m = h.get("metadata", {})
            ev = m.get("lifecycle_event", "unknown")
            event_groups.setdefault(ev, []).append(h)
        for event, hks in sorted(event_groups.items()):
            with st.expander(f"{event} ({len(hks)})"):
                for h in hks:
                    m = h.get("metadata", {})
                    st.write(f"**{m.get('name')}** (priority {m.get('priority')}, enabled: {m.get('enabled')})")
                    st.caption(m.get("description", ""))
    except Exception:
        st.warning("Could not load hooks")

    st.subheader("Recent Runs")
    try:
        runs = runs_data.get("runs", [])
        if runs:
            for r in runs:
                st.write(f"- `{r['id'][:8]}...` **{r['status']}** — {r.get('selected_skill', '?')} — {r['created_at']}")
        else:
            st.info("No runs yet. Go to Playground to run an agent.")
    except Exception:
        st.warning("Could not load runs")
