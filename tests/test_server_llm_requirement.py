from fastapi.testclient import TestClient

from smartjobs.server import app


def test_obrolan_returns_503_when_llm_not_configured():
    client = TestClient(app)
    response = client.post('/obrolan', json={'pertanyaan': 'data analyst jakarta', 'batas': 2})
    assert response.status_code == 503
    payload = response.json()
    assert payload['error_type'] == 'llm_required'
