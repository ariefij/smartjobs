from smartjobs.config import Settings


def test_settings_uses_cloud_run_port_env(monkeypatch):
    monkeypatch.delenv('APP_PORT', raising=False)
    monkeypatch.setenv('PORT', '8080')
    settings = Settings()
    assert settings.app_port == 8080


def test_app_port_overrides_port(monkeypatch):
    monkeypatch.setenv('APP_PORT', '8000')
    monkeypatch.setenv('PORT', '8080')
    settings = Settings()
    assert settings.app_port == 8000


def test_require_qdrant_url_rejects_placeholder(monkeypatch):
    monkeypatch.setenv('QDRANT_URL', 'https://your-qdrant-host')
    settings = Settings()
    try:
        settings.require_qdrant_url()
    except RuntimeError as exc:
        assert 'placeholder' in str(exc).lower()
    else:
        raise AssertionError('Expected RuntimeError for placeholder QDRANT_URL')


def test_require_qdrant_url_accepts_external_url(monkeypatch):
    monkeypatch.setenv('QDRANT_URL', 'https://demo-example.gcp.cloud.qdrant.io')
    settings = Settings()
    assert settings.require_qdrant_url() == 'https://demo-example.gcp.cloud.qdrant.io'
