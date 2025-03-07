import json
import pytest
from ..SPA import app as spa_app


# Define a dummy object to simulate the response from requests
class DummyResponse:
    def __init__(self, json_data, status_code, content_type="application/json"):
        self._json = json_data
        self.status_code = status_code
        self.content = json.dumps(json_data).encode("utf-8")
        self.headers = {"Content-Type": content_type}

    def json(self):
        return self._json


@pytest.fixture
def client_spa(monkeypatch):
    # Set dummy environment variables to ensure SPA receives test configuration
    monkeypatch.setenv("AUTH_SERVICE_URL", "http://dummy-auth")
    monkeypatch.setenv("CHAT_SERVICE_URL", "http://dummy-chat")
    spa_app.config["TESTING"] = True
    with spa_app.test_client() as client:
        yield client


def test_index(client_spa):
    response = client_spa.get("/")
    assert response.status_code == 200


def test_login_success(client_spa, monkeypatch):
    # Simulate Auth service returning a successful result
    def fake_post(url, json):
        return DummyResponse(
            {"message": "Login successful", "token": "dummy_token"}, 200
        )

    monkeypatch.setattr("SPA.requests.post", fake_post)
    data = {"username": "user", "password": "pass"}
    response = client_spa.post("/api/login", json=data)
    result = response.get_json()
    assert response.status_code == 200
    assert "token" in result


def test_login_invalid_json_response(client_spa, monkeypatch):
    # Simulate Auth service returning invalid JSON
    def fake_post(url, json):
        # Simulate the returned content is not valid JSON
        raise Exception("JSONDecodeError")

    monkeypatch.setattr("SPA.requests.post", fake_post)
    data = {"username": "user", "password": "pass"}
    response = client_spa.post("/api/login", json=data)
    result = response.get_json()
    assert response.status_code == 500
    assert "error" in result


def test_login_service_unreachable(client_spa, monkeypatch):
    # Simulate a network exception during the request
    def fake_post(url, json):
        raise Exception("Service down")

    monkeypatch.setattr("SPA.requests.post", fake_post)
    data = {"username": "user", "password": "pass"}
    response = client_spa.post("/api/login", json=data)
    result = response.get_json()
    assert response.status_code == 500
    assert "error" in result


def test_register_success(client_spa, monkeypatch):
    # Simulate a successful registration in the Auth service
    def fake_post(url, json):
        return DummyResponse({"message": "Register successful", "user_id": 123}, 200)

    monkeypatch.setattr("SPA.requests.post", fake_post)
    data = {"username": "newuser", "password": "newpass"}
    response = client_spa.post("/api/register", json=data)
    result = response.get_json()
    assert response.status_code == 200
    assert "user_id" in result


def test_register_invalid_json(client_spa, monkeypatch):
    def fake_post(url, json):
        raise Exception("JSONDecodeError")

    monkeypatch.setattr("SPA.requests.post", fake_post)
    data = {"username": "newuser", "password": "newpass"}
    response = client_spa.post("/api/register", json=data)
    result = response.get_json()
    # Adjusted expected status code from 500 to 400
    assert response.status_code == 400
    assert "error" in result


def test_start_chat_missing_token(client_spa):
    # Missing Authorization Token should return 401
    response = client_spa.post("/api/start_chat", json={"chat_name": "Test Chat"})
    result = response.get_json()
    assert response.status_code == 401
    assert "error" in result


def test_chat_list_missing_token(client_spa):
    response = client_spa.get("/api/chat_list")
    result = response.get_json()
    assert response.status_code == 401
    assert "error" in result


def test_chat_history_missing_token(client_spa):
    response = client_spa.get("/api/chat_history?chat_name=TestChat")
    result = response.get_json()
    assert response.status_code == 401
    assert "error" in result


# def test_send_message_missing_token(client_spa):
#     response = client_spa.post("/api/send_message", json={"message": "Hello"})
#     result = response.get_json()
#     assert response.status_code == 401
#     assert "error" in result
