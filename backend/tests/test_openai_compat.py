"""Regression tests for the OpenAI-compatible surface.

A local AI client polls ``GET /v1/models`` to discover models. When that route
was missing, every poll produced a 404 in the backend log. These tests keep
the probe and its follow-up calls working.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_models_probe_returns_openai_shape():
    response = client.get("/v1/models")
    assert response.status_code == 200

    body = response.json()
    assert body["object"] == "list"
    assert body["data"]
    assert all(item["object"] == "model" and item["id"] for item in body["data"])


def test_model_retrieve_and_unknown_model():
    known = client.get("/v1/models").json()["data"][0]["id"]

    found = client.get(f"/v1/models/{known}")
    assert found.status_code == 200
    assert found.json()["id"] == known

    assert client.get("/v1/models/does-not-exist").status_code == 404


def test_chat_completion_shape():
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Hello"}],
        },
    )
    assert response.status_code == 200

    body = response.json()
    assert body["object"] == "chat.completion"
    assert body["choices"][0]["message"]["role"] == "assistant"
    assert isinstance(body["choices"][0]["message"]["content"], str)


def test_chat_completion_stream_terminates():
    response = client.post(
        "/v1/chat/completions",
        json={
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": True,
        },
    )
    assert response.status_code == 200
    assert response.text.rstrip().endswith("data: [DONE]")


def test_embeddings_use_existing_dimensions():
    response = client.post("/v1/embeddings", json={"input": "hello"})
    assert response.status_code == 200

    body = response.json()
    assert body["object"] == "list"
    assert len(body["data"]) == 1
    assert len(body["data"][0]["embedding"]) > 0


def test_favicon_does_not_404():
    assert client.get("/favicon.ico").status_code == 204
