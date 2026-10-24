import importlib
import socket
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient


KEY = "test-only-access-key"
RECORD = {"material": "测试物料", "type": "入库", "quantity": 2, "unit": "斤"}
ENDPOINTS = [
    ("GET", "/inventory", {}),
    ("POST", "/inventory", {"json": RECORD}),
    ("GET", "/stock", {"params": {"material": "测试物料", "unit": "斤"}}),
    ("POST", "/agent/query", {"json": {"message": "查询测试库存"}}),
]


@pytest.fixture
def isolated_app(monkeypatch, tmp_path):
    # Configure isolation BEFORE imports: database.py initializes on import.
    monkeypatch.setenv("DB_PATH", str(tmp_path / "inventory-test.db"))
    monkeypatch.setenv("API_ACCESS_KEY", KEY)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def reject_network(*args, **kwargs):
        raise AssertionError("Tests must not open network connections")

    # Leave socketpair available for Windows asyncio's local wakeup pipe.
    monkeypatch.setattr(socket, "create_connection", reject_network)
    import openai

    create = Mock(return_value=SimpleNamespace(output=[], output_text="模拟库存回答"))
    monkeypatch.setattr(openai, "OpenAI", Mock(return_value=SimpleNamespace(
        responses=SimpleNamespace(create=create)
    )))
    names = ("main", "agent", "inventory_service", "database")
    previous = {name: sys.modules.pop(name) for name in names if name in sys.modules}
    try:
        main = importlib.import_module("main")
        database = importlib.import_module("database")
        yield main, database, create
    finally:
        for name in names:
            sys.modules.pop(name, None)
        sys.modules.update(previous)


@pytest.mark.parametrize("method,path,kwargs", ENDPOINTS)
@pytest.mark.parametrize("supplied_key", [None, "", "wrong-key"])
def test_invalid_credentials_block_business(isolated_app, method, path, kwargs, supplied_key):
    main, database, create = isolated_app
    headers = {} if supplied_key is None else {"X-API-Key": supplied_key}
    with TestClient(main.app) as client:
        response = client.request(method, path, headers=headers, **kwargs)
    assert response.status_code == 401
    assert database.fetch_records() == []
    create.assert_not_called()


@pytest.mark.parametrize("method,path,kwargs", ENDPOINTS)
@pytest.mark.parametrize("configured_key", [None, "", "   "])
def test_missing_server_key_fails_closed(isolated_app, monkeypatch, method, path, kwargs, configured_key):
    main, database, create = isolated_app
    if configured_key is None:
        monkeypatch.delenv("API_ACCESS_KEY")
    else:
        monkeypatch.setenv("API_ACCESS_KEY", configured_key)
    with TestClient(main.app) as client:
        response = client.request(method, path, headers={"X-API-Key": KEY}, **kwargs)
    assert response.status_code == 503
    assert database.fetch_records() == []
    create.assert_not_called()


def test_valid_key_allows_inventory_and_agent(isolated_app):
    main, database, create = isolated_app
    with TestClient(main.app, headers={"X-API-Key": KEY}) as client:
        response = client.post("/inventory", json=RECORD)
        assert response.status_code == 200
        assert response.json()["data"] == RECORD
        response = client.get("/inventory")
        assert response.status_code == 200
        assert response.json()["current_stock"] == {"测试物料_斤": 2}
        response = client.get("/stock", params={"material": "测试物料", "unit": "斤"})
        assert response.status_code == 200
        assert response.json()["current_stock"] == 2
        response = client.post("/agent/query", json={"message": "查询测试库存"})
        assert response.status_code == 200
        assert response.json()["answer"] == "模拟库存回答"
    assert len(database.fetch_records()) == 1
    assert create.call_count == 1


@pytest.mark.parametrize("environment,expected", [(None, 404), ("production", 404), ("typo", 404), ("development", 200)])
def test_documentation_visibility(isolated_app, monkeypatch, environment, expected):
    main, _, _ = isolated_app
    if environment is not None:
        monkeypatch.setenv("APP_ENV", environment)
    importlib.reload(main)
    with TestClient(main.app) as client:
        for path in ("/docs", "/redoc", "/openapi.json"):
            assert client.get(path).status_code == expected
        # Enabling development docs must never disable business authentication.
        assert client.get("/inventory").status_code == 401


def test_health_check_remains_public(isolated_app, monkeypatch):
    main, _, create = isolated_app
    monkeypatch.delenv("API_ACCESS_KEY")
    with TestClient(main.app) as client:
        assert client.get("/").status_code == 200
    create.assert_not_called()
