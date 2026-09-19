import os
import sys
import pytest

os.environ["TESTING"] = "1"
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.models import Base
from app.database.connection import get_db
from app.main import app

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def mock_external_services(monkeypatch):
    memory_store = {}

    class DummyRedis:
        def get(self, key): return memory_store.get(key)
        def set(self, key, val):
            memory_store[key] = str(val)
            return True
        def setex(self, key, ttl, val):
            memory_store[key] = str(val)
            return True
        def ping(self): return True
        def lpush(self, key, val): return 1
        def ltrim(self, key, s, e): return True
        def lrange(self, key, s, e): return []
        def expire(self, key, ttl): return True
        def delete(self, *keys):
            for k in keys:
                memory_store.pop(k, None)
            return True
        def hset(self, key, field=None, val=None, mapping=None): return 1
        def hget(self, key, field): return None
        def hgetall(self, key): return {}
        def incrbyfloat(self, key, amount): return amount

    monkeypatch.setattr("app.database.connection.check_database_connection", lambda: True)
    monkeypatch.setattr("app.services.redis_service.check_redis_connection", lambda: True)
    monkeypatch.setattr("app.services.redis_service.get_redis_client", lambda *args, **kwargs: DummyRedis())
    monkeypatch.setattr("app.core.redis.get_redis_client", lambda *args, **kwargs: DummyRedis())
    monkeypatch.setattr("app.services.redis_service.push_recent_transaction", lambda m, t: None)
    monkeypatch.setattr("app.services.redis_service.increment_merchant_counter", lambda m, k, a=1.0: None)
    monkeypatch.setattr("app.services.redis_service.get_recent_transactions", lambda m, l=50: [])
    monkeypatch.setattr("app.services.redis_service.get_merchant_counter", lambda m, k: 0.0)
    monkeypatch.setattr("app.services.redis_service.get_key", lambda k: memory_store.get(k))
    monkeypatch.setattr("app.services.redis_service.set_key", lambda k, v, expire_seconds=None, **kwargs: memory_store.update({k: str(v)}) or True)
    monkeypatch.setattr("app.services.redis_service.delete_key", lambda k: memory_store.pop(k, None) is not None or True)
    monkeypatch.setattr("app.services.n8n_service.check_n8n_connection", lambda *args, **kwargs: True)
    monkeypatch.setattr("app.services.n8n_service.trigger_n8n_webhook", lambda *args, **kwargs: {"ok": True, "status_code": 200})
    monkeypatch.setattr("app.agent.runner._configure_gemini", lambda: None)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
