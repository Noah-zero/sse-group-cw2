import pytest
import os
from chat.deepseek import app as deepseek_app
from chat.tests.conftest import (
    DummySupabaseClient,
    DummyOpenAIClient,
    DummySupabaseResponse,
)  # Import the DummySupabaseClient defined in conftest


# Define a fake jwt.decode function to bypass token verification
def fake_jwt_decode(token, secret, algorithms):
    return {"user_id": 1}


@pytest.fixture
def client_deepseek():
    deepseek_app.config["TESTING"] = True
    with deepseek_app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def patch_deepseek_dependencies(monkeypatch):
    # Replace deepseek.jwt.decode with our fake_jwt_decode to bypass token checks
    monkeypatch.setattr("chat.deepseek.jwt.decode", fake_jwt_decode)
    # Replace deepseek.supabase_client with an instance of DummySupabaseClient
    monkeypatch.setattr("chat.deepseek.supabase_client", DummySupabaseClient())
    # Replace deepseek.OpenAI with an instance of DummyOpenAIClient
    monkeypatch.setattr(
        "chat.deepseek.OpenAI", lambda *args, **kwargs: DummyOpenAIClient()
    )


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


def test_send_message_streaming(client_deepseek, monkeypatch):
    def mock_get_conversation(supabase_client, user_id, chat_name):
        return DummySupabaseResponse(
            [{"id": 1, "name": "Test Chat", "messages": {"messages": ["Hello", "Hi"]}}]
        )

    monkeypatch.setattr("chat.deepseek.get_conversation", mock_get_conversation)

    def mock_streaming_chat(*args, **kwargs):
        return DummyOpenAIClient.chat.completions.create_streaming()

    monkeypatch.setattr(
        "chat.deepseek.ChatBot.chat",
        lambda self, conversation, stream: (
            mock_streaming_chat() if stream else "Mocked response"
        ),
    )

    token = "Bearer dummy_token"
    response = client_deepseek.post(
        "/send_message",
        headers={"Authorization": token},
        json={"message": "Hello", "chat_name": "Test Chat"},
    )

    assert response.status_code == 200
    assert b"Mocked response" in b"".join(response.response)


def test_client_initialization():
    from chat.deepseek import client_xunfei

    assert client_xunfei.api_key == os.environ.get("CLIENT_XUNFEI_API_KEY")
    assert client_xunfei.base_url == os.environ.get("CLIENT_XUNFEI_BASE_URL")
