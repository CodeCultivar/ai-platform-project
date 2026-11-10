from types import SimpleNamespace
from unittest.mock import patch

import anthropic
import httpx2
from fastapi.testclient import TestClient

import main
from main import app

client = TestClient(app)

REQUEST = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")

def fake_message(text):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])

def timeout_error():
    return anthropic.APITimeoutError(request=REQUEST)

def server_error():
    response = httpx2.Response(500, request=REQUEST)
    return anthropic.InternalServerError(message="Internal server error", response=response, body=None)

def auth_error():
    response = httpx2.Response(401, request=REQUEST)
    return anthropic.AuthenticationError(message="Invalid API key", response=response, body=None)

def post_question():
    return client.post("/ask", json={"question": "What does a cow say?"})

def test_ask_question():
    valid_payload = {
        "question": "What does a cow say?"
    }
    with patch.object(main.client.messages, "create", return_value=fake_message("A cow says moo.")):
        response = client.post("/ask", json=valid_payload)
    assert response.status_code == 200
    answer = response.json()["answer"]
    assert "moo" in answer

def test_ask_retries_after_timeout_then_succeeds():
    with patch.object(main.client.messages, "create", side_effect=[timeout_error(), fake_message("A cow says moo.")]) as create, \
            patch("main.time.sleep") as sleep:
        response = post_question()
    assert response.status_code == 200
    assert response.json() == {"answer": "A cow says moo."}
    assert create.call_count == 2
    sleep.assert_called_once_with(main.RETRY_DELAY_SECONDS)

def test_ask_returns_504_when_every_attempt_times_out():
    with patch.object(main.client.messages, "create", side_effect=[timeout_error()] * main.MAX_ATTEMPTS) as create, \
            patch("main.time.sleep"):
        response = post_question()
    assert response.status_code == 504
    assert response.json() == {"error": "model_timeout", "message": "The model did not respond in time."}
    assert create.call_count == main.MAX_ATTEMPTS

def test_ask_returns_502_when_server_errors_persist():
    with patch.object(main.client.messages, "create", side_effect=[server_error()] * main.MAX_ATTEMPTS) as create, \
            patch("main.time.sleep"):
        response = post_question()
    assert response.status_code == 502
    assert response.json() == {"error": "model_unavailable", "message": "The model is temporarily unavailable."}
    assert create.call_count == main.MAX_ATTEMPTS

def test_ask_does_not_retry_client_errors():
    with patch.object(main.client.messages, "create", side_effect=auth_error()) as create, \
            patch("main.time.sleep") as sleep:
        response = post_question()
    assert response.status_code == 502
    assert response.json() == {"error": "model_error", "message": "The model call failed."}
    assert create.call_count == 1
    sleep.assert_not_called()

def test_ask_returns_502_when_response_has_no_text():
    with patch.object(main.client.messages, "create", return_value=SimpleNamespace(content=[])):
        response = post_question()
    assert response.status_code == 502
    assert response.json() == {"error": "model_invalid_response", "message": "The model returned no text."}

def test_ask_null_question():
    invalid_payload = {
        "question": ""
    }

    response = client.post("/ask", json=invalid_payload)

    assert response.status_code == 422

def test_ask_question_invalid_question():
    valid_payload = {
        "question": "Wh"
    }

    response = client.post("/ask", json=valid_payload)

    assert response.status_code == 422
