import os
from fastapi.testclient import TestClient


def test_api_endpoints_smoke():
    os.environ.setdefault("ENV", "development")
    from main import app
    client = TestClient(app)

    assert client.get('/health').status_code == 200
    assert isinstance(client.get('/matches').json(), list)
    assert isinstance(client.get('/predictions').json(), list)
    assert isinstance(client.get('/dashboard/summary').json(), dict)


def test_production_requires_database_url(monkeypatch):
    monkeypatch.setenv('ENV', 'production')
    monkeypatch.delenv('DATABASE_URL', raising=False)
    from main import lifespan
    import asyncio

    async def _run():
        try:
            async with lifespan(None):
                pass
        except RuntimeError as exc:
            return str(exc)
        return ''

    msg = asyncio.run(_run())
    assert 'DATABASE_URL is required in production' in msg
