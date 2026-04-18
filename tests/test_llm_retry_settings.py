from smartjobs.config import Settings


def test_llm_retry_and_timeout_settings_from_env(monkeypatch):
    monkeypatch.setenv("LLM_REQUEST_TIMEOUT_SECONDS", "75")
    monkeypatch.setenv("LLM_MAX_RETRIES", "4")
    monkeypatch.setenv("LLM_RETRY_BACKOFF_SECONDS", "1.5")
    settings = Settings()
    assert settings.llm_request_timeout_seconds == 75
    assert settings.llm_max_retries == 4
    assert settings.llm_retry_backoff_seconds == 1.5
