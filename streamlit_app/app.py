import streamlit as st

from api import API_BASE, health, set_api_base

st.set_page_config(
    page_title="Agent Skills & Hooks Playground",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _check_health() -> bool:
    try:
        info = health()
        return info.get("status") == "ok"
    except Exception:
        return False


if "api_base" not in st.session_state:
    st.session_state.api_base = API_BASE


st.sidebar.title("Agent Playground")
st.sidebar.markdown("---")

base_url = st.sidebar.text_input(
    "API Base URL",
    value=st.session_state.api_base.replace("/api/v1", ""),
    key="api_url_input",
    on_change=lambda: set_api_base(st.session_state.api_url_input),
)
set_api_base(base_url)

status_ok = _check_health()
st.sidebar.markdown(
    f"**Backend:** {'✅ Connected' if status_ok else '❌ Disconnected'}"
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Navigation")

page = st.sidebar.radio(
    "Go to",
    ["Dashboard", "Playground", "Skills", "Hooks", "Run History"],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")
st.sidebar.caption("v0.1.0 — Agent Skills & Hooks")

if page == "Dashboard":
    import pages.dashboard as dashboard
    dashboard.show()
elif page == "Playground":
    import pages.playground as playground
    playground.show()
elif page == "Skills":
    import pages.skills as skills
    skills.show()
elif page == "Hooks":
    import pages.hooks as hooks
    hooks.show()
elif page == "Run History":
    import pages.run_history as run_history
    run_history.show()
