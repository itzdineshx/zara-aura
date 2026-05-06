from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_health_and_home_mode_endpoints():
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        set_home = client.post("/home-mode", json={"enabled": True})
        assert set_home.status_code == 200
        assert set_home.json() == {"enabled": True}

        get_home = client.get("/home-mode")
        assert get_home.status_code == 200
        assert get_home.json() == {"enabled": True}


def test_home_status_endpoint_shape():
    with TestClient(app) as client:
        response = client.get("/home/status")
        assert response.status_code == 200
        payload = response.json()

        assert "connected" in payload
        assert "broker" in payload
        assert payload["control_topic"] == "zara/home/control"
        assert payload["status_topic"] == "zara/home/status"


def test_chat_home_action_blocked_when_home_mode_off():
    with TestClient(app) as client:
        client.post("/home-mode", json={"enabled": False})

        chat = client.post(
            "/chat",
            json={
                "text": "turn on lights",
                "mode": "smart",
                "preferred_language": "en",
                "synthesize": False,
            },
        )

        assert chat.status_code == 200
        payload = chat.json()

        assert payload["action"]["domain"] == "home"
        assert payload["action"]["status"] == "blocked_home_mode"
        assert "Home Automation is OFF" in payload["text"]


def test_chat_home_action_executes_with_stubbed_mqtt_publish():
    with TestClient(app) as client:
        services = app.state.services

        async def fake_publish_action(action: str, value=None):
            return {
                "type": action,
                "action": action,
                "domain": "home",
                "status": "executed",
                "topic": services.home_controller.settings.home_mqtt_control_topic,
            }

        services.home_controller.publish_action = fake_publish_action

        client.post("/home-mode", json={"enabled": True})

        chat = client.post(
            "/chat",
            json={
                "text": "turn off tv",
                "mode": "smart",
                "preferred_language": "en",
                "synthesize": False,
            },
        )

        assert chat.status_code == 200
        payload = chat.json()

        assert payload["action"]["domain"] == "home"
        assert payload["action"]["status"] == "executed"
        assert payload["action"]["action"] == "tv_off"
        assert "command sent" in payload["text"].lower()
