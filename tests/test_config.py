import pytest
from pydantic import ValidationError
from app.core.config import Settings


def test_settings_missing_secret_key_or_password_raises_validation_error(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
    monkeypatch.delenv("POSTGRES_USER", raising=False)
    monkeypatch.delenv("POSTGRES_DB", raising=False)

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)
    
    errors = str(exc_info.value)
    assert "POSTGRES_USER" in errors
    assert "POSTGRES_PASSWORD" in errors
    assert "POSTGRES_DB" in errors
    assert "SECRET_KEY" in errors


def test_settings_computes_asyncpg_database_url(monkeypatch):
    monkeypatch.setenv("POSTGRES_USER", "myuser")
    monkeypatch.setenv("POSTGRES_PASSWORD", "mypassword")
    monkeypatch.setenv("POSTGRES_DB", "mydb")
    monkeypatch.setenv("POSTGRES_HOST", "dbhost")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("SECRET_KEY", "super_secret_test_key_1234567890")

    settings = Settings(_env_file=None)
    assert settings.database_url == "postgresql+asyncpg://myuser:mypassword@dbhost:5432/mydb"
    assert settings.POSTGRES_HOST == "dbhost"
    assert settings.POOL_SIZE == 5
    assert settings.BCRYPT_COST == 12


def test_settings_reflects_custom_host_and_port(monkeypatch):
    monkeypatch.setenv("POSTGRES_USER", "admin")
    monkeypatch.setenv("POSTGRES_PASSWORD", "admin123")
    monkeypatch.setenv("POSTGRES_DB", "libreria")
    monkeypatch.setenv("POSTGRES_HOST", "192.168.1.100")
    monkeypatch.setenv("POSTGRES_PORT", "5433")
    monkeypatch.setenv("SECRET_KEY", "another_secret_key_987654321")
    monkeypatch.setenv("POOL_SIZE", "10")
    monkeypatch.setenv("SQL_ECHO", "true")

    settings = Settings(_env_file=None)
    assert settings.database_url == "postgresql+asyncpg://admin:admin123@192.168.1.100:5433/libreria"
    assert settings.POOL_SIZE == 10
    assert settings.SQL_ECHO is True
