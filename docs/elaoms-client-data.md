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
- [Data Transformations](#data-transformations)
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
│  Step 1: GET /users/{encoded_phone}/summary                 │
│  Step 2: POST /memory/query for name extraction             │
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
│ - Get top_content       │     │ - No config override    │
│ - Filter filler content │     │                         │
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
    logger.info(f"Client-data webhook called for caller: {phone_number}")

    try:
        # Query OpenMemory for user profile (async)
        profile = await get_user_profile(phone_number)

        if profile:
            logger.info(f"Found profile for caller {phone_number}: {profile.get('name', 'Unknown')}")
        else:
            logger.info(f"No profile found for new caller {phone_number}")

        # Build response - exclude None values
        response_data: dict[str, Any] = {}

        # Build dynamic variables (only include non-null values)
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

        logger.info(f"Returning client-data response: {response_data}")
        return JSONResponse(content=response_data)

    except Exception as e:
        logger.error(f"Error processing client-data webhook: {e}", exc_info=True)
        # Return empty response on error to allow conversation to proceed
        return JSONResponse(content={"dynamic_variables": {}})
```

---

## OpenMemory Integration

The webhook queries OpenMemory using a two-step process to retrieve the caller's profile.

### Step 1: User Summary Request

```http
GET http://localhost:8080/users/%2B16129782029/summary
Authorization: Bearer {OPENMEMORY_KEY}
Content-Type: application/json
```

**Note:** The phone number is URL-encoded (`+` becomes `%2B`).

#### Summary Response Format

```json
{
  "user_id": "+16129782029",
  "summary": "5 memories, 3 patterns | medium | avg_sal=0.72 | top: semantic(2, sal=0.85): \"founder of Arbez, interested in AI technology...\"",
  "reflection_count": 2,
  "updated_at": 1764853457629
}
```

The summary string is parsed to extract:
- **memory_count**: Number of memories (e.g., `5`)
- **activity_level**: `low`, `medium`, or `high`
- **top_content**: Content in quotes after `top:` (filtered for conversational filler)

### Step 2: Memory Query for Name Extraction

```http
POST http://localhost:8080/memory/query
Authorization: Bearer {OPENMEMORY_KEY}
Content-Type: application/json

{
  "query": "user name first_name",
  "k": 10,
  "filters": {
    "user_id": "+16129782029"
  }
}
```

#### Memory Query Response

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

### Profile Building Result

The combined data produces a profile structure:

```python
profile = {
    "name": "Stefan",                    # Extracted from memories
    "summary": "founder of Arbez...",    # From top_content (cleaned)
    "top_content": "founder of Arbez...",
    "memories": [...],                   # Raw memory matches
    "memory_count": 5,                   # Total memories
    "has_memories": True,
    "activity_level": "medium",          # low/medium/high
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

### Example Response: Returning Caller (Name + Content)

```json
{
  "dynamic_variables": {
    "user_name": "Stefan",
    "user_profile_summary": "founder of Arbez, interested in AI technology",
    "last_call_summary": "Last time we talked about: account setup and integration requirements."
  },
  "conversation_config_override": {
    "agent": {
      "first_message": "Hello Stefan, it's Margaret. Welcome back! Last time you shared about founder of Arbez, interested in AI technology. I'd love to continue that story - what feels right to explore today?"
    }
  }
}
```

### Example Response: Returning Caller (Name Only)

```json
{
  "dynamic_variables": {
    "user_name": "Stefan"
  },
  "conversation_config_override": {
    "agent": {
      "first_message": "Hello Stefan, it's Margaret again. It's so good to hear your voice. I'm looking forward to continuing our journey through your life stories. What would you like to share today?"
    }
  }
}
```

### Example Response: Returning Caller (Content Only, No Name)

```json
{
  "dynamic_variables": {
    "user_profile_summary": "discussed product support issues"
  },
  "conversation_config_override": {
    "agent": {
      "first_message": "Hello, it's Margaret. Welcome back! Last time you shared about discussed product support issues - I'd love to hear more. By the way, I don't think I caught your name last time?"
    }
  }
}
```

### Example Response: Returning Caller (No Name, No Content)

```json
{
  "dynamic_variables": {},
  "conversation_config_override": {
    "agent": {
      "first_message": "Hello, it's Margaret. Welcome back - it's lovely to hear from you again. Before we continue, I don't think I caught your name last time?"
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
| `user_profile_summary` | string | Profile summary from top content | `"founder of Arbez..."` |
| `last_call_summary` | string | Last conversation context | `"Last time we talked about..."` |

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

### Personalized Greeting Logic (4 Cases)

The greeting is built based on available context:

| Condition | Greeting Template |
|-----------|-------------------|
| **Name + Content** | `"Hello {name}, it's Margaret. Welcome back! Last time you shared about {content}. I'd love to continue that story - what feels right to explore today?"` |
| **Name only** | `"Hello {name}, it's Margaret again. It's so good to hear your voice. I'm looking forward to continuing our journey through your life stories. What would you like to share today?"` |
| **Content only (no name)** | `"Hello, it's Margaret. Welcome back! Last time you shared about {content} - I'd love to hear more. By the way, I don't think I caught your name last time?"` |
| **No name + no content** | `"Hello, it's Margaret. Welcome back - it's lovely to hear from you again. Before we continue, I don't think I caught your name last time?"` |
| **No profile (new caller)** | No override returned (use ElevenLabs default greeting) |

### Implementation

```python
# app/memory/profiles.py

def build_conversation_override(profile: Optional[dict]) -> Optional[ConversationConfigOverride]:
    if profile is None:
        # New caller - return None to use ElevenLabs defaults
        return None

    name = profile.get("name")
    top_content = profile.get("top_content")

    # Validate content is meaningful before using it
    has_content = (
        top_content
        and len(top_content) > 10
        and not _is_conversational_filler(top_content)
    )

    # Clean up content for natural speech if available
    if has_content:
        clean_content = _truncate_at_sentence(top_content, max_length=100) or top_content[:100]
    else:
        clean_content = None

    # Build a personalized greeting based on available context
    if name and has_content:
        # Case 1: Has name + has content - full personalization
        first_message = (
            f"Hello {name}, it's Margaret. Welcome back! "
            f"Last time you shared about {clean_content}. "
            "I'd love to continue that story - what feels right to explore today?"
        )
    elif name:
        # Case 2: Has name + no content - simple greeting with name
        first_message = (
            f"Hello {name}, it's Margaret again. It's so good to hear your voice. "
            "I'm looking forward to continuing our journey through your life stories. "
            "What would you like to share today?"
        )
    elif has_content:
        # Case 3: No name + has content - reference content + ask for name
        first_message = (
            f"Hello, it's Margaret. Welcome back! "
            f"Last time you shared about {clean_content} - I'd love to hear more. "
            "By the way, I don't think I caught your name last time?"
        )
    else:
        # Case 4: No name + no content - generic returning caller + ask for name
        first_message = (
            "Hello, it's Margaret. Welcome back - it's lovely to hear from you again. "
            "Before we continue, I don't think I caught your name last time?"
        )

    return ConversationConfigOverride(
        agent=AgentConfig(first_message=first_message)
    )
```

---

## Data Transformations

The webhook applies several transformations to ensure clean, natural-sounding content.

### Name Extraction

Names are extracted from memories by searching for patterns:

```python
name_keywords = ["name is", "my name is", "called", "i'm", "i am"]
```

Also checks memory metadata for `name` or `first_name` fields.

### Conversational Filler Filtering

Content is filtered to remove raw transcript artifacts that would sound awkward:

```python
filler_patterns = [
    # Conversational fillers
    "you know", "um", "uh", "okay", "ok", "great", "yeah", "yep",
    "right", "sure", "well", "so", "like", "actually",
    # Meta-commentary and session notes
    "session quality", "surface-level", "moderate", "rich",
    "chapters discussed", "stories shared", "emotional moments",
    # Agent speech patterns
    "can you tell me", "tell me about", "that's wonderful",
    # Short affirmations
    "yes", "no", "maybe", "i see", "i understand",
]
```

### Sentence Truncation

Long content is truncated at natural boundaries:

1. **Sentence endings** (`. `, `! `, `? `) - preferred
2. **Comma boundaries** - fallback
3. **Word boundaries with ellipsis** - last resort

```python
def _truncate_at_sentence(text: str, max_length: int = 150) -> Optional[str]:
    if len(text) <= max_length:
        return text

    # Look for sentence endings
    truncated = text[:max_length]
    for ending in [". ", "! ", "? "]:
        pos = truncated.rfind(ending)
        if pos > 20:
            return truncated[:pos + 1].strip()

    # Fallback to comma
    comma_pos = truncated.rfind(", ")
    if comma_pos > 30:
        return truncated[:comma_pos].strip()

    # Last resort: word boundary with ellipsis
    space_pos = truncated.rfind(" ")
    if space_pos > 30:
        return truncated[:space_pos].strip() + "..."
```

### Last Call Summary

Extracted from episodic memories with the format:

```
"Last time we talked about: {content}"
```

Only meaningful content is included (conversational filler is filtered out).

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
| OpenMemory timeout (10s) | Return empty after timeout |
| User not found (404) | Return empty (new caller) |
| Invalid phone format | HTTP 422 validation error |
| Malformed JSON | HTTP 422 validation error |
| Internal error | Return empty, log error |

### Logging Examples

**Successful request:**
```
INFO: Client-data webhook called for caller: +16129782029
INFO: Found profile for caller +16129782029: Stefan
INFO: Returning client-data response: {"dynamic_variables": {"user_name": "Stefan"}, ...}
```

**New caller:**
```
INFO: Client-data webhook called for caller: +19998887777
INFO: No profile found for new caller +19998887777
INFO: Returning client-data response: {"dynamic_variables": {}}
```

**Error:**
```
ERROR: Error processing client-data webhook: Connection timeout
ERROR: HTTP error querying OpenMemory for +16129782029: ReadTimeout
```

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENMEMORY_KEY` | Yes | API key for OpenMemory authentication |
| `OPENMEMORY_PORT` | Yes | OpenMemory service URL or port number |

### OpenMemory URL Resolution

The `OPENMEMORY_PORT` value is resolved to a full URL:

```python
@property
def openmemory_url(self) -> str:
    port = self.OPENMEMORY_PORT
    if port.startswith("http://") or port.startswith("https://"):
        return port  # Already a full URL
    return f"http://localhost:{port}"  # Port number only
```

**Examples:**
- `OPENMEMORY_PORT=8080` → `http://localhost:8080`
- `OPENMEMORY_PORT=https://api.openmemory.io` → `https://api.openmemory.io`

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
        "top_content": "founder of Arbez",
        "memories": [{"content": "User's name is Stefan", "salience": 0.9}],
        "memory_count": 1,
        "has_memories": True,
        "activity_level": "medium",
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
| `app/memory/profiles.py` | Profile building and transformation functions |
| `app/config.py` | Configuration and settings |
| `tests/test_webhooks.py` | Unit tests |
| `payloads/client_data.json` | Sample request payload |

---

## Sequence Diagram

```
┌─────────┐          ┌─────────────┐          ┌────────────┐          ┌────────────┐
│ Caller  │          │  Twilio     │          │ ElevenLabs │          │   ELAOMS   │
└────┬────┘          └──────┬──────┘          └─────┬──────┘          └─────┬──────┘
     │                      │                       │                       │
     │  Dial +16123241623   │                       │                       │
     │─────────────────────>│                       │                       │
     │                      │                       │                       │
     │                      │  Trigger Agent        │                       │
     │                      │──────────────────────>│                       │
     │                      │                       │                       │
     │                      │                       │  POST /webhook/client-data
     │                      │                       │──────────────────────>│
     │                      │                       │                       │
     │                      │                       │                       │ Query OpenMemory
     │                      │                       │                       │ ─────────────────┐
     │                      │                       │                       │                  │
     │                      │                       │                       │<─────────────────┘
     │                      │                       │                       │
     │                      │                       │  {dynamic_variables,  │
     │                      │                       │   config_override}    │
     │                      │                       │<──────────────────────│
     │                      │                       │                       │
     │                      │                       │ Use personalized      │
     │                      │                       │ greeting              │
     │                      │                       │                       │
     │  "Hello Stefan..."   │                       │                       │
     │<─────────────────────────────────────────────│                       │
     │                      │                       │                       │
```

---

## See Also

- [ElevenLabs Agent Configuration Guide](./elevenlabs-agent-configuration-guide.md)
- [ELAOMS Post-Call Webhook](./elaoms-post-call.md)
- [ELAOMS Search-Data Webhook](./elaoms-search-data.md)
- [Cloud Deployment Guide](./cloud-deployment-guide.md)
- [Data Model ERD](./data-model-erd.md)
