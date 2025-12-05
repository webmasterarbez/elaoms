# ElevenLabs Agent Configuration Examples

Pre-built JSON configurations for common voice AI agent use cases.

## Quick Start

```bash
# Set your API key
export ELEVENLABS_API_KEY=your_api_key_here

# List available agents
python create_agent.py --list

# Create a specific agent
python create_agent.py 01-customer-support.json

# Create all agents
python create_agent.py --all

# Preview without creating (dry run)
python create_agent.py --dry-run 01-customer-support.json
```

## Available Agents

| File | Agent Type | Use Case |
|------|------------|----------|
| `01-customer-support.json` | Customer Support | Inbound support, troubleshooting, ticket creation |
| `02-sales-lead-qualification.json` | Sales | BANT qualification, demo scheduling |
| `03-healthcare-appointment.json` | Healthcare | Appointment scheduling, prescription refills |
| `04-ecommerce-shopping.json` | E-commerce | Order tracking, returns, product search |
| `05-it-helpdesk.json` | IT Support | Password resets, VPN issues, tickets |
| `06-financial-services.json` | Banking | Account inquiries, disputes, card services |
| `07-hospitality-concierge.json` | Hospitality | Hotel reservations, concierge services |
| `08-memoir-interviewer.json` | Memoir Writing | Biographical interviews, story capture |

## Customization

### Override Voice ID

```bash
# Via environment variable
export ELEVENLABS_VOICE_ID=your_voice_id
python create_agent.py 01-customer-support.json

# Via command line
python create_agent.py --voice-id your_voice_id 01-customer-support.json
```

### Edit Configuration

1. Copy a config file: `cp 01-customer-support.json my-agent.json`
2. Edit the JSON file to customize:
   - `name`: Agent display name
   - `conversation_config.agent.first_message`: Opening greeting
   - `conversation_config.agent.prompt.prompt`: System prompt
   - `conversation_config.tts.voice_id`: Voice selection
   - `platform_settings.data_collection`: Fields to extract
3. Create: `python create_agent.py my-agent.json`

### Using curl Instead

```bash
# Load your API key
export ELEVENLABS_API_KEY=your_api_key_here

# Create agent from JSON file
curl -X POST "https://api.elevenlabs.io/v1/convai/agents/create" \
  -H "xi-api-key: $ELEVENLABS_API_KEY" \
  -H "Content-Type: application/json" \
  -d @01-customer-support.json
```

## Voice Options

| Voice | ID | Style |
|-------|------|-------|
| Rachel | `21m00Tcm4TlvDq8ikWAM` | Warm, professional female |
| Adam | `pNInz6obpgDQGcFmaJgB` | Clear, authoritative male |
| Bella | `EXAVITQu4vr4xnSDxMaL` | Friendly, conversational female |
| Antoni | `ErXwobaYiN019PkySvjV` | Calm, reassuring male |
| Elli | `MF3mGyEYCl7XYWbV9V6O` | Young, energetic female |
| Josh | `TxGEqnHWrfWFTfGW9XjX` | Deep, trustworthy male |

## Webhook Placeholders

All configs use placeholder webhook URLs (`https://your-webhook-url.com/...`). Replace these with your actual endpoints before creating agents.
