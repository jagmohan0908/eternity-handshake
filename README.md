# Handshake MCP Gateway

Handshake MCP is a guarded domain gateway between AI agents and Frappe.

Agents call this service through JSON-RPC `tools/call`. This service owns Frappe credentials, idempotency, per-call limits, audit logs, low-concurrency writes, and circuit breaker behavior.

## Tools

- `send_whatsapp_template`

The gateway intentionally exposes only the WhatsApp template sending tool instead of broad Frappe CRUD write access.

## Run Locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m app.main
```

Set these in `.env`:

- `MCP_BEARER_TOKEN`
- `FRAPPE_BASE_URL`
- `FRAPPE_AUTHORIZATION`
- `WA_DEFAULT_TEMPLATE`
- `WA_DEFAULT_CHANNEL_ACCOUNT`

For multiple Frappe accounts, set `FRAPPE_TENANTS_JSON` instead of relying only on the single-account Frappe env vars. Agents can route a request by passing `tenant_key`, `frappe_tenant`, `company_key`, `account_key`, `frappe_account`, or `domain`.

Example:

```json
{
  "default": {
    "base_url": "https://site-a.example.com",
    "authorization": "token api_key:api_secret",
    "default_template": "vobiz_ai",
    "default_channel_account": "vobiz_main",
    "default_language": "en"
  },
  "clinic_b": {
    "base_url": "https://site-b.example.com",
    "authorization": "token api_key:api_secret",
    "default_template": "clinic_b_template",
    "default_channel_account": "clinic_b_channel",
    "default_language": "en"
  }
}
```

## Agent Endpoint

Use:

```text
POST /mcp
Authorization: Bearer <MCP_BEARER_TOKEN>
```

Example:

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "tools/call",
  "params": {
    "name": "send_whatsapp_template",
    "arguments": {
      "phone": "+919999999999",
      "company_key": "default",
      "message": "Clinic address: B-92, near Millennium City Centre Metro Station, Gurugram.",
      "template_name": "vobiz_dg",
      "channel_account": "Interakt SRIAAS Male",
      "language_code": "en",
      "body_values": ["Clinic address: B-92, near Millennium City Centre Metro Station, Gurugram."],
      "agent_id": "vobiz-gemini-live",
      "call_id": "livekit-room-name",
      "idempotency_key": "vobiz-gemini-live:livekit-room-name:whatsapp:hash"
    }
  }
}
```

## Safety Defaults

- WhatsApp sends: 1 per `tenant + agent_id + call_id`
- Total Frappe calls: 10 per `tenant + agent_id + call_id`
- Idempotency TTL: 24 hours
- Frappe write concurrency: 2

## WhatsApp Behavior

The gateway sends approved templates only. It does not send direct/free-text WhatsApp messages.

Default template assumption:

```text
Hi, I am from SRIAAS {{1}}
```

The agent's generated text is passed as the first body variable.
