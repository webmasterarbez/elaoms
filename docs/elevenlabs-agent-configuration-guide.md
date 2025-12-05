# ElevenLabs Agent Configuration Guide

A comprehensive guide to creating conversational voice AI agents using the ElevenLabs Agents Platform API, with full integration support for the OpenMemory system.

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Configuration Schema](#configuration-schema)
- [Agent Examples](#agent-examples)
- [OpenMemory Integration](#openmemory-integration)
- [Webhook Configuration](#webhook-configuration)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

---

## Overview

The ElevenLabs Agents Platform provides a powerful API for creating conversational voice AI agents. This guide covers:

- **Agent Creation**: How to configure and deploy agents via the API
- **Voice Configuration**: TTS settings for natural speech synthesis
- **Tool Integration**: Webhooks, client tools, and MCP connections
- **Conversation Flow**: Turn-taking, timeouts, and interruption handling
- **Data Collection**: Extracting structured information from conversations
- **OpenMemory Integration**: Persistent memory for personalized experiences

### Architecture Flow

```
User Call → Telephony (Twilio/SIP) → ElevenLabs Agent
                                          ↓
                    ┌─────────────────────┼─────────────────────┐
                    ↓                     ↓                     ↓
            ASR (Speech-to-Text)    LLM (GPT/Claude)    TTS (Voice Synthesis)
                    ↓                     ↓                     ↓
            User Transcript     Agent Response Text     Agent Audio Output
                                          ↓
                              Webhooks → OpenMemory
```

---

## Prerequisites

### Required Credentials

1. **ElevenLabs API Key**: Get from [ElevenLabs Settings](https://elevenlabs.io/app/settings/api-keys)
2. **Voice ID**: Choose from [ElevenLabs Voice Library](https://elevenlabs.io/app/voice-library)
3. **OpenMemory Key** (optional): For persistent caller memory

### Environment Setup

```bash
# Set your API key
export ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# Optional: Set a default voice
export ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM
```

---

## Quick Start

We provide pre-built agent configurations as JSON files in `examples/agents/`. Use the Python script to create agents:

```bash
cd examples/agents

# List available agent templates
python create_agent.py --list

# Create a specific agent
python create_agent.py 01-customer-support.json

# Create all agents
python create_agent.py --all

# Preview without creating (dry run)
python create_agent.py --dry-run 01-customer-support.json
```

Or use curl directly with a JSON file:

```bash
curl -X POST "https://api.elevenlabs.io/v1/convai/agents/create" \
  -H "xi-api-key: $ELEVENLABS_API_KEY" \
  -H "Content-Type: application/json" \
  -d @examples/agents/01-customer-support.json
```

---

## API Reference

### Endpoint

```
POST https://api.elevenlabs.io/v1/convai/agents/create
```

### Authentication

```
Header: xi-api-key: YOUR_API_KEY
```

### Response

```json
{
  "agent_id": "agent_xxxxxxxxxxxxxxxxxxxx"
}
```

---

## Configuration Schema

### Root Structure

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | No | Agent display name |
| `conversation_config` | object | **Yes** | Core conversation settings |
| `platform_settings` | object | No | Widget, auth, webhooks, data collection |
| `tags` | array | No | Categorization tags |

### Conversation Config

```json
{
  "conversation_config": {
    "agent": {
      "first_message": "Hello! How can I help?",
      "language": "en",
      "prompt": {
        "prompt": "System prompt here...",
        "llm": "gpt-4o-mini",
        "temperature": 0.7,
        "max_tokens": 1024
      }
    },
    "asr": {
      "provider": "elevenlabs",
      "quality": "high"
    },
    "tts": {
      "model_id": "eleven_turbo_v2_5",
      "voice_id": "YOUR_VOICE_ID",
      "stability": 0.5,
      "similarity_boost": 0.75
    },
    "turn": {
      "turn_timeout": 10.0,
      "silence_end_call_timeout": 30.0
    }
  }
}
```

### Available LLMs

| Provider | Models |
|----------|--------|
| **OpenAI** | `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `gpt-4`, `gpt-3.5-turbo` |
| **Anthropic** | `claude-3-5-sonnet`, `claude-3-7-sonnet`, `claude-sonnet-4`, `claude-sonnet-4-5`, `claude-3-haiku`, `claude-haiku-4-5` |
| **Google** | `gemini-2.0-flash`, `gemini-2.5-flash`, `gemini-1.5-pro`, `gemini-1.5-flash` |

### TTS Models

| Model | Description | Use Case |
|-------|-------------|----------|
| `eleven_turbo_v2_5` | Latest turbo model | General use, low latency |
| `eleven_flash_v2_5` | Fastest model | Real-time conversations |
| `eleven_multilingual_v2` | Multi-language support | International deployments |

### Popular Voice IDs

| Voice | ID | Description |
|-------|------|-------------|
| Rachel | `21m00Tcm4TlvDq8ikWAM` | Warm, professional female |
| Adam | `pNInz6obpgDQGcFmaJgB` | Clear, authoritative male |
| Bella | `EXAVITQu4vr4xnSDxMaL` | Friendly, conversational female |
| Antoni | `ErXwobaYiN019PkySvjV` | Calm, reassuring male |
| Elli | `MF3mGyEYCl7XYWbV9V6O` | Young, energetic female |
| Josh | `TxGEqnHWrfWFTfGW9XjX` | Deep, trustworthy male |

---

## Agent Examples

All examples are available as JSON files in [`examples/agents/`](../examples/agents/):

| File | Agent Type | Key Features |
|------|------------|--------------|
| `01-customer-support.json` | Customer Support | FAQ handling, ticket creation, escalation |
| `02-sales-lead-qualification.json` | Sales | BANT qualification, demo scheduling, CRM capture |
| `03-healthcare-appointment.json` | Healthcare | Appointment booking, prescription refills, triage |
| `04-ecommerce-shopping.json` | E-commerce | Order tracking, returns, product recommendations |
| `05-it-helpdesk.json` | IT Helpdesk | Password resets, VPN troubleshooting, ticket creation |
| `06-financial-services.json` | Financial Services | Account inquiries, fraud alerts, disputes |
| `07-hospitality-concierge.json` | Hospitality | Reservations, concierge services, loyalty programs |
| `08-memoir-interviewer.json` | Memoir Writing | Biographical interviews, story capture |

### Customizing an Agent

1. **Copy a template**: `cp examples/agents/01-customer-support.json my-agent.json`
2. **Edit the configuration**:
   - `name`: Your agent's name
   - `conversation_config.agent.first_message`: Opening greeting
   - `conversation_config.agent.prompt.prompt`: System instructions
   - `conversation_config.tts.voice_id`: Voice selection
   - Webhook URLs: Replace `https://your-webhook-url.com/...` with your endpoints
3. **Deploy**: `python examples/agents/create_agent.py my-agent.json`

---

## OpenMemory Integration

All agents can be enhanced with persistent memory using OpenMemory. This enables:

- **Caller Recognition**: Personalized greetings based on history
- **Conversation Continuity**: Pick up where you left off
- **Preference Learning**: Remember user preferences across calls
- **Behavioral Patterns**: Adapt to individual communication styles

### Configure Webhooks for Memory

Add these webhook URLs to your agent's platform settings to enable OpenMemory integration:

```json
{
  "platform_settings": {
    "workspace_overrides": {
      "conversation_initiation_client_data_webhook": {
        "url": "https://your-server.com/webhook/client-data",
        "request_headers": {
          "Authorization": "Bearer YOUR_WEBHOOK_SECRET"
        }
      },
      "webhooks": {
        "events": ["transcript"],
        "send_audio": false
      }
    },
    "overrides": {
      "enable_conversation_initiation_client_data_from_webhook": true
    }
  }
}
```

### Memory Flow

```
1. Call Starts
   └─→ Client-Data Webhook called
       └─→ Query OpenMemory for caller profile
           └─→ Return dynamic_variables + first_message override

2. Call In Progress
   └─→ Agent uses dynamic variables in conversation
   └─→ Search-Data Webhook for mid-call memory queries

3. Call Ends
   └─→ Post-Call Webhook receives transcript
       └─→ Extract memories from conversation
           └─→ Store in OpenMemory for future calls
```

### Example Client-Data Response

```json
{
  "dynamic_variables": {
    "user_name": "Sarah",
    "user_profile_summary": "Returning customer, prefers email follow-ups",
    "last_call_summary": "Discussed billing inquiry on Dec 1"
  },
  "conversation_config_override": {
    "agent": {
      "first_message": "Welcome back, Sarah! I see we spoke recently about your billing. How can I help you today?"
    }
  }
}
```

---

## Webhook Configuration

### Setting Up Post-Call Webhooks

1. **Create webhook URL endpoint** on your server
2. **Configure in ElevenLabs Dashboard**:
   - Go to Agent Settings → Webhooks
   - Add Post-Call Webhook URL
   - Copy HMAC Secret for signature validation

### HMAC Signature Validation

```python
import hmac
import hashlib
import time

def verify_elevenlabs_webhook(signature_header: str, body: bytes, secret: str) -> bool:
    """Verify ElevenLabs webhook signature."""
    try:
        parts = dict(part.split("=") for part in signature_header.split(","))
        timestamp = parts.get("t", "")
        provided_hash = parts.get("v0", "")

        # Check timestamp (30-minute tolerance)
        if abs(time.time() - int(timestamp)) > 1800:
            return False

        # Compute expected signature
        message = f"{timestamp}.{body.decode()}"
        expected_hash = hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(provided_hash, expected_hash)
    except Exception:
        return False
```

---

## Best Practices

### System Prompt Design

1. **Be Specific**: Clear role definition and boundaries
2. **Include Examples**: Show expected dialogue patterns
3. **Define Escalation**: When and how to transfer to humans
4. **Set Tone**: Explicit guidance on personality and style

### Voice Selection

| Use Case | Voice Characteristics | Recommended Settings |
|----------|----------------------|---------------------|
| Customer Support | Clear, patient | Stability: 0.6, Similarity: 0.8 |
| Sales | Energetic, warm | Stability: 0.5, Similarity: 0.75 |
| Healthcare | Calm, reassuring | Stability: 0.65, Similarity: 0.8 |
| Financial | Professional, trustworthy | Stability: 0.7, Similarity: 0.8 |
| Hospitality | Elegant, warm | Stability: 0.6, Similarity: 0.8 |
| Memoir | Gentle, unhurried | Stability: 0.7, Similarity: 0.85 |

### Turn Configuration

| Scenario | Turn Timeout | Silence End Call | Eagerness |
|----------|-------------|------------------|-----------|
| Quick inquiries | 8-10s | 20s | normal |
| Complex support | 15s | 45s | patient |
| Elderly callers | 20-30s | 60s | patient |
| Sales calls | 10-12s | 20s | normal |
| Emotional conversations | 30s | 60s | patient |

### LLM Selection

| Complexity | Recommended LLM | Temperature |
|------------|-----------------|-------------|
| Simple FAQ | gpt-4o-mini | 0.3-0.5 |
| General support | gpt-4o-mini | 0.5-0.7 |
| Complex reasoning | gpt-4o | 0.5-0.7 |
| Creative/empathetic | gpt-4o or claude-3-5-sonnet | 0.7-0.9 |
| Tool-heavy | gpt-4o or claude-3-5-sonnet | 0.4-0.6 |

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Agent not responding | Invalid API key | Verify `ELEVENLABS_API_KEY` is correct |
| No voice output | Invalid voice_id | Check voice exists in your account |
| Webhook not called | URL not accessible | Ensure HTTPS and public accessibility |
| HMAC validation fails | Wrong secret | Re-copy secret from ElevenLabs dashboard |
| Agent cuts off early | Short timeout | Increase `silence_end_call_timeout` |
| Poor transcription | Low audio quality | Use higher quality ASR setting |

### Debug Commands

```bash
# Test API key
curl -X GET "https://api.elevenlabs.io/v1/user" \
  -H "xi-api-key: $ELEVENLABS_API_KEY"

# List your agents
curl -X GET "https://api.elevenlabs.io/v1/convai/agents" \
  -H "xi-api-key: $ELEVENLABS_API_KEY"

# Get specific agent
curl -X GET "https://api.elevenlabs.io/v1/convai/agents/{agent_id}" \
  -H "xi-api-key: $ELEVENLABS_API_KEY"

# List available voices
curl -X GET "https://api.elevenlabs.io/v1/voices" \
  -H "xi-api-key: $ELEVENLABS_API_KEY"
```

---

## Additional Resources

- [ElevenLabs Documentation](https://elevenlabs.io/docs)
- [Agents Platform Overview](https://elevenlabs.io/docs/agents-platform)
- [Voice Library](https://elevenlabs.io/app/voice-library)
- [API Reference](https://elevenlabs.io/docs/api-reference)
- [OpenMemory Integration Guide](../README.md)

---

## Support

- **ElevenLabs Support**: [support@elevenlabs.io](mailto:support@elevenlabs.io)
- **API Status**: [status.elevenlabs.io](https://status.elevenlabs.io)
- **Community**: [Discord](https://discord.gg/elevenlabs)
