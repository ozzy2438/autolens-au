"""Streamlit runtime bootstrap shared by every dashboard entry script."""

import os


def bootstrap() -> None:
    """Expose root-level Streamlit secrets as environment variables.

    ``config.settings`` reads configuration from the environment at import time.
    Streamlit Cloud stores deployment configuration in ``st.secrets``; bridging
    root-level scalar secrets into the environment before the first
    ``config.settings`` import makes the same code work locally (``.env``/shell)
    and on Streamlit Cloud without platform-specific branches. Existing
    environment variables always win.
    """
    try:
        import streamlit as st

        secrets = dict(st.secrets)
    except Exception:
        return
    for key, value in secrets.items():
        if isinstance(value, (str, int, float, bool)):
            os.environ.setdefault(key, str(value))
