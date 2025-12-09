# ELAOMS Search-Data Webhook Documentation

This document provides a complete technical reference for the `search-data` webhook in the ElevenLabs OpenMemory Service (ELAOMS).

## Overview

The search-data webhook enables **mid-conversation memory retrieval** for ElevenLabs conversational AI agents. When an agent needs to recall information about a caller during an active conversation, it invokes this webhook to query the OpenMemory database.

### Key Characteristics

- **Endpoint**: `POST /webhook/search-data`
- **Authentication**: No HMAC signature required (unlike post-call webhook)
- **Purpose**: Real-time memory search during active conversations
- **Data Source**: OpenMemory API (semantic vector search)
- **Multi-tenant**: Uses phone numbers (`user_id`) for data isolation

---

## Architecture Flow

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   ElevenLabs     │     │     ELAOMS       │     │   OpenMemory     │
│   AI Agent       │     │   Webhook        │     │   Service        │
└────────┬─────────┘     └────────┬─────────┘     └────────┬─────────┘
         │                        │                        │
         │  POST /webhook/        │                        │
         │  search-data           │                        │
         │ ───────────────────────>                        │
         │                        │                        │
         │                        │  POST /memory/query    │
         │                        │ ───────────────────────>
         │                        │                        │
         │                        │  { matches: [...] }    │
         │                        │ <───────────────────────
         │                        │                        │
         │  { profile, memories } │                        │
         │ <───────────────────────                        │
         │                        │                        │
```

---

## Request Format

### Endpoint

```
POST /webhook/search-data
Content-Type: application/json
```

### Request Model: `SearchDataRequest`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | `string` | Yes | The search query from the ElevenLabs agent |
| `user_id` | `string` | Yes | Phone number in E.164 format (e.g., `+16129782029`) |
| `agent_id` | `string` | Yes | The ElevenLabs agent identifier |
| `conversation_id` | `string` | No | Current conversation identifier |
| `context` | `object` | No | Additional context (e.g., `current_topic`, `call_duration_secs`) |

### Validation Rules

- **`user_id`** must be in E.164 phone format:
  - Starts with `+`
  - Followed by country code and digits
  - Max 15 digits total
  - Pattern: `^\+[1-9]\d{1,14}$`

### Example Request

```json
{
  "query": "What is the user's name and preferences?",
  "user_id": "+16129782029",
  "agent_id": "agent_8501k9r8sbb5fjbbym8c9y1jqt9b",
  "conversation_id": "conv_8701kb8xfaaney589jkc6pjesxrc",
  "context": {
    "current_topic": "user inquiry",
    "call_duration_secs": 15
  }
}
```

### cURL Example

```bash
curl -X POST "https://your-domain.com/webhook/search-data" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the user'\''s name and preferences?",
    "user_id": "+16129782029",
    "agent_id": "agent_8501k9r8sbb5fjbbym8c9y1jqt9b",
    "conversation_id": "conv_8701kb8xfaaney589jkc6pjesxrc"
  }'
```

---

## Response Format

### Response Model: `SearchDataResponse`

| Field | Type | Description |
|-------|------|-------------|
| `profile` | `ProfileData \| null` | User profile information (if found) |
| `memories` | `MemoryItem[]` | Array of relevant memories matching the query |

### ProfileData Structure

| Field | Type | Description |
|-------|------|-------------|
| `name` | `string \| null` | User's name extracted from memories |
| `summary` | `string \| null` | Summary built from high-salience memories |
| `phone_number` | `string \| null` | User's phone number |

### MemoryItem Structure

| Field | Type | Description |
|-------|------|-------------|
| `content` | `string` | The memory content text |
| `sector` | `string` | Memory classification (see Memory Sectors below) |
| `salience` | `float` | Importance score from 0.0 to 1.0 |
| `timestamp` | `datetime \| null` | When the memory was created |

### Memory Sectors

| Sector | Description |
|--------|-------------|
| `semantic` | Factual knowledge (e.g., "User's name is Stefan") |
| `episodic` | Past events (e.g., "Previous call about account setup") |
| `procedural` | How-to knowledge (e.g., "User prefers email contact") |
| `emotional` | Emotional associations |
| `reflective` | Meta-cognitive observations |

### Salience Scores

| Score Range | Meaning | Example |
|-------------|---------|---------|
| `0.9 - 1.0` | High priority profile facts | User's name, phone number |
| `0.7 - 0.89` | Medium priority conversation data | User preferences, recent topics |
| `0.5 - 0.69` | Standard memories | General conversation messages |
| `0.0 - 0.49` | Low priority | Ambient context |

### Example Response (Success)

```json
{
  "profile": {
    "name": "Stefan",
    "summary": "User's name is Stefan. User prefers email contact. Previous call about account setup.",
    "phone_number": "+16129782029"
  },
  "memories": [
    {
      "content": "User's name is Stefan",
      "sector": "semantic",
      "salience": 0.9,
      "timestamp": null
    },
    {
      "content": "User prefers email contact",
      "sector": "semantic",
      "salience": 0.8,
      "timestamp": null
    },
    {
      "content": "Previous call about account setup",
      "sector": "episodic",
      "salience": 0.7,
      "timestamp": null
    }
  ]
}
```

### Example Response (No Memories Found)

```json
{
  "profile": null,
  "memories": []
}
```

### Example Response (Error/Graceful Degradation)

On any error, the webhook returns an empty response rather than failing:

```json
{
  "profile": null,
  "memories": []
}
```

---

## Processing Logic

### Step-by-Step Flow

1. **Extract Parameters**
   ```python
   query = request.query
   phone_number = request.user_id
   ```

2. **Query OpenMemory**
   ```python
   search_result = search_memories(
       query=query,
       phone_number=phone_number,
   )
   ```

3. **Build Profile from Results**
   - Extract `name` from memory metadata where `field == "first_name"`
   - Build `summary` from high-salience memories (salience > 0.7)
   - Include `phone_number` from request

4. **Build Memory Items Array**
   - Map each memory to `MemoryItem` structure
   - Include `content`, `sector`, `salience`

5. **Return Response**
   - Return `SearchDataResponse` with profile and memories
   - On error: return empty response

### OpenMemory Query

The webhook queries OpenMemory using:

```python
payload = {
    "query": query,           # Semantic search query
    "k": 10,                  # Max results (default limit)
    "filters": {
        "user_id": phone_number  # Multi-tenant isolation
    }
}

response = client.post(f"{openmemory_url}/memory/query", json=payload)
```

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENMEMORY_KEY` | Yes | API key for OpenMemory authentication |
| `OPENMEMORY_PORT` | Yes | OpenMemory service URL or port number |
| `ELEVENLABS_SEARCH_DATA_KEY` | No | Reserved for future HMAC validation |

### OpenMemory URL Resolution

```python
# If OPENMEMORY_PORT is a full URL
if port.startswith("http://") or port.startswith("https://"):
    return port  # e.g., "https://api.openmemory.ai"

# Otherwise, treat as localhost port
return f"http://localhost:{port}"  # e.g., "http://localhost:8787"
```

### Example `.env` Configuration

```bash
# OpenMemory Configuration
OPENMEMORY_KEY=your_openmemory_api_key
OPENMEMORY_PORT=8787
OPENMEMORY_DB_PATH=./data/openmemory.db

# ElevenLabs Configuration
ELEVENLABS_API_KEY=your_elevenlabs_key
ELEVENLABS_SEARCH_DATA_KEY=  # Optional, not currently validated
```

---

## Error Handling

The search-data webhook implements **graceful degradation**:

| Error Type | Behavior |
|------------|----------|
| OpenMemory connection failure | Return empty response |
| OpenMemory query error | Return empty response |
| Invalid response format | Return empty response |
| Timeout (10 second limit) | Return empty response |

### Error Response

All errors return HTTP 200 with an empty response body:

```json
{
  "profile": null,
  "memories": []
}
```

This ensures the ElevenLabs agent continues functioning even when memory retrieval fails.

---

## Integration with ElevenLabs

### Agent Configuration

To use the search-data webhook, configure it as a **server tool** in your ElevenLabs agent:

1. Go to your ElevenLabs agent configuration
2. Add a server tool with the webhook URL
3. Configure the tool to pass `user_id`, `query`, and `agent_id`

### Tool Configuration

Add this tool to your agent's tools array. See `examples/tools/search-data-tool.json` for the full configuration.

**Critical Configuration Requirements:**

| Setting | Required Value | Notes |
|---------|----------------|-------|
| Method | `POST` | NOT GET - server expects JSON body |
| Parameters | `request_body_schema` | NOT `query_params_schema` |
| Content-Type | `application/json` | Add as static header |
| Timeout | `10` seconds | Match OpenMemory timeout |

```json
{
  "type": "webhook",
  "name": "search_data",
  "description": "Search memories and profile data for the current caller. Returns profile information (name, summary) and relevant memories from previous conversations.",
  "disable_interruptions": false,
  "force_pre_tool_speech": "auto",
  "assignments": [
    {
      "source": "response",
      "dynamic_variable": "profile",
      "value_path": "profile"
    },
    {
      "source": "response",
      "dynamic_variable": "memories",
      "value_path": "memories"
    }
  ],
  "tool_call_sound": "typing",
  "tool_call_sound_behavior": "auto",
  "execution_mode": "immediate",
  "api_schema": {
    "url": "https://your-webhook-url.com/webhook/search-data",
    "method": "POST",
    "path_params_schema": [],
    "query_params_schema": [],
    "request_body_schema": {
      "id": "body",
      "type": "object",
      "description": "Request body for searching caller memories",
      "properties": [
        {
          "id": "user_id",
          "type": "string",
          "value_type": "dynamic_variable",
          "description": "",
          "dynamic_variable": "system__caller_id",
          "constant_value": "",
          "enum": null,
          "is_system_provided": false,
          "required": true
        },
        {
          "id": "query",
          "type": "string",
          "value_type": "llm_prompt",
          "description": "Natural language search query",
          "dynamic_variable": "",
          "constant_value": "",
          "enum": null,
          "is_system_provided": false,
          "required": true
        },
        {
          "id": "agent_id",
          "type": "string",
          "value_type": "dynamic_variable",
          "description": "",
          "dynamic_variable": "system__agent_id",
          "constant_value": "",
          "enum": null,
          "is_system_provided": false,
          "required": true
        }
      ],
      "required": false,
      "value_type": "llm_prompt"
    },
    "request_headers": [
      {
        "type": "value",
        "name": "Content-Type",
        "value": "application/json"
      },
      {
        "type": "secret",
        "name": "X-Api-Key",
        "secret_id": "YOUR_SECRET_ID"
      }
    ],
    "auth_connection": null
  },
  "response_timeout_secs": 10,
  "dynamic_variables": {
    "dynamic_variable_placeholders": {}
  }
}
```

### System Prompt Integration

Add this section to your agent's system prompt to guide proper tool usage:

```markdown
# Tools

## search_data - Memory Retrieval
Use the search_data tool when you need to:
- Recall the caller's name or personal details
- Reference previous conversation topics
- Personalize responses based on caller history
- Answer questions about past interactions

**How to use:**
1. Formulate a natural language query describing what you want to know
2. Wait for the response containing {{profile}} and {{memories}}
3. Use the returned information naturally in your response

**Query examples:**
- "What is the caller's name and preferences?"
- "What did we discuss in previous calls?"
- "Does the caller have any pending issues?"

**After receiving results:**
- If {{profile.name}} is available, use it to address the caller by name
- Reference {{memories}} to provide continuity with past conversations
- If no memories found, proceed without personalization

**Do NOT use search_data:**
- For general knowledge questions (use your training)
- When caller explicitly starts a new topic
- Multiple times in quick succession for the same query
```

### When It's Called

The webhook is invoked when the ElevenLabs agent:
- Needs to recall information about the caller
- Wants to personalize responses based on history
- Attempts to continue a previous conversation topic

### Creating Tool via API

You can create the tool programmatically using the ElevenLabs API. See `scripts/create_search_data_tool.py` or `scripts/create-search-data-tool.sh`.

**Important:** The API format differs from the Dashboard UI format.

| Feature | Dashboard UI | API |
|---------|-------------|-----|
| Wrapper | None | `tool_config` object |
| `properties` | Array of objects | Object with keys |
| `required` | Boolean per property | Array of field names |
| `request_headers` | Array | Object |
| `path_params_schema` | Required (empty array) | Omit if empty |
| `query_params_schema` | Required (empty array) | Omit if empty |

**API Request:**

```bash
curl -X POST "https://api.elevenlabs.io/v1/convai/tools" \
  -H "xi-api-key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
  "tool_config": {
    "type": "webhook",
    "name": "search_data",
    "description": "Search memories and profile data for the current caller.",
    "api_schema": {
      "url": "https://your-webhook-url.com/webhook/search-data",
      "method": "POST",
      "request_body_schema": {
        "type": "object",
        "description": "Request body for searching caller memories",
        "properties": {
          "user_id": {"type": "string", "description": "Caller phone number in E.164 format"},
          "query": {"type": "string", "description": "Natural language search query"},
          "agent_id": {"type": "string", "description": "ElevenLabs agent ID"}
        },
        "required": ["user_id", "query", "agent_id"]
      },
      "request_headers": {
        "Content-Type": "application/json",
        "X-Api-Key": "{{YOUR_SECRET_ID}}"
      }
    },
    "response_timeout_secs": 10,
    "assignments": [
      {"source": "response", "dynamic_variable": "profile", "value_path": "profile"},
      {"source": "response", "dynamic_variable": "memories", "value_path": "memories"}
    ],
    "tool_call_sound": "typing",
    "execution_mode": "immediate",
    "dynamic_variables": {"dynamic_variable_placeholders": {}}
  }
}'
```

**Using Python Script:**

```bash
# Set API key and run
ELEVENLABS_API_KEY=sk_xxx python scripts/create_search_data_tool.py

# Or with custom webhook URL
python scripts/create_search_data_tool.py --api-key sk_xxx --webhook-url https://your-url.com/webhook/search-data
```

**Using Bash Script:**

```bash
ELEVENLABS_API_KEY=sk_xxx ./scripts/create-search-data-tool.sh
```

---

## Source Code Reference

| File | Description |
|------|-------------|
| `app/webhooks/search_data.py` | Main webhook handler |
| `app/models/requests.py:78-114` | `SearchDataRequest` model |
| `app/models/responses.py:143-157` | `SearchDataResponse` model |
| `app/memory/extraction.py:256-348` | `search_memories()` function |
| `app/config.py` | Configuration management |
| `tests/test_webhooks.py:178-218` | Unit tests |

---

## Testing

### Unit Test Example

```python
def test_search_data_returns_relevant_memories():
    mock_search_result = {
        "profile": {
            "name": "Stefan",
            "summary": "Regular caller",
            "phone_number": "+16129782029"
        },
        "memories": [
            {"content": "User prefers email contact", "sector": "semantic", "salience": 0.8},
            {"content": "Previous call about account setup", "sector": "episodic", "salience": 0.7}
        ]
    }

    with patch("app.webhooks.search_data.search_memories", return_value=mock_search_result):
        client = TestClient(app)

        request_data = {
            "query": "What are the user's preferences?",
            "user_id": "+16129782029",
            "agent_id": "agent_8501k9r8sbb5fjbbym8c9y1jqt9b"
        }

        response = client.post("/webhook/search-data", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["profile"]["name"] == "Stefan"
        assert len(data["memories"]) == 2
```

### Manual Testing

```bash
# Test with valid request
curl -X POST "http://localhost:8000/webhook/search-data" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the user'\''s name?",
    "user_id": "+16129782029",
    "agent_id": "test_agent"
  }'

# Expected response (with memories)
# {"profile": {"name": "Stefan", ...}, "memories": [...]}

# Expected response (no memories)
# {"profile": null, "memories": []}
```

---

## Security Considerations

1. **No HMAC Validation**: Unlike post-call webhook, search-data doesn't require signature validation. Consider adding authentication if exposed publicly.

2. **Multi-tenant Isolation**: Memories are isolated by `user_id` (phone number). The system only returns memories for the specified user.

3. **Input Validation**: Phone numbers are validated against E.164 format to prevent injection attacks.

4. **Timeout Protection**: HTTP requests to OpenMemory have a 10-second timeout to prevent hanging.

---

## Troubleshooting

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| Empty response always | OpenMemory not running | Check `OPENMEMORY_PORT` configuration |
| 422 Validation Error | Invalid phone format | Ensure `user_id` is E.164 format (`+1234567890`) |
| Slow responses | OpenMemory query latency | Check OpenMemory service health |
| Missing profile name | No profile memories stored | Ensure post-call webhook is storing memories |
