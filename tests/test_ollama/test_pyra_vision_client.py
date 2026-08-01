from src.pyra_vision.client import PyraVisionConfig


def test_pyra_vision_config_from_env(monkeypatch):
    monkeypatch.setenv("ZIGGY_VISION_BASE_URL", "http://localhost:9931/")
    monkeypatch.setenv("ZIGGY_VISION_TIMEOUT", "45")
    monkeypatch.setenv("ZIGGY_VISION_MAX_RETRIES", "0")
    monkeypatch.setenv("ZIGGY_VISION_MAX_TOKENS", "96")
    monkeypatch.setenv("ZIGGY_VISION_BACKEND", "ollama")
    monkeypatch.setenv("ZIGGY_VISION_MODEL", "gemma4:12b-it-qat")

    config = PyraVisionConfig.from_env()

    assert config.base_url == "http://localhost:9931"
    assert config.timeout == 45.0
    assert config.max_retries == 0
    assert config.max_tokens == 96
    assert config.backend == "ollama"
    assert config.model == "gemma4:12b-it-qat"


def test_pyra_vision_config_from_env_keeps_defaults(monkeypatch):
    for name in (
        "PYRA_VISION_BASE_URL",
        "PYRA_VISION_TIMEOUT",
        "PYRA_VISION_MAX_RETRIES",
        "PYRA_VISION_MAX_TOKENS",
        "PYRA_VISION_BACKEND",
        "PYRA_VISION_MODEL",
        "ZIGGY_VISION_BASE_URL",
        "ZIGGY_VISION_TIMEOUT",
        "ZIGGY_VISION_MAX_RETRIES",
        "ZIGGY_VISION_MAX_TOKENS",
        "ZIGGY_VISION_BACKEND",
        "ZIGGY_VISION_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)

    config = PyraVisionConfig.from_env()

    assert config.base_url == "http://localhost:9920"
    assert config.backend == "finetuned"
    assert config.model is None


def test_pyra_vision_config_from_env_keeps_legacy_pyra_fallback(monkeypatch):
    monkeypatch.delenv("ZIGGY_VISION_BASE_URL", raising=False)
    monkeypatch.setenv("PYRA_VISION_BASE_URL", "http://localhost:9920/")

    config = PyraVisionConfig.from_env()

    assert config.base_url == "http://localhost:9920"
