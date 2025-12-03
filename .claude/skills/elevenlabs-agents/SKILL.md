---
name: elevenlabs-agents
description: "Build and deploy conversational voice AI agents with ElevenLabs Agents Platform. Use when: (1) Creating voice agents for phone/web/mobile, (2) Integrating Twilio or SIP telephony, (3) Adding knowledge bases or tools to agents, (4) Setting up post-call webhooks, (5) Connecting MCP servers to agents, (6) Analyzing conversations, (7) Using ElevenLabs Python/TypeScript SDK for voice agents."
---

# ElevenLabs Agents Platform

Build multimodal conversational AI agents with voice capabilities, deploy across telephony, web, and mobile.

## Architecture

The platform coordinates 4 core components:
- **ASR**: Fine-tuned Speech-to-Text model
- **LLM**: Your choice (GPT-4o, Claude 3.5 Sonnet, Gemini) or custom LLM
- **TTS**: Low-latency Text-to-Speech across 5k+ voices, 31 languages
- **Turn-taking**: Proprietary model for natural conversation timing

## Quick Start

### Dashboard Setup

1. Sign in at [elevenlabs.io](https://elevenlabs.io)
2. Navigate to Agents Platform dashboard
3. Create agent from Blank template
4. Configure: Agent behavior → Voice → Knowledge Base → Tools

### Python SDK

```bash
pip install elevenlabs[pyaudio]  # pyaudio for audio I/O
```

```python
from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation
from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface
import os

client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
conversation = Conversation(
    client=client,
    agent_id=os.getenv("AGENT_ID"),
    requires_auth=False,  # True for private agents
    audio_interface=DefaultAudioInterface(),
    callback_agent_response=lambda r: print(f"Agent: {r}"),
    callback_user_transcript=lambda t: print(f"User: {t}"),
)
conversation.start_session()
conversation.wait_for_session_end()
```

## Agent Configuration

### System Prompt

Define agent behavior, personality, and task instructions:

```
You are a helpful customer support assistant for [Company].
Your role is to answer questions about our products and services.
Always be polite and professional.
When you don't know something, say so and offer to connect with a human.
```

### First Message

The agent's opening statement when conversation starts:
```
Hi! I'm your [Company] assistant. How can I help you today?
```

### Voice Selection

Choose voices from the library based on use case:
- **Customer Support**: Professional, clear voices
- **Sales**: Warm, engaging voices
- **Technical**: Precise, articulate voices

Configure in Voice tab: voice_id, stability, similarity_boost, latency optimization.

## Tools

Agents support 4 tool types. See [references/tools.md](references/tools.md) for detailed configuration.

### Client Tools
Execute on client-side (browser/mobile):
- Navigate UI states
- Open modals
- Trigger local actions

### Server Tools (Webhooks)
Call external APIs:
- Query databases
- Process payments
- Update CRMs

### MCP Tools
Connect Model Context Protocol servers:
- Zapier integrations
- Custom MCP servers
- Third-party data sources

### System Tools
Built-in platform tools:
- `end_call`: Terminate conversation
- `transfer_to_number`: Transfer to human operator

## Knowledge Base

Equip agents with domain-specific information:

```python
# Upload via API
client.convai.agent_knowledge_base.create(
    agent_id="agent_xxx",
    url="https://docs.example.com",  # or file upload
    name="Product Documentation"
)
```

**Limits**: 20MB or 300k characters (non-enterprise)

**Best Practices**:
- Structure information clearly
- Update regularly
- Review transcripts for knowledge gaps

## Deployment

### Web Widget

Embed the conversation widget:

```html
<script src="https://elevenlabs.io/convai-widget/index.js" async></script>
<elevenlabs-convai agent-id="YOUR_AGENT_ID"></elevenlabs-convai>
```

### Telephony

**Twilio Native Integration**:
1. Import Twilio number in Agents Platform → Phone Numbers
2. Enter Account SID, Auth Token
3. Assign agent to handle inbound calls
4. Make outbound calls via dashboard or API

**SIP Trunking**:
- Connect existing PBX systems
- Use `sip-static.rtc.elevenlabs.io` for static IP
- Configure digest authentication (recommended)

See [references/telephony.md](references/telephony.md) for detailed setup.

### Outbound Calls

```python
# Initiate outbound call
client.convai.twilio.outbound_call(
    agent_id="agent_xxx",
    agent_phone_number_id="phone_xxx",
    to_number="+1234567890"
)
```

## Post-Call Webhooks

Receive call data after analysis completes. Configure in Agents Platform settings.

**Webhook Types**:
- `post_call_transcription`: Full transcript + analysis
- `post_call_audio`: Base64-encoded audio
- `call_initiation_failure`: Failed call info

**Payload includes**: conversation_id, transcript, analysis results, extracted data

**HMAC Validation**:
```python
import hmac
import hashlib

def verify_webhook(signature_header, body, secret):
    timestamp, hash_value = signature_header.split(",")
    expected = hmac.new(
        secret.encode(),
        f"{timestamp}.{body}".encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(hash_value, expected)
```

## Conversation Analysis

### Evaluation Criteria

Define success metrics evaluated per conversation:

```json
{
  "name": "solved_user_inquiry",
  "prompt": "Evaluate if the agent successfully resolved the user's question",
  "result": "success | failure | unknown"
}
```

### Data Collection

Extract structured data from transcripts:

```json
{
  "identifier": "user_intent",
  "type": "string",
  "description": "The primary intent or question from the user"
}
```

## MCP Integration

Connect external MCP servers for extended capabilities:

1. Add Custom MCP Server in dashboard
2. Configure: Name, Description, Server URL, optional Secret Token
3. Set approval mode: Always Ask (recommended) | Fine-Grained | No Approval
4. Assign to agents

**Security**: Review [MCP security guidelines](https://elevenlabs.io/docs/agents-platform/customization/tools/mcp/security) before integration.

## API Reference

Base URL: `https://api.elevenlabs.io/v1/convai`

**Key Endpoints**:
- `POST /agents/create` - Create agent
- `GET /agents/{agent_id}` - Get agent config
- `PATCH /agents/{agent_id}` - Update agent
- `GET /conversations` - List conversations
- `POST /twilio/outbound_call` - Initiate call

See [references/api.md](references/api.md) for complete reference.

## Best Practices

### LLM Selection
- **GPT-4o mini** or **Claude 3.5 Sonnet**: Best for tool calling
- Avoid Gemini 1.5 Flash for complex function calls

### Tool Design
- Use clear, descriptive names (avoid abbreviations)
- Include detailed parameter descriptions
- Specify expected formats (e.g., "YYYY-MM-DD")

### System Prompt Tips
- Guide tool usage explicitly
- Provide context for complex scenarios
- Include instructions for parameter collection

### Latency Optimization
- Balance voice quality vs response time
- Use appropriate model tiers
- Configure ambient audio during tool execution
