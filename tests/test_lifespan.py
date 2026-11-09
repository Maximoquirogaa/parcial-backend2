import pytest
from fastapi import FastAPI
from app.main import lifespan


@pytest.mark.asyncio
async def test_lifespan_creates_and_disposes_resources(monkeypatch):
    monkeypatch.setenv("POSTGRES_USER", "testuser")
    monkeypatch.setenv("POSTGRES_PASSWORD", "testpass")
    monkeypatch.setenv("POSTGRES_DB", "testdb")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("SECRET_KEY", "test_secret_key_1234567890123456")
    monkeypatch.setenv("BCRYPT_COST", "4")  # Fast for tests

    app = FastAPI(lifespan=lifespan)
    assert not hasattr(app.state, "engine")
    assert not hasattr(app.state, "fabrica_sesiones")
    assert not hasattr(app.state, "dummy_hash")

    async with lifespan(app):
        assert hasattr(app.state, "engine")
        assert hasattr(app.state, "fabrica_sesiones")
        assert hasattr(app.state, "dummy_hash")
        assert app.state.dummy_hash.startswith("$2")
