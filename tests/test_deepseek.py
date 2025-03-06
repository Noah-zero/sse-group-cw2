import pytest
from deepseek import app as deepseek_app


# Dummy Supabase mock class
class DummySupabaseResponse:
    def __init__(self, data):
        self.data = data


class DummySupabaseTable:
    def __init__(self, data=None):
        self.data = data or []

    def select(self, columns="*"):
        self.columns = columns
        return self

    def eq(self, key, value):
        self.filter_key = key
        self.filter_value = value
        return self

    def execute(self):
        # Return simulated data when filtering by user_id
        if hasattr(self, "filter_key") and self.filter_key == "user_id":
            return DummySupabaseResponse(
                [{"id": 1, "name": "Test Chat", "messages": {"messages": []}}]
            )
        return DummySupabaseResponse([])

    def update(self, data):
        self.updated_data = data
        return self

    def insert(self, data):
        self.inserted_data = data
        return self


class DummySupabaseClient:
    def table(self, name):
        return DummySupabaseTable()


# Define a fake jwt.decode to bypass token verification
def fake_jwt_decode(token, secret, algorithms):
    return {"user_id": 1}


@pytest.fixture
def client_deepseek():
    deepseek_app.config["TESTING"] = True
    with deepseek_app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def patch_deepseek_dependencies(monkeypatch):
    monkeypatch.setattr("deepseek.jwt.decode", fake_jwt_decode)
    monkeypatch.setattr("deepseek.supabase_client", DummySupabaseClient())


def test_start_chat_success(client_deepseek):
    token = "Bearer dummy_token"
    data = {"chat_name": "New Chat"}
    response = client_deepseek.post(
        "/start_chat", headers={"Authorization": token}, json=data
    )
    result = response.get_json()
    assert response.status_code == 200
    assert "chat_name" in result


def test_start_chat_invalid_payload(client_deepseek):
    token = "Bearer dummy_token"
    data = {}  # Missing chat_name
    response = client_deepseek.post(
        "/start_chat", headers={"Authorization": token}, json=data
    )
    assert response.status_code == 400


def test_chat_list_success(client_deepseek):
    token = "Bearer dummy_token"
    response = client_deepseek.get("/chat_list", headers={"Authorization": token})
    result = response.get_json()
    assert response.status_code == 200
    assert "chats" in result


def test_chat_history_missing_chat_name(client_deepseek):
    token = "Bearer dummy_token"
    response = client_deepseek.get("/chat_history", headers={"Authorization": token})
    result = response.get_json()
    assert response.status_code == 400
    assert "message" in result


def test_send_message_missing_token(client_deepseek):
    response = client_deepseek.post(
        "/send_message", json={"message": "Hello", "chat_name": "Test Chat"}
    )
    result = response.get_json()
    assert response.status_code == 401
    assert "message" in result
