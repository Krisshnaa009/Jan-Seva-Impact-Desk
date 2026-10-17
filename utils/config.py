"""
Configuration loader for JanSeva Impact Desk.
Reads settings from environment variables or Streamlit secrets.
Never exposes or logs API keys.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional




@dataclass
class AppConfig:
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-3.8-flash"
    app_name: str = "JanSeva Impact Desk"
    app_version: str = "1.0.0"
    default_currency: str = "INR"
    max_upload_size_mb: int = 10
    ai_timeout_seconds: int = 30
    is_demo_mode: bool = field(init=False)

    def __post_init__(self):
        self.is_demo_mode = not bool(self.gemini_api_key)


def get_config() -> AppConfig:
    """
    Load configuration in priority order:
    1. Environment variables
    2. Streamlit secrets (if running inside Streamlit)
    3. Defaults (demo/mock mode)
    """
    api_key: Optional[str] = os.environ.get("GEMINI_API_KEY") or None

    # Try Streamlit secrets (won't fail if not in Streamlit context)
    if not api_key:
        try:
            import streamlit as st  # noqa: PLC0415

            api_key = st.secrets.get("GEMINI_API_KEY") or None
        except Exception:
            pass

    model_name = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")

    return AppConfig(
        gemini_api_key=api_key,
        gemini_model=model_name,
    )
