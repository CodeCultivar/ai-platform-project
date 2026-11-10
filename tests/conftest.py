import socket
from unittest.mock import patch

import pytest

import ask


def unscripted_reply(**kwargs):
    raise AssertionError("The model call was not faked. Use the fake_model fixture and script its replies.")


@pytest.fixture(autouse=True)
def no_real_model_calls():
    # Every test gets a fake model call, so the real API is never reached by accident.
    with patch.object(ask.client.messages, "create", side_effect=unscripted_reply) as create:
        yield create


@pytest.fixture
def fake_model(no_real_model_calls):
    # Script the model by setting side_effect to a list of messages and exceptions, one per call.
    return no_real_model_calls


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    # Belt and braces: even code that bypasses the model fake cannot open a connection.
    def refuse(*args, **kwargs):
        raise RuntimeError("Tests must not open network connections.")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)
