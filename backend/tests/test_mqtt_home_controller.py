from __future__ import annotations

import asyncio
from dataclasses import fields
from types import SimpleNamespace

from app.config import Settings
from app.services.mqtt_home import MQTTHomeAutomationController


def make_settings(**overrides):
    base = Settings()
    values = {field.name: getattr(base, field.name) for field in fields(Settings)}
    values.update(overrides)
    return SimpleNamespace(**values)


def test_publish_action_rejects_unsupported_action():
    settings = make_settings(home_mqtt_enabled=True)
    controller = MQTTHomeAutomationController(settings)

    result = asyncio.run(controller.publish_action("unsupported_action"))

    assert result["status"] == "failed"
    assert result["domain"] == "home"
    assert "Unsupported home action" in result["error"]


def test_publish_action_fails_when_mqtt_disabled():
    settings = make_settings(home_mqtt_enabled=False)
    controller = MQTTHomeAutomationController(settings)

    result = asyncio.run(controller.publish_action("light_on"))

    assert result["status"] == "failed"
    assert result["domain"] == "home"
    assert "disabled" in result["error"].lower()


def test_build_command_updates_internal_state_for_scenes_and_status_snapshot():
    settings = make_settings(
        home_temperature_default=24,
        home_fan_speed_min=0,
        home_fan_speed_max=100,
        home_fan_speed_step=10,
        home_ac_temp_min=16,
        home_ac_temp_max=30,
        home_ac_temp_step=1,
    )
    controller = MQTTHomeAutomationController(settings)

    scene = controller._build_command("scene_good_night", None)
    status = controller._build_command("status_check", None)

    assert scene["action"] == "scene_good_night"
    assert status["action"] == "status_check"
    assert status["lights_on"] is False
    assert status["door_locked"] is True
    assert status["fan_speed"] <= settings.home_fan_speed_max


def test_publish_action_success_path_with_stubbed_publish():
    settings = make_settings(home_mqtt_enabled=True)
    controller = MQTTHomeAutomationController(settings)
    controller._connected = True
    controller._publish_json = lambda payload: None

    result = asyncio.run(controller.publish_action("light_on"))

    assert result["status"] == "executed"
    assert result["domain"] == "home"
    assert result["action"] == "light_on"
    assert result["topic"] == settings.home_mqtt_control_topic
