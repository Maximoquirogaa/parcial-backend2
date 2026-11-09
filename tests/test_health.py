import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from app.modules.health.router import router as health_router


@pytest.fixture
def test_app():
    app = FastAPI()
    app.include_router(health_router)
    return app


@pytest.mark.asyncio
async def test_health_live_returns_200_without_database(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        res = await client.get("/health/live")
        assert res.status_code == 200
        assert res.json() == {"estado": "vivo"}


@pytest.mark.asyncio
async def test_health_ready_returns_503_when_db_fails(test_app):
    class FailingSession:
        async def execute(self, stmt):
            raise ConnectionRefusedError("Database unreachable")

    async def override_failing_session():
        yield FailingSession()

    from app.core.database import get_session
    test_app.dependency_overrides[get_session] = override_failing_session

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        res = await client.get("/health/ready")
        assert res.status_code == 503
        data = res.json()
        assert "detail" in data
        assert data["detail"]["estado"] == "error"


@pytest.mark.asyncio
async def test_health_ready_returns_200_when_db_is_healthy(test_app):
    class HealthyResult:
        def scalar(self):
            return 1

    class HealthySession:
        async def execute(self, stmt):
            return HealthyResult()

    async def override_healthy_session():
        yield HealthySession()

    from app.core.database import get_session
    test_app.dependency_overrides[get_session] = override_healthy_session

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        res = await client.get("/health/ready")
        assert res.status_code == 200
        data = res.json()
        assert data["estado"] == "listo"
        assert data["base_de_datos"] == "conectada"
