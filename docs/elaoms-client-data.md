# ELAOMS Client-Data Webhook

A comprehensive guide to the client-data webhook in the ElevenLabs OpenMemory Integration system.

---

## Table of Contents

- [Overview](#overview)
- [Endpoint Details](#endpoint-details)
- [Request Payload](#request-payload)
- [Processing Flow](#processing-flow)
- [OpenMemory Integration](#openmemory-integration)
- [Response Structure](#response-structure)
- [Dynamic Variables](#dynamic-variables)
- [Conversation Config Override](#conversation-config-override)
- [Error Handling](#error-handling)
- [Configuration](#configuration)
- [Testing](#testing)

---

## Overview

The client-data webhook is called by ElevenLabs when a conversation is initiated (e.g., when a phone call comes in). Its purpose is to:

1. **Identify the caller** using their phone number
2. **Query OpenMemory** for the caller's profile and history
3. **Return personalized data** including dynamic variables and a custom greeting
4. **Enable personalized experiences** for returning callers

This webhook enables the "memory" aspect of ELAOMS, allowing the AI agent to recognize and personalize conversations for returning callers.

### When This Webhook Is Called

```
Caller dials phone number
         ↓
    Twilio receives call
         ↓
    ElevenLabs Agent triggered
         ↓
    POST /webhook/client-data ←── This webhook
         ↓
    Agent uses returned data for personalization
         ↓
    Conversation begins
```

---

## Endpoint Details

| Property | Value |
|----------|-------|
| **URL** | `POST /webhook/client-data` |
| **Authentication** | None (webhook called from ElevenLabs infrastructure) |
| **Content-Type** | `application/json` |
| **Timeout** | Should respond within 5 seconds |

### Full URL Example

```
https://your-server.com/webhook/client-data
```

---

## Request Payload

ElevenLabs sends a JSON payload containing information about the incoming call.

### Request Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `caller_id` | string | Yes | Phone number of the caller in E.164 format |
| `agent_id` | string | Yes | Unique identifier of the ElevenLabs agent |
| `called_number` | string | Yes | The phone number that was called (Twilio number) |
| `call_sid` | string | Yes | Unique identifier for the Twilio call session |

### Example Request

```http
POST /webhook/client-data HTTP/1.1
Host: your-server.com
Content-Type: application/json
User-Agent: ElevenLabs/1.0
Accept: */*

{
  "caller_id": "+16129782029",
  "agent_id": "agent_8501k9r8sbb5fjbbym8c9y1jqt9b",
  "called_number": "+16123241623",
  "call_sid": "CA841665fa7c0d67dcbe339174e89be679"
}
```

### Request Headers from ElevenLabs

| Header | Example Value | Description |
|--------|---------------|-------------|
| `Content-Type` | `application/json` | Always JSON |
| `User-Agent` | `ElevenLabs/1.0` | ElevenLabs user agent |
| `Accept` | `*/*` | Accepts any response format |
| `Accept-Encoding` | `gzip, deflate, br` | Compression support |
| `X-Forwarded-For` | `34.59.11.47` | Original requester IP |
| `X-Api-Key` | `W7WWH...` | Optional API key if configured |

### Phone Number Validation

Both `caller_id` and `called_number` must be in **E.164 format**:

- Starts with `+`
- Followed by country code
- Followed by subscriber number
- Maximum 15 digits total

**Valid examples:**
- `+16129782029` (US number)
- `+442071234567` (UK number)
- `+33612345678` (France number)

**Invalid examples:**
- `6129782029` (missing `+`)
- `+1-612-978-2029` (contains dashes)
- `+1 612 978 2029` (contains spaces)

---

## Processing Flow

The webhook handler (`app/webhooks/client_data.py`) follows this sequence:

```
┌─────────────────────────────────────────────────────────────┐
│                  1. RECEIVE REQUEST                         │
│  Parse ClientDataRequest from JSON body                     │
│  Extract caller_id (phone number)                           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                 2. QUERY OPENMEMORY                         │
│  Call get_user_profile(phone_number)                        │
│  Query: "user profile information preferences name"         │
│  Filter: {"user_id": phone_number}                          │
└─────────────────────────────────────────────────────────────┘
                              ↓
              ┌───────────────┴───────────────┐
              ↓                               ↓
┌─────────────────────────┐     ┌─────────────────────────┐
│   PROFILE FOUND         │     │   NO PROFILE (NEW)      │
│   (Returning Caller)    │     │   (First-time Caller)   │
└─────────────────────────┘     └─────────────────────────┘
              ↓                               ↓
┌─────────────────────────┐     ┌─────────────────────────┐
│ 3a. BUILD RESPONSE      │     │ 3b. BUILD EMPTY RESPONSE│
│ - Extract name          │     │ - Empty dynamic_vars    │
│ - Build summary         │     │ - No config override    │
│ - Get last call context │     │                         │
│ - Create first_message  │     │                         │
└─────────────────────────┘     └─────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   4. RETURN JSON RESPONSE                   │
│  {"dynamic_variables": {...}, "conversation_config_override": {...}}│
└─────────────────────────────────────────────────────────────┘
```

### Code Implementation

```python
# app/webhooks/client_data.py

@router.post("/client-data")
async def client_data_webhook(request: ClientDataRequest) -> JSONResponse:
    phone_number = request.caller_id

    # Query OpenMemory for user profile (async)
    profile = await get_user_profile(phone_number)

    # Build response
    response_data = {}

    # Build dynamic variables
    dynamic_vars = build_dynamic_variables(profile)
    dv_dict = {}
    if dynamic_vars.user_name:
        dv_dict["user_name"] = dynamic_vars.user_name
    if dynamic_vars.user_profile_summary:
        dv_dict["user_profile_summary"] = dynamic_vars.user_profile_summary
    if dynamic_vars.last_call_summary:
        dv_dict["last_call_summary"] = dynamic_vars.last_call_summary

    response_data["dynamic_variables"] = dv_dict

    # Build conversation config override (personalized greeting)
    conversation_override = build_conversation_override(profile)
    if conversation_override and conversation_override.agent:
        response_data["conversation_config_override"] = {
            "agent": {
                "first_message": conversation_override.agent.first_message
            }
        }

    return JSONResponse(content=response_data)
```

---

## OpenMemory Integration

The webhook queries OpenMemory to retrieve the caller's profile using their phone number as the unique identifier.

### Query Request to OpenMemory

```http
POST http://localhost:8080/memory/query
Authorization: Bearer {OPENMEMORY_KEY}
Content-Type: application/json

{
  "query": "user profile information preferences name",
  "k": 20,
  "filters": {
    "user_id": "+16129782029"
  }
}
```

### OpenMemory Response Structure

```json
{
  "matches": [
    {
      "content": "User's name is Stefan",
      "salience": 0.95,
      "primary_sector": "semantic",
      "metadata": {
        "name": "Stefan"
      }
    },
    {
      "content": "User called about account setup on November 28",
      "salience": 0.8,
      "primary_sector": "episodic"
    }
  ]
}
```

### Profile Building

The profile builder (`app/memory/profiles.py`) extracts:

1. **Name**: From memory content or metadata
2. **Summary**: Built from top 3 highest-salience memories
3. **Last Call Summary**: From most recent episodic memory

```python
profile = {
    "name": "Stefan",
    "summary": "User's name is Stefan. Called about account setup.",
    "memories": [...],
    "memory_count": 5,
    "phone_number": "+16129782029"
}
```

---

## Response Structure

The webhook returns a JSON response with two main sections:

### Response Schema

```json
{
  "dynamic_variables": {
    "user_name": "string | null",
    "user_profile_summary": "string | null",
    "last_call_summary": "string | null"
  },
  "conversation_config_override": {
    "agent": {
      "first_message": "string"
    }
  }
}
```

### Example Response: Returning Caller

```json
{
  "dynamic_variables": {
    "user_name": "Stefan",
    "user_profile_summary": "User's name is Stefan. Regular caller interested in product support.",
    "last_call_summary": "Previous conversation: User called about account setup on November 28..."
  },
  "conversation_config_override": {
    "agent": {
      "first_message": "Hello Stefan, it's Margaret again. It's so lovely to hear from you. I've been thinking about our last conversation. Previous conversation: User called about account setup... I'd love to pick up where we left off, or explore a new chapter of your story. What feels right to you today?"
    }
  }
}
```

### Example Response: New Caller

```json
{
  "dynamic_variables": {}
}
```

For new callers:
- `dynamic_variables` is an empty object `{}`
- `conversation_config_override` is **omitted** (not present)
- ElevenLabs uses default agent greeting

---

## Dynamic Variables

Dynamic variables are injected into the ElevenLabs agent's context and can be referenced in the agent's system prompt.

### Available Variables

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `user_name` | string | Caller's name | `"Stefan"` |
| `user_profile_summary` | string | Profile summary | `"Regular caller..."` |
| `last_call_summary` | string | Last conversation context | `"Called about..."` |

### Using in Agent Prompt

Reference dynamic variables in your ElevenLabs agent's system prompt:

```
You are Margaret, a friendly assistant.

{{#if user_name}}
The caller's name is {{user_name}}.
Their profile: {{user_profile_summary}}
Last interaction: {{last_call_summary}}
{{else}}
This is a new caller. Start by asking their name.
{{/if}}
```

### How Variables Are Built

```python
# app/memory/profiles.py

def build_dynamic_variables(profile: Optional[dict]) -> DynamicVariables:
    if profile is None:
        return DynamicVariables(
            user_name=None,
            user_profile_summary=None,
            last_call_summary=None
        )

    return DynamicVariables(
        user_name=profile.get("name"),
        user_profile_summary=profile.get("summary"),
        last_call_summary=_get_last_call_summary(profile.get("memories", []))
    )
```

---

## Conversation Config Override

The conversation config override allows customizing the agent's behavior for specific callers, primarily the initial greeting message.

### Override Structure

```json
{
  "conversation_config_override": {
    "agent": {
      "first_message": "Custom greeting message here"
    }
  }
}
```

### Personalized Greeting Logic

The greeting is built based on available context:

| Available Data | Greeting Template |
|----------------|-------------------|
| Name + Last Call | `"Hello {name}, it's Margaret again... I've been thinking about our last conversation. {last_call}..."` |
| Name + Summary | `"Hello {name}, it's Margaret. I remember {summary}..."` |
| Name only | `"Hello {name}, it's Margaret again. It's so good to hear your voice..."` |
| Profile (no name) | `"Hello, it's Margaret. Welcome back..."` |
| No profile | No override (use default greeting) |

### Implementation

```python
# app/memory/profiles.py

def build_conversation_override(profile: Optional[dict]) -> Optional[ConversationConfigOverride]:
    if profile is None:
        return None  # Use ElevenLabs default greeting

    name = profile.get("name")
    summary = profile.get("summary")
    last_call = _get_last_call_summary(profile.get("memories", []))

    if name and last_call:
        first_message = (
            f"Hello {name}, it's Margaret again. It's so lovely to hear from you. "
            f"I've been thinking about our last conversation. {last_call} "
            "I'd love to pick up where we left off..."
        )
    elif name and summary:
        first_message = (
            f"Hello {name}, it's Margaret. How wonderful to speak with you again. "
            f"I remember {summary[:100]}..."
        )
    # ... more cases

    return ConversationConfigOverride(
        agent=AgentConfig(first_message=first_message)
    )
```

---

## Error Handling

The webhook is designed to be resilient and never block a conversation from starting.

### Error Response

On any error, the webhook returns an empty response:

```json
{
  "dynamic_variables": {}
}
```

This allows:
- The conversation to proceed normally
- ElevenLabs to use default agent configuration
- No blocking of the caller experience

### Error Scenarios

| Scenario | Behavior |
|----------|----------|
| OpenMemory unavailable | Return empty, log error |
| OpenMemory timeout | Return empty after 10s timeout |
| Invalid phone format | HTTP 422 validation error |
| Malformed JSON | HTTP 422 validation error |
| Internal error | Return empty, log error |

### Logging

All requests and errors are logged:

```
INFO: Client-data webhook called for caller: +16129782029
INFO: Found profile for caller +16129782029: Stefan
INFO: Returning client-data response: {...}
```

```
ERROR: Error processing client-data webhook: Connection timeout
ERROR: HTTP error querying OpenMemory for +16129782029: ...
```

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENMEMORY_KEY` | Yes | API key for OpenMemory authentication |
| `OPENMEMORY_PORT` | Yes | OpenMemory service URL or port |

### Configuration in ElevenLabs

Configure the client-data webhook in your ElevenLabs agent:

```json
{
  "platform_settings": {
    "workspace_overrides": {
      "conversation_initiation_client_data_webhook": {
        "url": "https://your-server.com/webhook/client-data",
        "request_headers": {
          "Authorization": "Bearer YOUR_WEBHOOK_SECRET"
        }
      }
    },
    "overrides": {
      "enable_conversation_initiation_client_data_from_webhook": true
    }
  }
}
```

---

## Testing

### Test with cURL

**Simulate a returning caller:**

```bash
curl -X POST http://localhost:8000/webhook/client-data \
  -H "Content-Type: application/json" \
  -d '{
    "caller_id": "+16129782029",
    "agent_id": "agent_8501k9r8sbb5fjbbym8c9y1jqt9b",
    "called_number": "+16123241623",
    "call_sid": "CA841665fa7c0d67dcbe339174e89be679"
  }'
```

**Simulate a new caller:**

```bash
curl -X POST http://localhost:8000/webhook/client-data \
  -H "Content-Type: application/json" \
  -d '{
    "caller_id": "+19998887777",
    "agent_id": "agent_8501k9r8sbb5fjbbym8c9y1jqt9b",
    "called_number": "+16123241623",
    "call_sid": "CA98d2b6a08ebed6b78880b61ffc0e3290"
  }'
```

### Unit Tests

Located in `tests/test_webhooks.py`:

```python
def test_client_data_returns_profile_for_known_caller():
    """Test POST /webhook/client-data returns profile for known caller."""
    mock_profile = {
        "name": "Stefan",
        "summary": "Returning caller interested in support.",
        "memories": [{"content": "User's name is Stefan", "salience": 0.9}],
        "memory_count": 1,
        "phone_number": "+16129782029"
    }

    with patch("app.webhooks.client_data.get_user_profile", return_value=mock_profile):
        response = client.post("/webhook/client-data", json=request_data)

        assert response.status_code == 200
        assert response.json()["dynamic_variables"]["user_name"] == "Stefan"

def test_client_data_returns_empty_for_new_caller():
    """Test POST /webhook/client-data returns empty for new caller."""
    with patch("app.webhooks.client_data.get_user_profile", return_value=None):
        response = client.post("/webhook/client-data", json=request_data)

        assert response.status_code == 200
        assert response.json().get("conversation_config_override") is None
```

### Run Tests

```bash
pytest tests/test_webhooks.py -v -k "client_data"
```

---

## Related Files

| File | Description |
|------|-------------|
| `app/webhooks/client_data.py` | Webhook handler implementation |
| `app/models/requests.py` | `ClientDataRequest` model |
| `app/models/responses.py` | `DynamicVariables`, `ConversationConfigOverride` models |
| `app/memory/profiles.py` | Profile building functions |
| `app/config.py` | Configuration and settings |
| `tests/test_webhooks.py` | Unit tests |
| `payloads/client_data.json` | Sample request payload |
| `tests/fixtures/client_data_request.json` | Test fixture |

---

## See Also

- [ElevenLabs Agent Configuration Guide](./elevenlabs-agent-configuration-guide.md)
- [Cloud Deployment Guide](./cloud-deployment-guide.md)
- [Data Model ERD](./data-model-erd.md)
