"""Cloud credentials must work without a local secret file."""
import importlib.util
from pathlib import Path
from unittest.mock import patch


def load_harness():
    path = Path(__file__).resolve().parents[2] / "agent/tools/harness.py"
    spec = importlib.util.spec_from_file_location("integration_harness", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cloud_provider_credential_is_scoped(tmp_path):
    harness = load_harness()
    provider = {"key_from": "qwen_key", "env_key": "OPENAI_API_KEY"}
    with patch.object(harness, "PROJECT", tmp_path), patch.dict(
        "os.environ", {"qwen_key": "test-provider-value", "OPENAI_API_KEY": "unrelated-value"}, clear=True
    ):
        env = harness.process_env("codex", home=tmp_path, provider=provider)
    assert env["OPENAI_API_KEY"] == "test-provider-value"
    assert "qwen_key" not in env
    assert "unrelated-value" not in env.values()


def test_missing_provider_credential_fails_explicitly(tmp_path):
    import pytest
    harness = load_harness()
    with patch.object(harness, "PROJECT", tmp_path), patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="environment or .env"):
            harness.process_env("codex", home=tmp_path, provider={"key_from": "qwen_key"})
