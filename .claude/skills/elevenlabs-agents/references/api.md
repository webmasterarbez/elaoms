# API Reference

ElevenLabs Agents Platform API endpoints.

Base URL: `https://api.elevenlabs.io/v1/convai`

## Authentication

All requests require `xi-api-key` header:
```
xi-api-key: your_api_key_here
```

## Agents

### Create Agent

```
POST /agents/create
```

```python
agent = client.convai.agents.create(
    name="Support Assistant",
    conversation_config={
        "agent": {
            "prompt": {
                "prompt": "You are a helpful support assistant...",
            },
            "first_message": "Hi! How can I help you today?",
            "language": "en"
        },
        "tts": {
            "voice_id": "21m00Tcm4TlvDq8ikWAM"
        }
    }
)
print(agent.agent_id)
```

**Request Body**:
```json
{
  "name": "string",
  "conversation_config": {
    "agent": {
      "prompt": { "prompt": "string" },
      "first_message": "string",
      "language": "string"
    },
    "tts": {
      "voice_id": "string",
      "model_id": "string",
      "stability": 0.5,
      "similarity_boost": 0.75
    },
    "stt": {
      "model": "string"
    },
    "turn_detection": {
      "mode": "server_vad"
    }
  },
  "platform_settings": {
    "auth": { "enable_auth": false },
    "widget": { "variant": "compact" }
  }
}
```

### Get Agent

```
GET /agents/{agent_id}
```

```python
agent = client.convai.agents.get(agent_id="agent_xxx")
```

### Update Agent

```
PATCH /agents/{agent_id}
```

```python
client.convai.agents.update(
    agent_id="agent_xxx",
    name="Updated Name",
    conversation_config={
        "agent": {
            "prompt": {"prompt": "Updated system prompt..."}
        }
    }
)
```

### List Agents

```
GET /agents
```

```python
agents = client.convai.agents.list(
    page_size=30,
    search="support"
)
for agent in agents:
    print(agent.name, agent.agent_id)
```

### Delete Agent

```
DELETE /agents/{agent_id}
```

```python
client.convai.agents.delete(agent_id="agent_xxx")
```

## Conversations

### List Conversations

```
GET /conversations
```

```python
conversations = client.convai.conversations.list(
    agent_id="agent_xxx",
    page_size=50
)
```

### Get Conversation

```
GET /conversations/{conversation_id}
```

```python
conversation = client.convai.conversations.get(
    conversation_id="conv_xxx"
)
print(conversation.transcript)
print(conversation.analysis)
```

### Get Conversation Audio

```
GET /conversations/{conversation_id}/audio
```

```python
audio = client.convai.conversations.get_audio(
    conversation_id="conv_xxx"
)
with open("conversation.mp3", "wb") as f:
    f.write(audio)
```

## Knowledge Base

### Create Document

```
POST /agents/{agent_id}/knowledge-base
```

**From URL**:
```python
doc = client.convai.agent_knowledge_base.create(
    agent_id="agent_xxx",
    url="https://docs.example.com/faq",
    name="FAQ Documentation"
)
```

**From File**:
```python
with open("manual.pdf", "rb") as f:
    doc = client.convai.agent_knowledge_base.create(
        agent_id="agent_xxx",
        file=f,
        name="Product Manual"
    )
```

### List Documents

```
GET /agents/{agent_id}/knowledge-base
```

```python
docs = client.convai.agent_knowledge_base.list(agent_id="agent_xxx")
```

### Delete Document

```
DELETE /agents/{agent_id}/knowledge-base/{document_id}
```

```python
client.convai.agent_knowledge_base.delete(
    agent_id="agent_xxx",
    document_id="doc_xxx"
)
```

## Phone Numbers

### List Phone Numbers

```
GET /phone-numbers
```

```python
numbers = client.convai.phone_numbers.list()
```

### Get Phone Number

```
GET /phone-numbers/{phone_number_id}
```

```python
number = client.convai.phone_numbers.get(phone_number_id="phone_xxx")
```

### Create (Import) Phone Number

```
POST /phone-numbers
```

**Twilio**:
```python
number = client.convai.phone_numbers.create(
    provider="twilio",
    phone_number="+1234567890",
    label="Support Line",
    twilio_config={
        "account_sid": "ACxxx",
        "auth_token": "xxx"
    }
)
```

**SIP Trunk**:
```python
number = client.convai.phone_numbers.create(
    provider="sip",
    phone_number="+1234567890",
    label="PBX Line",
    sip_config={
        "address": "sip.provider.com",
        "transport": "tls",
        "username": "user",
        "password": "pass"
    }
)
```

### Update Phone Number

```
PATCH /phone-numbers/{phone_number_id}
```

```python
client.convai.phone_numbers.update(
    phone_number_id="phone_xxx",
    agent_id="agent_xxx"  # Assign agent
)
```

## Outbound Calls

### Twilio Outbound Call

```
POST /twilio/outbound_call
```

```python
call = client.convai.twilio.outbound_call(
    agent_id="agent_xxx",
    agent_phone_number_id="phone_xxx",
    to_number="+1987654321",
    conversation_initiation_client_data={
        "customer_id": "cust_123",
        "context": "Follow-up call"
    }
)
print(call.conversation_id)
```

## WebSocket Connection

For real-time conversations:

```
wss://api.elevenlabs.io/v1/convai/conversation
```

**Connection Parameters**:
- `agent_id`: Your agent ID
- `xi-api-key`: API key (for authenticated agents)

**Events**:
- `conversation_initiation_metadata`: Connection established
- `audio`: Audio chunk from agent
- `user_transcript`: Transcribed user speech
- `agent_response`: Text of agent response
- `interruption`: User interrupted agent

## Signed URLs

Generate secure URLs for client-side connections:

```
GET /agents/{agent_id}/link
```

```python
link = client.convai.agents.get_link(agent_id="agent_xxx")
# Use link.signed_url in client SDK
```

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Invalid API key |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 422 | Unprocessable Entity - Validation error |
| 429 | Too Many Requests - Rate limited |
| 500 | Internal Server Error |

## Rate Limits

- Standard tier: 100 requests/minute
- Enterprise tier: Custom limits

Rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640000000
```

## SDKs

**Python**:
```bash
pip install elevenlabs
```

**TypeScript/JavaScript**:
```bash
npm install @11labs/client
```

**React**:
```bash
npm install @11labs/react
```
