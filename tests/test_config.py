import pytest
from webpilot.config import get_settings

@pytest.fixture
def config():
    return get_settings()


def test_defaults(monkeypatch, config):
    assert config.webpilot_model == "claude-sonnet-4-6"
    assert config.webpilot_max_seconds == 300
    assert config.webpilot_max_tool_calls == 40
    assert config.webpilot_max_pages == 10
    assert config.webpilot_max_input_tokens == 200000
    assert config.webpilot_max_output_tokens == 20000
    assert config.webpilot_headless is True


