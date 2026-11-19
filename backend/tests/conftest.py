"""Test isolation for external API credentials.

The local .env may contain real provider keys. Tests must opt in explicitly so
they never make accidental network calls.
"""

import pytest

from app.core.config import settings
from app.services.gemini_client import gemini_service


@pytest.fixture(autouse=True)
def isolate_external_provider_keys(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", None)
    monkeypatch.setattr(settings, "TAVILY_API_KEY", None)
    monkeypatch.setattr(settings, "EXA_API_KEY", None)
    monkeypatch.setattr(gemini_service, "api_key", None)
    monkeypatch.setattr(gemini_service, "client", None)
