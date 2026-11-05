from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

def test_ask_question():
    valid_payload = {
        "question": "What does a cow say?"
    }

    response = client.post("/ask", json=valid_payload)

    assert response.status_code == 200
    assert response.json() == {"answer": "Moo"}

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