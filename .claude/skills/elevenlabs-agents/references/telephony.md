# Telephony Reference

Deploy ElevenLabs agents on phone systems.

## Twilio Native Integration

### Prerequisites
- Twilio account with Account SID and Auth Token
- Twilio phone number (purchased or verified caller ID)

### Phone Number Types

| Type | Inbound | Outbound | Requirements |
|------|---------|----------|--------------|
| Purchased | ✅ | ✅ | Number in Twilio "Phone Numbers" section |
| Verified Caller ID | ❌ | ✅ | Number in Twilio "Verified Caller IDs" |

### Import Number

**Dashboard**:
1. Navigate to Phone Numbers tab in Agents Platform
2. Click "+ Import number" → "From Twilio"
3. Enter:
   - Label: Descriptive name
   - Phone Number: Your Twilio number
   - Twilio SID: Account SID
   - Twilio Token: Auth Token
4. Click Import

**API**:
```python
client.convai.phone_numbers.create(
    provider="twilio",
    phone_number="+1234567890",
    label="Customer Support Line",
    twilio_account_sid="ACxxx",
    twilio_auth_token="xxx"
)
```

### Assign Agent

```python
client.convai.phone_numbers.update(
    phone_number_id="phone_xxx",
    agent_id="agent_xxx"
)
```

### Inbound Calls

After assignment, calls to the number route to your agent automatically.
ElevenLabs configures Twilio webhooks during import.

### Outbound Calls

**Dashboard**: Click "Outbound call" button on phone number

**API**:
```python
response = client.convai.twilio.outbound_call(
    agent_id="agent_xxx",
    agent_phone_number_id="phone_xxx",
    to_number="+1987654321",
    conversation_initiation_client_data={
        "customer_name": "John Doe",
        "order_id": "ORD-12345"
    }
)
print(response.conversation_id)
```

### Batch Calling

For multiple outbound calls:
```python
client.convai.batch_calling.create(
    agent_id="agent_xxx",
    phone_number_id="phone_xxx",
    calls=[
        {"to_number": "+1111111111", "data": {"name": "Alice"}},
        {"to_number": "+2222222222", "data": {"name": "Bob"}},
    ]
)
```

## SIP Trunking

Connect existing PBX or VoIP systems.

### Import SIP Number

1. Navigate to Phone Numbers → Import Number → From SIP Trunk
2. Configure:
   - Label: Descriptive name
   - Phone Number: Your SIP number
   - SIP Trunk Address: Hostname/IP for outbound (no `sip:` prefix)
   - Transport: UDP, TCP, or TLS
   - Digest Auth: Username/Password (recommended)
   - Termination URI: ElevenLabs SIP endpoint for inbound

### Authentication

**Digest Authentication** (recommended):
- Username and password configured in SIP trunk
- No IP allowlisting required
- More secure with dynamic IPs

**ACL (IP Allowlisting)**:
- Allowlist ElevenLabs IP addresses
- Use static IP infrastructure (`sip-static.rtc.elevenlabs.io`)
- Requires /24 block allowlist (256 addresses)

### ElevenLabs SIP Endpoints

| Environment | Endpoint |
|-------------|----------|
| US/International | `sip-static.rtc.elevenlabs.io` |
| EU | Contact support for regional endpoints |

### Inbound Call Flow

1. Call arrives at your SIP provider
2. Provider routes to ElevenLabs termination URI
3. ElevenLabs matches number to agent
4. Agent handles conversation

### Custom SIP Headers

Include metadata in INVITE:
```
X-ElevenLabs-Conversation-Id: conv_xxx
X-ElevenLabs-Caller-Id: caller_123
```

Or Twilio-specific:
```
sip.twilio.callSid: CAxxxx
```

Metadata available in:
- Pre-call webhook
- Dynamic variables (`{{caller_id}}`, `{{call_id}}`)

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection failed | Check firewall allows SIP ports (5060 TCP, 5061 TLS) |
| Audio issues | Verify μ-law 8kHz format, check RTP ports |
| Auth failed | Verify digest credentials, check ACL if used |
| TLS errors | Validate provider certificates |

## Human Transfer

Transfer calls to human operators during conversation.

### Configuration

Add `transfer_to_number` system tool to agent:

```json
{
  "tools": [{
    "type": "system",
    "name": "transfer_to_number",
    "config": {
      "transfer_rules": [{
        "transfer_type": "conference",
        "number_type": "phone",
        "phone_number": "+1234567890",
        "condition": "User requests human support"
      }]
    }
  }]
}
```

### Transfer Types

**Conference** (default):
1. Agent calls destination number
2. Adds human to conference
3. Removes AI agent
4. Caller and human continue

**SIP REFER**:
1. Direct SIP transfer
2. Requires SIP trunk
3. Supports SIP URIs

### Transfer Messages

```json
{
  "user_wait_message": "Please hold while I connect you to a specialist.",
  "agent_handoff_message": "Customer needs help with order #12345, they've been waiting 2 minutes."
}
```

## Pre-Call Webhooks

Execute logic before call connects to agent.

### Configuration

Set webhook URL in agent settings. Webhook receives:

```json
{
  "phone_number": "+1234567890",
  "caller_id": "caller_xxx",
  "call_id": "call_xxx",
  "agent_id": "agent_xxx",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Response

Return dynamic variables for the conversation:

```json
{
  "dynamic_variables": {
    "customer_name": "John Doe",
    "account_status": "premium",
    "recent_orders": ["ORD-123", "ORD-456"]
  }
}
```

### Use Cases
- Look up caller in CRM
- Set personalization data
- Route to specific agent variant
- Block spam callers

## Dynamic Variables

Pass context to agent during calls.

### Sources
- Pre-call webhook response
- Conversation initiation data
- Tool responses
- SIP headers

### Usage in Prompts

```
System prompt:
Hello {{customer_name}}! I see you're a {{account_status}} member.
How can I help you today?
```

### Updating Variables

Server tools can update variables:
```json
{
  "response": {
    "order_status": "shipped",
    "tracking_number": "1Z999AA10123456784"
  },
  "update_variables": true
}
```
