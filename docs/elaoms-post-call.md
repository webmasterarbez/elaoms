# ELAOMS Post-Call Webhook Documentation

This document provides a complete technical reference for the post-call webhook implementation in ELAOMS. The post-call webhook receives data from ElevenLabs after a voice conversation ends and processes it for transcription storage and memory extraction.

## Overview

The post-call webhook is an asynchronous endpoint that:
1. Receives webhook payloads from ElevenLabs after calls complete
2. Validates HMAC signatures for security
3. Returns immediately (200 OK) to prevent timeouts
4. Processes payloads in background tasks
5. Saves transcriptions, audio, and failure logs to disk
6. Extracts user information and stores it in OpenMemory

**Endpoint:** `POST /webhook/post-call`

**Source file:** `app/webhooks/post_call.py`

---

## Authentication

### HMAC Signature Verification

All post-call webhooks require HMAC authentication via the `elevenlabs-signature` header.

**Header format:**
```
elevenlabs-signature: t=1764457176,v0=abc123def456...
```

**Components:**
| Part | Description |
|------|-------------|
| `t=` | Unix timestamp when the signature was generated |
| `v0=` | SHA256 HMAC signature hash |

**Signature computation:**
```python
payload = f"{timestamp}.{request_body}"
signature = HMAC-SHA256(secret=ELEVENLABS_POST_CALL_KEY, message=payload)
```

**Validation rules:**
- Timestamp must be within 30 minutes of current time (1800 seconds tolerance)
- Signature is compared using constant-time comparison to prevent timing attacks
- Missing or invalid signatures return `401 Unauthorized`

**Configuration:**
```env
ELEVENLABS_POST_CALL_KEY=your-hmac-secret-key
```

---

## Webhook Types

The post-call webhook handles three distinct payload types:

| Type | Description | Processing |
|------|-------------|------------|
| `post_call_transcription` | Call transcript and metadata | Saves JSON, extracts memories |
| `post_call_audio` | Base64-encoded call audio | Decodes and saves as MP3 |
| `call_initiation_failure` | Failed call information | Saves failure log |

---

## Request Flow

```
ElevenLabs Platform
        │
        ▼
POST /webhook/post-call
        │
        ▼
┌─────────────────────────────┐
│  HMAC Signature Validation  │◄── 401 if invalid
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│  Return 200 Immediately     │
│  {"status": "received"}     │
└─────────────────────────────┘
        │
        ▼ (Background Task)
┌─────────────────────────────┐
│  Parse PostCallWebhookRequest│
└─────────────────────────────┘
        │
        ├── post_call_transcription:
        │   ├── Save transcription JSON
        │   ├── Extract caller phone
        │   ├── Extract user info from analysis
        │   ├── Store profile memories (salience: 0.9)
        │   └── Store conversation memories (salience: 0.7)
        │
        ├── post_call_audio:
        │   ├── Extract base64 audio
        │   ├── Decode base64
        │   └── Save as MP3 file
        │
        └── call_initiation_failure:
            └── Save failure log JSON
```

---

## Payload Structure

### PostCallWebhookRequest

The top-level request structure:

```json
{
  "type": "post_call_transcription",
  "event_timestamp": 1764457176,
  "data": { ... }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | One of: `post_call_transcription`, `post_call_audio`, `call_initiation_failure` |
| `event_timestamp` | integer | Unix timestamp when the event occurred |
| `data` | object | `PostCallData` payload (see below) |

### PostCallData

The main data payload containing conversation details:

```json
{
  "agent_id": "agent_8501k9r8sbb5fjbbym8c9y1jqt9b",
  "conversation_id": "conv_8701kb8xfaaney589jkc6pjesxrc",
  "status": "done",
  "user_id": null,
  "branch_id": null,
  "transcript": [...],
  "metadata": {...},
  "analysis": {...},
  "conversation_initiation_client_data": {...},
  "has_audio": false,
  "has_user_audio": false,
  "has_response_audio": false
}
```

| Field | Type | Description |
|-------|------|-------------|
| `agent_id` | string | Unique identifier for the ElevenLabs agent |
| `conversation_id` | string | Unique identifier for this conversation |
| `status` | string | Call status (e.g., "done") |
| `user_id` | string? | User ID if provided |
| `branch_id` | string? | Branch ID for versioned agents |
| `transcript` | array | List of `TranscriptEntry` objects |
| `metadata` | object | `CallMetadata` with timing, cost, features |
| `analysis` | object | `Analysis` with extracted data and summaries |
| `conversation_initiation_client_data` | object | Client data from call initiation |
| `has_audio` | boolean | Whether audio is available |
| `has_user_audio` | boolean | Whether user audio is available |
| `has_response_audio` | boolean | Whether agent audio is available |

### TranscriptEntry

Individual entries in the conversation transcript:

```json
{
  "role": "user",
  "message": "Stefan.",
  "time_in_call_secs": 4,
  "tool_calls": [],
  "tool_results": [],
  "llm_usage": null,
  "conversation_turn_metrics": {
    "metrics": {
      "convai_asr_trailing_service_latency": {
        "elapsed_time": 0.155
      }
    }
  },
  "interrupted": false,
  "original_message": null,
  "source_medium": "audio",
  "feedback": null,
  "agent_metadata": null
}
```

| Field | Type | Description |
|-------|------|-------------|
| `role` | string | `"agent"` or `"user"` |
| `message` | string? | Text content of the message |
| `time_in_call_secs` | integer | Seconds from call start |
| `tool_calls` | array | Tool invocations during this turn |
| `tool_results` | array | Results from tool calls |
| `llm_usage` | object? | Token usage and cost for this turn |
| `conversation_turn_metrics` | object? | Performance metrics |
| `interrupted` | boolean | Whether the turn was interrupted |
| `source_medium` | string? | Source of the message (e.g., "audio") |
| `agent_metadata` | object? | Agent information for this turn |

### Analysis

Extracted information and evaluation results:

```json
{
  "evaluation_criteria_results": {},
  "data_collection_results": {
    "first_name": {
      "data_collection_id": "first_name",
      "value": "Stefan",
      "json_schema": {
        "type": "string",
        "description": "First name"
      },
      "rationale": "The user states their name is Stefan..."
    }
  },
  "call_successful": "success",
  "transcript_summary": "The agent greets the user...",
  "call_summary_title": "Greeting and Introduction"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `evaluation_criteria_results` | object | Results of custom evaluation criteria |
| `data_collection_results` | object | Extracted data fields with values and rationale |
| `call_successful` | string? | Success status (e.g., "success", "failure") |
| `transcript_summary` | string? | AI-generated summary of the conversation |
| `call_summary_title` | string? | Short title for the call |

### ConversationInitiationClientData

Client data provided when the call was initiated, including system-injected dynamic variables:

```json
{
  "conversation_config_override": null,
  "custom_llm_extra_body": {},
  "user_id": null,
  "source_info": {
    "source": null,
    "version": null
  },
  "dynamic_variables": {
    "system__agent_id": "agent_8501k9r8sbb5fjbbym8c9y1jqt9b",
    "system__caller_id": "+16129782029",
    "system__time_utc": "2025-11-29T22:59:33.797566+00:00",
    "system__call_sid": "CA98d2b6a08ebed6b78880b61ffc0e3299",
    "system__called_number": "+16123241623",
    "system__conversation_id": "conv_8701kb8xfaaney589jkc6pjesxrc",
    "system__call_duration_secs": 10,
    "system__agent_turns": 2
  }
}
```

**Key dynamic variables:**

| Variable | Description |
|----------|-------------|
| `system__caller_id` | Caller's phone number in E.164 format |
| `system__called_number` | Twilio number that was called |
| `system__call_sid` | Twilio call session ID |
| `system__conversation_id` | ElevenLabs conversation ID |
| `system__time_utc` | Call start time in ISO 8601 format |
| `system__call_duration_secs` | Total call duration in seconds |
| `system__agent_turns` | Number of agent turns in the conversation |

### CallMetadata

Detailed call information including timing, costs, and features:

```json
{
  "start_time_unix_secs": 1764457163,
  "end_time_unix_secs": null,
  "call_duration_secs": 10,
  "cost": 70.0,
  "deletion_settings": {...},
  "feedback": {...},
  "authorization_method": "signed_url",
  "phone_call": {
    "type": "twilio",
    "stream_sid": "MZ86eb397c30ae6ccc325b1af798ce829d",
    "call_sid": "CA98d2b6a08ebed6b78880b61ffc0e3299"
  },
  "termination_reason": "Call ended by remote party",
  "main_language": "en",
  "features_usage": {...},
  "conversation_initiation_source": "twilio"
}
```

---

## Complete Payload Example

Below is a complete example of a `post_call_transcription` webhook payload:

```json
{
  "type": "post_call_transcription",
  "event_timestamp": 1764457176,
  "data": {
    "agent_id": "agent_8501k9r8sbb5fjbbym8c9y1jqt9b",
    "conversation_id": "conv_8701kb8xfaaney589jkc6pjesxrc",
    "status": "done",
    "user_id": null,
    "branch_id": null,
    "transcript": [
      {
        "role": "agent",
        "message": "Hello, how are you? What is your name?",
        "time_in_call_secs": 0,
        "tool_calls": [],
        "tool_results": [],
        "llm_usage": null,
        "conversation_turn_metrics": {
          "metrics": {
            "convai_tts_service_ttfb": {
              "elapsed_time": 0.391
            }
          }
        },
        "interrupted": false,
        "source_medium": null,
        "agent_metadata": {
          "agent_id": "agent_8501k9r8sbb5fjbbym8c9y1jqt9b",
          "branch_id": null,
          "workflow_node_id": null
        }
      },
      {
        "role": "user",
        "message": "Stefan.",
        "time_in_call_secs": 4,
        "tool_calls": [],
        "tool_results": [],
        "llm_usage": null,
        "conversation_turn_metrics": {
          "metrics": {
            "convai_asr_trailing_service_latency": {
              "elapsed_time": 0.155
            }
          }
        },
        "interrupted": false,
        "source_medium": "audio"
      },
      {
        "role": "agent",
        "message": "Hello Stefan, nice to meet you. How can I help you today?\n",
        "time_in_call_secs": 5,
        "tool_calls": [],
        "tool_results": [],
        "llm_usage": {
          "model_usage": {
            "gemini-2.0-flash-lite": {
              "input": {
                "tokens": 944,
                "price": 0.0000708
              },
              "output_total": {
                "tokens": 16,
                "price": 0.0000048
              }
            }
          }
        },
        "conversation_turn_metrics": {
          "metrics": {
            "convai_llm_service_ttf_sentence": {
              "elapsed_time": 0.354
            },
            "convai_llm_service_ttfb": {
              "elapsed_time": 0.290
            },
            "convai_tts_service_ttfb": {
              "elapsed_time": 0.463
            }
          }
        },
        "interrupted": false,
        "agent_metadata": {
          "agent_id": "agent_8501k9r8sbb5fjbbym8c9y1jqt9b"
        }
      }
    ],
    "metadata": {
      "start_time_unix_secs": 1764457163,
      "end_time_unix_secs": null,
      "call_duration_secs": 10,
      "cost": 70.0,
      "deletion_settings": {
        "deletion_time_unix_secs": null,
        "delete_transcript_and_pii": false,
        "delete_audio": false
      },
      "feedback": {
        "type": null,
        "overall_score": null,
        "likes": 0,
        "dislikes": 0
      },
      "authorization_method": "signed_url",
      "phone_call": {
        "type": "twilio",
        "stream_sid": "MZ86eb397c30ae6ccc325b1af798ce829d",
        "call_sid": "CA98d2b6a08ebed6b78880b61ffc0e3299"
      },
      "termination_reason": "Call ended by remote party",
      "main_language": "en",
      "features_usage": {
        "language_detection": {"enabled": false, "used": false},
        "transfer_to_agent": {"enabled": false, "used": false},
        "transfer_to_number": {"enabled": false, "used": false},
        "multivoice": {"enabled": false, "used": false},
        "dtmf_tones": {"enabled": false, "used": false},
        "external_mcp_servers": {"enabled": false, "used": false},
        "workflow": {"enabled": false}
      },
      "conversation_initiation_source": "twilio",
      "timezone": "UTC"
    },
    "analysis": {
      "evaluation_criteria_results": {},
      "data_collection_results": {
        "first_name": {
          "data_collection_id": "first_name",
          "value": "Stefan",
          "json_schema": {
            "type": "string",
            "description": "First name"
          },
          "rationale": "The user states their name is Stefan in response to the agent asking for their name."
        },
        "last_name": {
          "data_collection_id": "last_name",
          "value": null,
          "json_schema": {
            "type": "string",
            "description": "Last name"
          },
          "rationale": "The user only provided their first name. No last name was mentioned."
        }
      },
      "call_successful": "success",
      "transcript_summary": "The agent greets the user, asks for their name, and then offers assistance after learning the user's name is Stefan.\n",
      "call_summary_title": "Greeting and Introduction"
    },
    "conversation_initiation_client_data": {
      "conversation_config_override": null,
      "custom_llm_extra_body": {},
      "user_id": null,
      "dynamic_variables": {
        "system__agent_id": "agent_8501k9r8sbb5fjbbym8c9y1jqt9b",
        "system__caller_id": "+16129782029",
        "system__time_utc": "2025-11-29T22:59:33.797566+00:00",
        "system__call_sid": "CA98d2b6a08ebed6b78880b61ffc0e3299",
        "system__called_number": "+16123241623",
        "system__conversation_id": "conv_8701kb8xfaaney589jkc6pjesxrc",
        "system__call_duration_secs": 10,
        "system__agent_turns": 2,
        "system__time": "Saturday, 22:59 29 November 2025",
        "system__timezone": "UTC"
      }
    },
    "has_audio": false,
    "has_user_audio": false,
    "has_response_audio": false
  }
}
```

---

## Storage Structure

Processed payloads are saved to the configured storage path organized by conversation ID:

```
PAYLOAD_STORAGE_PATH/
└── {conversation_id}/
    ├── {conversation_id}_transcription.json   # Full transcription payload
    ├── {conversation_id}_audio.mp3            # Decoded audio (if available)
    ├── {conversation_id}_failure.json         # Failure information
    └── {conversation_id}_error.json           # Processing errors (if any)
```

**Configuration:**
```env
PAYLOAD_STORAGE_PATH=/path/to/storage
```

**Example:**
```
/storage/conv_8701kb8xfaaney589jkc6pjesxrc/
├── conv_8701kb8xfaaney589jkc6pjesxrc_transcription.json
└── conv_8701kb8xfaaney589jkc6pjesxrc_audio.mp3
```

---

## Memory Processing

When a `post_call_transcription` webhook is received, the system automatically extracts information and stores it in OpenMemory.

### Extraction Flow

1. **Extract caller phone number** from `dynamic_variables.system__caller_id`
2. **Extract user info** from `analysis.data_collection_results`
3. **Extract user messages** from `transcript` where `role="user"`
4. **Store profile memories** with high salience (0.9)
5. **Store conversation memories** with medium salience (0.7)

### Memory Types

#### Profile Memories

Extracted user information is stored as semantic memories with high salience:

```json
{
  "content": "User's name is Stefan",
  "tags": ["profile", "first_name"],
  "metadata": {
    "field": "first_name",
    "value": "Stefan",
    "conversation_id": "conv_8701kb8xfaaney589jkc6pjesxrc",
    "timestamp_utc": "2025-11-29T22:59:33.797566+00:00"
  },
  "user_id": "+16129782029",
  "salience": 0.9,
  "decay_lambda": 0
}
```

**Salience:** 0.9 (high importance for quick recall)
**Decay:** 0 (permanent retention)

#### Conversation Memories

Each user utterance is stored as an episodic memory:

```json
{
  "content": "Stefan.",
  "tags": ["conversation", "user_message"],
  "metadata": {
    "message_index": 0,
    "type": "user_utterance",
    "time_in_call_secs": 4,
    "conversation_id": "conv_8701kb8xfaaney589jkc6pjesxrc",
    "timestamp_utc": "2025-11-29T22:59:33.797566+00:00"
  },
  "user_id": "+16129782029",
  "salience": 0.7,
  "decay_lambda": 0
}
```

**Salience:** 0.7 (medium importance)
**Decay:** 0 (permanent retention)

### Multi-tenant Isolation

Memories are isolated by phone number (E.164 format). Each caller's memories are stored with their phone number as the `user_id`, ensuring complete data separation between users.

---

## Response Format

### Success Response

```json
{
  "status": "received",
  "type": "post_call_transcription",
  "conversation_id": "conv_8701kb8xfaaney589jkc6pjesxrc",
  "message": "Webhook received and queued for processing"
}
```

### Error Response (401 Unauthorized)

```json
{
  "detail": "HMAC authentication failed: Invalid signature: computed hash does not match received hash"
}
```

---

## Error Handling

The webhook is designed for resilience:

1. **Immediate response** - Returns 200 to ElevenLabs before processing to prevent timeouts
2. **Background processing** - Heavy I/O operations run asynchronously
3. **Error preservation** - Failed payloads are saved to `{conversation_id}_error.json` for debugging
4. **Graceful degradation** - Memory storage failures don't prevent transcription saving

### Error Payload Format

When processing fails, the raw payload is saved with error details:

```json
{
  "error": "Error message describing what went wrong",
  "payload": { ... original payload ... }
}
```

---

## Configuration Reference

| Environment Variable | Description | Required |
|---------------------|-------------|----------|
| `ELEVENLABS_POST_CALL_KEY` | HMAC secret for signature verification | Yes |
| `PAYLOAD_STORAGE_PATH` | Directory for saving transcriptions/audio | Yes |
| `OPENMEMORY_KEY` | OpenMemory API key | No* |
| `OPENMEMORY_PORT` | OpenMemory server port | No* |

*Required for memory storage functionality

---

## Testing

### Generate Valid HMAC Signature

```python
import hmac
import time
import json
from hashlib import sha256

def generate_signature(payload: dict, secret: str) -> str:
    timestamp = int(time.time())
    body = json.dumps(payload)
    full_payload = f"{timestamp}.{body}"
    signature = hmac.new(
        key=secret.encode("utf-8"),
        msg=full_payload.encode("utf-8"),
        digestmod=sha256
    ).hexdigest()
    return f"t={timestamp},v0={signature}"

# Example usage
payload = {"type": "post_call_transcription", ...}
header = generate_signature(payload, "your-secret-key")
```

### Test Request with curl

```bash
curl -X POST http://localhost:8000/webhook/post-call \
  -H "Content-Type: application/json" \
  -H "elevenlabs-signature: t=1764457176,v0=abc123..." \
  -d @tests/fixtures/post_call_transcription.json
```

---

## Related Files

| File | Purpose |
|------|---------|
| `app/webhooks/post_call.py` | Main webhook handler implementation |
| `app/models/requests.py` | Pydantic models for request validation |
| `app/auth/hmac.py` | HMAC signature verification |
| `app/memory/extraction.py` | Memory extraction and storage |
| `app/config.py` | Configuration and settings |
| `tests/test_webhooks.py` | Integration tests |
| `tests/fixtures/post_call_transcription.json` | Sample payload |
