import streamlit as st

import api


def show() -> None:
    st.title("Skills")
    st.markdown("Skills represent what the agent **can do**.")

    try:
        data = api.list_skills()
    except Exception as exc:
        st.error(f"Failed to load skills: {exc}")
        return

    skills = data.get("skills", [])
    st.write(f"**{data.get('total', len(skills))}** skills registered.")

    for s in skills:
        m = s.get("metadata", {})
        skill_id = s.get("id", "")
        with st.expander(
            f"{m.get('name', skill_id)} v{m.get('version', '?')} "
            f"{'✅' if m.get('enabled', True) else '❌'}",
            expanded=False,
        ):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.write("**Description:**")
                st.write(m.get("description", "No description"))

                if m.get("input_schema"):
                    st.write("**Input Schema:**")
                    st.json(m["input_schema"])

                if m.get("output_schema"):
                    st.write("**Output Schema:**")
                    st.json(m["output_schema"])

            with col2:
                st.write(f"**ID:** `{skill_id}`")
                st.write(f"**Version:** {m.get('version', '?')}")
                st.write(f"**Enabled:** {m.get('enabled', True)}")

                allowed = m.get("allowed_tools")
                if allowed:
                    st.write(f"**Allowed Tools:** {', '.join(allowed)}")
