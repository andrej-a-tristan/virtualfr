"""Tests for girlfriend canon injection into chat gateway."""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.api.store import set_girlfriend, _all_girlfriends, _sessions, set_session_user


@pytest.fixture(autouse=True)
def clear_store():
    """Clear in-memory store before each test."""
    _all_girlfriends.clear()
    _sessions.clear()
    yield
    _all_girlfriends.clear()
    _sessions.clear()


@pytest.fixture
def mock_girlfriend():
    """Sample girlfriend with identity and identity_canon."""
    return {
        "id": "gf-test-1",
        "name": "Luna",
        "avatar_url": "https://example.com/avatar.png",
        "traits": {"emotional_style": "warm"},
        "identity": {
            "name": "Luna",
            "job_vibe": "barista",
            "hobbies": ["reading", "coffee walks", "cooking"],
            "origin_vibe": "cozy-european",
        },
        "identity_canon": {
            "backstory": "Luna grew up in a small European town.\n\nShe moved to the city for a fresh start.",
            "daily_routine": "Mornings at the café, afternoons for reading, evenings for cooking.",
            "favorites": {
                "music_vibe": "indie / lo-fi",
                "comfort_food": "homemade pasta",
                "weekend_idea": "café hopping",
            },
            "memory_seeds": [
                "I learned cooking from my grandmother",
                "I have a comfort playlist for rainy days",
                "There's a café I go to when I need to think",
            ],
        },
        "created_at": "2025-01-01T00:00:00Z",
    }


def test_canon_injection_with_girlfriend(mock_girlfriend):
    """When girlfriend exists with identity/canon, system prompt is prepended."""
    session_id = "test-session-123"
    set_session_user(session_id, {"id": "user-1", "email": "test@test.com"})
    set_girlfriend(session_id, mock_girlfriend)
    
    captured_messages = []
    
    async def mock_stream(*args, **kwargs):
        # Capture the messages passed to _proxy_stream
        captured_messages.extend(kwargs.get("messages", []))
        yield "event: token\ndata: {\"token\": \"Hi\"}\n\n"
        yield "event: done\ndata: {\"finish_reason\": \"stop\"}\n\n"
    
    with patch("app.routers.chat._proxy_stream", side_effect=mock_stream):
        client = TestClient(app)
        response = client.post(
            "/api/chat/stream",
            json={
                "session_id": session_id,
                "model": "test-model",
                "model_version": "1.0",
                "messages": [{"role": "user", "content": "Hi there!"}],
            },
            headers={"Authorization": "Bearer dev-key"},
        )
        # Consume the streaming response
        list(response.iter_lines())
    
    # Should have 2 messages: system (canon) + user
    assert len(captured_messages) == 2
    
    # First message should be the canon system prompt
    assert captured_messages[0]["role"] == "system"
    assert "CANON IDENTITY" in captured_messages[0]["content"]
    assert "Luna" in captured_messages[0]["content"]
    assert "barista" in captured_messages[0]["content"]
    assert "reading" in captured_messages[0]["content"]
    
    # Second message should be the user message
    assert captured_messages[1]["role"] == "user"
    assert captured_messages[1]["content"] == "Hi there!"


def test_no_injection_without_girlfriend():
    """When no girlfriend exists, no system prompt is injected."""
    session_id = "test-session-no-gf"
    set_session_user(session_id, {"id": "user-2", "email": "test2@test.com"})
    # No girlfriend set
    
    captured_messages = []
    
    async def mock_stream(*args, **kwargs):
        captured_messages.extend(kwargs.get("messages", []))
        yield "event: token\ndata: {\"token\": \"Hello\"}\n\n"
        yield "event: done\ndata: {\"finish_reason\": \"stop\"}\n\n"
    
    with patch("app.routers.chat._proxy_stream", side_effect=mock_stream):
        client = TestClient(app)
        response = client.post(
            "/api/chat/stream",
            json={
                "session_id": session_id,
                "model": "test-model",
                "model_version": "1.0",
                "messages": [{"role": "user", "content": "Hello!"}],
            },
            headers={"Authorization": "Bearer dev-key"},
        )
        list(response.iter_lines())
    
    # Should only have the user message (no injection)
    assert len(captured_messages) == 1
    assert captured_messages[0]["role"] == "user"
    assert captured_messages[0]["content"] == "Hello!"


def test_injection_preserves_existing_messages():
    """Canon injection prepends; existing messages (including any client system messages) are preserved after."""
    session_id = "test-session-preserve"
    set_session_user(session_id, {"id": "user-3", "email": "test3@test.com"})
    set_girlfriend(session_id, {
        "id": "gf-2",
        "name": "Aria",
        "identity": {"name": "Aria", "job_vibe": "tech", "hobbies": ["gaming"], "origin_vibe": "big-city"},
        "identity_canon": {
            "backstory": "Aria loves tech.",
            "daily_routine": "Code all day.",
            "favorites": {"music_vibe": "electronic", "comfort_food": "pizza", "weekend_idea": "gaming marathon"},
            "memory_seeds": ["I have a favorite keyboard"],
        },
    })
    
    captured_messages = []
    
    async def mock_stream(*args, **kwargs):
        captured_messages.extend(kwargs.get("messages", []))
        yield "event: done\ndata: {\"finish_reason\": \"stop\"}\n\n"
    
    with patch("app.routers.chat._proxy_stream", side_effect=mock_stream):
        client = TestClient(app)
        response = client.post(
            "/api/chat/stream",
            json={
                "session_id": session_id,
                "model": "test-model",
                "model_version": "1.0",
                "messages": [
                    {"role": "system", "content": "Be helpful."},
                    {"role": "user", "content": "What's your name?"},
                ],
            },
            headers={"Authorization": "Bearer dev-key"},
        )
        list(response.iter_lines())
    
    # Should have 3 messages: canon system + client system + user
    assert len(captured_messages) == 3
    assert captured_messages[0]["role"] == "system"
    assert "CANON IDENTITY" in captured_messages[0]["content"]
    assert "Aria" in captured_messages[0]["content"]
    
    assert captured_messages[1]["role"] == "system"
    assert captured_messages[1]["content"] == "Be helpful."
    
    assert captured_messages[2]["role"] == "user"
    assert captured_messages[2]["content"] == "What's your name?"


def test_injection_with_partial_canon():
    """Injection works even if identity_canon is partial or missing some fields."""
    session_id = "test-session-partial"
    set_session_user(session_id, {"id": "user-4", "email": "test4@test.com"})
    set_girlfriend(session_id, {
        "id": "gf-3",
        "name": "Maya",
        "identity": {"name": "Maya", "job_vibe": "creative", "hobbies": [], "origin_vibe": None},
        # identity_canon missing entirely
    })
    
    captured_messages = []
    
    async def mock_stream(*args, **kwargs):
        captured_messages.extend(kwargs.get("messages", []))
        yield "event: done\ndata: {\"finish_reason\": \"stop\"}\n\n"
    
    with patch("app.routers.chat._proxy_stream", side_effect=mock_stream):
        client = TestClient(app)
        response = client.post(
            "/api/chat/stream",
            json={
                "session_id": session_id,
                "model": "test-model",
                "model_version": "1.0",
                "messages": [{"role": "user", "content": "Hey!"}],
            },
            headers={"Authorization": "Bearer dev-key"},
        )
        list(response.iter_lines())
    
    # Should still inject system prompt with anchors even without full canon
    assert len(captured_messages) == 2
    assert captured_messages[0]["role"] == "system"
    assert "Maya" in captured_messages[0]["content"]
    assert "creative" in captured_messages[0]["content"]
