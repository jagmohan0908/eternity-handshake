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
- `WA_CHANNEL_ACCOUNTS_BY_PROFILE_JSON`

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
      "profile_key": "male-kamal-sriaas",
      "message": "Clinic address: B-92, near Millennium City Centre Metro Station, Gurugram.",
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

- WhatsApp sends: 1 per `agent_id + call_id`
- Total Frappe calls: 10 per `agent_id + call_id`
- Idempotency TTL: 24 hours
- Frappe write concurrency: 2

## WhatsApp Behavior

The gateway sends approved templates only. It does not send direct/free-text WhatsApp messages.

Template body assumption:

```text
Hi, I am from SRIAAS {{1}}
```

The `template_name` comes from the matching profile config, and the agent's generated text is passed as the first body variable.

To route WhatsApp sends by voice profile, set both the WhatsApp channel account and template in `WA_CHANNEL_ACCOUNTS_BY_PROFILE_JSON`:

```text
WA_CHANNEL_ACCOUNTS_BY_PROFILE_JSON={"male-kamal-sriaas":{"channel_account":"Interakt SRIAAS Male","template_name":"vobiz_ai","language_code":"en"},"female-megha-sriaas":{"channel_account":"Interakt SRIAAS Female","template_name":"vobiz_ai_female","language_code":"en"}}
```

If a request includes `channel_account` or `template_name`, that explicit value wins for that field. Otherwise MCP uses the profile mapping. Without a mapped or explicit channel/template, the send is rejected.
