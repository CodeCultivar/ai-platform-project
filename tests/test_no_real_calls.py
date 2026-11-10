import socket

import pytest

import ask


def test_unfaked_model_call_fails_the_test():
    with pytest.raises(AssertionError, match="was not faked"):
        ask.client.messages.create(model=ask.MODEL, max_tokens=1, messages=[{"role": "user", "content": "hi"}])


def test_network_connections_are_blocked():
    with socket.socket() as sock:
        with pytest.raises(RuntimeError, match="must not open network connections"):
            sock.connect(("203.0.113.1", 443))
