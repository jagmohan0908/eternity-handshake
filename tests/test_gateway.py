import os
import json

os.environ.setdefault("MCP_BEARER_TOKEN", "test-token")
os.environ.setdefault("MCP_DB_PATH", "data/test_gateway.sqlite3")

import app.main as gateway  # noqa: E402
from app.main import init_db, normalize_phone, send_whatsapp_template  # noqa: E402


def test_gateway_exposes_only_whatsapp_tool():
    assert sorted(gateway.TOOLS) == ["send_whatsapp_template"]


def test_normalize_india_phone():
    assert normalize_phone("99999 99999") == "+919999999999"


def test_whatsapp_validates_template_variable_count():
    init_db()
    result = send_whatsapp_template(
        {
            "phone": "+919999999999",
            "message": "Address",
            "body_values": [],
            "agent_id": "agent",
            "call_id": "call-template-variable-count",
            "idempotency_key": "key-1",
        }
    )
    assert result["status"] == "failed"


def test_whatsapp_frappe_failed_delivery_is_failed(monkeypatch):
    init_db()

    monkeypatch.setenv(
        "WA_CHANNEL_ACCOUNTS_BY_PROFILE_JSON",
        json.dumps({"default-test-profile": {"channel_account": "Interakt SRIAAS Male", "template_name": "vobiz_ai"}}),
    )
    monkeypatch.setattr(gateway, "resolve_or_create_conversation", lambda phone, channel: "conversation-1")

    def fake_frappe_request(method, path, *, json_body=None, params=None):
        return {
            "message": {
                "conversation": "conversation-1",
                "sent": False,
                "delivery_status": "Failed",
                "error": "No approved template found",
            }
        }

    monkeypatch.setattr(gateway, "frappe_request", fake_frappe_request)

    result = send_whatsapp_template(
        {
            "profile_key": "default-test-profile",
            "phone": "+919999999999",
            "message": "Address",
            "body_values": ["Address"],
            "agent_id": "agent",
            "call_id": "call-failed-delivery",
            "idempotency_key": "key-failed-delivery",
        }
    )

    assert result["status"] == "failed"
    assert result["delivery_status"] == "failed"
    assert result["error"] == "No approved template found"


def test_whatsapp_uses_profile_channel_mapping(monkeypatch):
    init_db()
    captured = {}
    monkeypatch.setenv(
        "WA_CHANNEL_ACCOUNTS_BY_PROFILE_JSON",
        json.dumps(
            {
                "male-kamal-sriaas": {
                    "channel_account": "Interakt SRIAAS Male",
                    "template_name": "vobiz_ai",
                    "language_code": "en",
                }
            }
        ),
    )
    def fake_resolve_conversation(phone, channel):
        captured["channel"] = channel
        return "conversation-1"

    monkeypatch.setattr(gateway, "resolve_or_create_conversation", fake_resolve_conversation)

    def fake_frappe_request(method, path, *, json_body=None, params=None):
        captured["template_body"] = json_body
        return {
            "message": {
                "conversation": "conversation-1",
                "sent": True,
                "delivery_status": "Sent",
            }
        }

    monkeypatch.setattr(gateway, "frappe_request", fake_frappe_request)

    result = send_whatsapp_template(
        {
            "profile_key": "male-kamal-sriaas",
            "phone": "+919999999999",
            "message": "Address",
            "body_values": ["Address"],
            "agent_id": "agent",
            "call_id": "call-profile-channel",
            "idempotency_key": "key-profile-channel",
        }
    )

    assert result["status"] == "sent"
    assert result["profile_key"] == "male-kamal-sriaas"
    assert result["template_name"] == "vobiz_ai"
    assert result["channel_account"] == "Interakt SRIAAS Male"
    assert captured["channel"] == "Interakt SRIAAS Male"


def test_whatsapp_rejects_missing_profile_template_and_channel(monkeypatch):
    init_db()
    monkeypatch.delenv("WA_CHANNEL_ACCOUNTS_BY_PROFILE_JSON", raising=False)

    result = send_whatsapp_template(
        {
            "profile_key": "missing-profile",
            "phone": "+919999999999",
            "message": "Address",
            "body_values": ["Address"],
            "agent_id": "agent",
            "call_id": "call-missing-profile-config",
            "idempotency_key": "key-missing-profile-config",
        }
    )

    assert result["status"] == "failed"
    assert "template_name is required" in result["error"]
