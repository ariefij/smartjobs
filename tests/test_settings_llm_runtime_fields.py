from smartjobs.config import Settings


def test_settings_has_llm_runtime_fields():
    settings = Settings()
    assert settings.llm_request_timeout_seconds == 60.0
    assert settings.llm_max_retries == 3
    assert settings.llm_retry_backoff_seconds == 2.0
