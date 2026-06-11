import os

os.environ.setdefault("MCP_BEARER_TOKEN", "test-token")
os.environ.setdefault("MCP_DB_PATH", "data/test_gateway.sqlite3")

from app.main import init_db, normalize_phone, send_whatsapp_template  # noqa: E402


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
            "call_id": "call",
            "idempotency_key": "key-1",
        }
    )
    assert result["status"] == "failed"

