import importlib
from types import SimpleNamespace
from unittest.mock import patch

import anthropic
import httpx2
import pytest
from fastapi.testclient import TestClient

import ask
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

def test_ask_question(fake_model):
    valid_payload = {
        "question": "What does a cow say?"
    }
    fake_model.side_effect = [fake_message("A cow says moo.")]
    response = client.post("/ask", json=valid_payload)
    assert response.status_code == 200
    answer = response.json()["answer"]
    assert "moo" in answer

def test_ask_retries_after_timeout_then_succeeds(fake_model):
    fake_model.side_effect = [timeout_error(), fake_message("A cow says moo.")]
    with patch("ask.time.sleep") as sleep:
        response = post_question()
    assert response.status_code == 200
    assert response.json() == {"answer": "A cow says moo."}
    assert fake_model.call_count == 2
    sleep.assert_called_once_with(ask.RETRY_DELAY_SECONDS)

def test_ask_returns_504_when_every_attempt_times_out(fake_model):
    fake_model.side_effect = [timeout_error()] * ask.MAX_ATTEMPTS
    with patch("ask.time.sleep"):
        response = post_question()
    assert response.status_code == 504
    assert response.json() == {"error": "model_timeout", "message": "The model did not respond in time."}
    assert fake_model.call_count == ask.MAX_ATTEMPTS

def test_ask_returns_502_when_server_errors_persist(fake_model):
    fake_model.side_effect = [server_error()] * ask.MAX_ATTEMPTS
    with patch("ask.time.sleep"):
        response = post_question()
    assert response.status_code == 502
    assert response.json() == {"error": "model_unavailable", "message": "The model is temporarily unavailable."}
    assert fake_model.call_count == ask.MAX_ATTEMPTS

def test_ask_does_not_retry_client_errors(fake_model):
    fake_model.side_effect = auth_error()
    with patch("ask.time.sleep") as sleep:
        response = post_question()
    assert response.status_code == 502
    assert response.json() == {"error": "model_error", "message": "The model call failed."}
    assert fake_model.call_count == 1
    sleep.assert_not_called()

def test_ask_returns_502_when_response_has_no_text(fake_model):
    fake_model.side_effect = [SimpleNamespace(content=[])]
    response = post_question()
    assert response.status_code == 502
    assert response.json() == {"error": "model_invalid_response", "message": "The model returned no text."}

def test_settings_read_from_environment(monkeypatch):
    monkeypatch.setenv("CLAUDE_MODEL", "claude-test-model")
    monkeypatch.setenv("REQUEST_TIMEOUT_SECONDS", "2.5")
    monkeypatch.setenv("MAX_ATTEMPTS", "5")
    monkeypatch.setenv("RETRY_DELAY_SECONDS", "0.1")
    try:
        reloaded = importlib.reload(ask)
        assert reloaded.MODEL == "claude-test-model"
        assert reloaded.REQUEST_TIMEOUT_SECONDS == 2.5
        assert reloaded.MAX_ATTEMPTS == 5
        assert reloaded.RETRY_DELAY_SECONDS == 0.1
    finally:
        monkeypatch.undo()
        importlib.reload(ask)

def test_read_setting_names_the_variable_when_invalid(monkeypatch):
    monkeypatch.setenv("MAX_ATTEMPTS", "abc")
    with pytest.raises(ValueError, match="MAX_ATTEMPTS must be a valid int, got 'abc'"):
        ask.read_setting("MAX_ATTEMPTS", "3", int)

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
