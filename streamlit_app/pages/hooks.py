import streamlit as st

import api


def show() -> None:
    st.title("Hooks")
    st.markdown("Hooks define **when** lifecycle logic executes.")

    try:
        data = api.list_hooks()
    except Exception as exc:
        st.error(f"Failed to load hooks: {exc}")
        return

    hooks = data.get("hooks", [])
    st.write(f"**{data.get('total', len(hooks))}** hooks registered.")

    event_groups: dict[str, list[dict]] = {}
    for h in hooks:
        m = h.get("metadata", {})
        ev = m.get("lifecycle_event", "unknown")
        event_groups.setdefault(ev, []).append(h)

    for event_name in sorted(event_groups.keys()):
        hks = event_groups[event_name]
        with st.expander(f"{event_name} ({len(hks)} hooks)", expanded=True):
            for h in sorted(hks, key=lambda x: x.get("metadata", {}).get("priority", 0)):
                m = h.get("metadata", {})
                h_id = h.get("hook_id", "")

                cols = st.columns([3, 1, 1, 1])
                cols[0].write(f"**{m.get('name', h_id)}**")
                cols[0].caption(m.get("description", ""))
                cols[1].write(f"Priority: {m.get('priority', 0)}")
                cols[2].write(f"Enabled: {'✅' if m.get('enabled', True) else '❌'}")

                more = m.get("metadata", {})
                if more:
                    cols[3].write(f"Metadata: {len(more)} keys")

                st.divider()
