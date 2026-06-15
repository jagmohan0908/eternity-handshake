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

    monkeypatch.setattr(gateway, "resolve_or_create_conversation", lambda phone, channel, config: "conversation-1")

    def fake_frappe_request(method, path, *, config, json_body=None, params=None):
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


def test_resolve_frappe_config_uses_requested_tenant(monkeypatch):
    monkeypatch.setenv(
        "FRAPPE_TENANTS_JSON",
        json.dumps(
            {
                "default": {
                    "base_url": "https://default.example.com",
                    "authorization": "token default:key",
                    "default_template": "default_template",
                    "default_channel_account": "default_channel",
                },
                "clinic_b": {
                    "base_url": "https://clinic-b.example.com",
                    "authorization": "token clinic-b:key",
                    "default_template": "clinic_b_template",
                    "default_channel_account": "clinic_b_channel",
                },
            }
        ),
    )

    config = gateway.resolve_frappe_config({"company_key": "clinic_b"})

    assert config["tenant_key"] == "clinic_b"
    assert config["base_url"] == "https://clinic-b.example.com"
    assert config["authorization"] == "token clinic-b:key"
    assert config["default_template"] == "clinic_b_template"
    assert config["default_channel_account"] == "clinic_b_channel"


def test_whatsapp_uses_tenant_defaults(monkeypatch):
    init_db()
    calls = []
    monkeypatch.setenv(
        "FRAPPE_TENANTS_JSON",
        json.dumps(
            {
                "clinic_b": {
                    "base_url": "https://clinic-b.example.com",
                    "authorization": "token clinic-b:key",
                    "default_template": "clinic_b_template",
                    "default_channel_account": "clinic_b_channel",
                    "default_language": "en",
                }
            }
        ),
    )
    monkeypatch.setattr(gateway, "resolve_or_create_conversation", lambda phone, channel, config: "conversation-tenant")

    def fake_frappe_request(method, path, *, config, json_body=None, params=None):
        calls.append({"method": method, "path": path, "config": config, "json_body": json_body})
        return {
            "message": {
                "conversation": "conversation-tenant",
                "sent": True,
                "delivery_status": "Sent",
            }
        }

    monkeypatch.setattr(gateway, "frappe_request", fake_frappe_request)

    result = send_whatsapp_template(
        {
            "company_key": "clinic_b",
            "phone": "+919999999999",
            "message": "Address",
            "body_values": ["Address"],
            "agent_id": "agent",
            "call_id": "call-tenant-defaults",
            "idempotency_key": "key-tenant-defaults",
        }
    )

    assert result["status"] == "sent"
    assert result["tenant_key"] == "clinic_b"
    assert result["template_name"] == "clinic_b_template"
    assert result["channel_account"] == "clinic_b_channel"
    assert calls[0]["config"]["base_url"] == "https://clinic-b.example.com"
    assert calls[0]["json_body"]["template_name"] == "clinic_b_template"
