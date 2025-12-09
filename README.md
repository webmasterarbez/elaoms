# ELAOMS - Eleven Labs Agents Open Memory System

A self-learning memory system that enables Voice AI agents to deliver personalized, context-aware conversations by integrating **ElevenLabs Agents Platform** with **OpenMemory's cognitive memory engine**.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Endpoints](#api-endpoints)
- [How It Works](#how-it-works)
- [Memory Management](#memory-management)
- [Security](#security)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

**ElevenLabs Agents Open Memory System (ELAOMS)** solves the problem of stateless voice AI conversations. Traditional voice AI agents start each call from zero—callers must re-introduce themselves, repeat preferences, and re-explain their history on every interaction.

ELAOMS provides:
- **Instant caller recognition** using phone numbers as persistent identifiers
- **Personalization from the first ring** with dynamic variable injection
- **Continuous learning** across all interactions via OpenMemory's cognitive memory engine
- **Multi-sector memory organization** (episodic, semantic, procedural, emotional, reflective)

### The Problem

Voice AI agents powered by ElevenLabs deliver exceptional speech synthesis and natural conversation flow, but each call starts from zero:

- 30-45 seconds wasted per call on re-identification
- 25% higher customer frustration for repeated interactions
- Lost upsell opportunities due to lack of purchase history awareness
- Increased costs from longer average handle times

### The Solution

A three-webhook architecture that captures, stores, and retrieves caller memories:

```
Caller → Twilio → ElevenLabs Agents
           ↓
   [1] Client-Data Webhook → Retrieve caller profile → Personalized greeting
           ↓
   [2] Search-Data Webhook → Mid-call memory queries → Real-time context
           ↓
   [3] Post-Call Webhook → Extract & store memories → Profile updated
```

---

## Key Features

### Personalization
- **Phone number-based identification** - Automatic caller recognition via Twilio-provided caller ID
- **Dynamic variable injection** - Personalize agent prompts and first messages
- **Returning caller greetings** - "Welcome back, Sarah!" before the first word is spoken
- **Profile summaries** - Quick context about the caller's history and preferences

### Memory Management
- **Multi-sector organization** - Episodic, semantic, procedural, emotional, and reflective memory
- **Salience-based retrieval** - Intelligent ranking by relevance, recency, and reinforcement
- **Zero-decay retention** - Critical memories persist indefinitely
- **Per-caller isolation** - Strict memory separation for multi-tenant deployments

### Integration
- **SDK-first approach** - Clean Python interfaces via ElevenLabs and OpenMemory SDKs
- **Webhook authentication** - HMAC-SHA256 signature validation
- **Environment-based configuration** - Secure, portable deployment
- **Local development support** - ngrok tunneling for webhook testing

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ELEVENLABS AGENTS                              │
│                           (Voice AI Platform)                               │
└─────────────────────────────────────────────────────────────────────────────┘
                │                    │                    │
                ▼                    ▼                    ▼
    ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
    │  Client-Data      │ │   Search-Data     │ │   Post-Call       │
    │  Webhook          │ │   Webhook         │ │   Webhook         │
    │  (Call Start)     │ │   (Mid-Call)      │ │   (Call End)      │
    └─────────┬─────────┘ └─────────┬─────────┘ └─────────┬─────────┘
              │                     │                     │
              ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           APPLICATION LAYER                                 │
│              (FastAPI Webhooks + Pydantic Request/Response Models)          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              OPENMEMORY                                     │
│                    (Persistent Long-Term Memory Engine)                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │   Semantic   │ │   Episodic   │ │  Procedural  │ │  Emotional   │       │
│  │   Memory     │ │   Memory     │ │   Memory     │ │   Memory     │       │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Language** | Python 3.12+ | Primary development language |
| **Web Framework** | FastAPI | High-performance async API framework |
| **ASGI Server** | Uvicorn | Production-grade async server |
| **Data Validation** | Pydantic v2 | Request/response validation |
| **Voice AI** | ElevenLabs Agents Platform | Conversational AI with speech synthesis |
| **Memory Engine** | OpenMemory | Cognitive memory for persistent profiles |
| **Telephony** | Twilio (via ElevenLabs) | Inbound/outbound call handling |
| **Code Quality** | Black, Ruff, mypy | Formatting, linting, type checking |
| **Testing** | pytest, pytest-asyncio | Test framework with async support |

---

## Project Structure

```
elaoms/
├── app/                          # Main application source code
│   ├── __init__.py
│   ├── main.py                   # FastAPI application entry point (v1.0.0)
│   ├── config.py                 # Environment configuration & validation
│   ├── auth/                     # Authentication & Security
│   │   ├── __init__.py
│   │   └── hmac.py               # HMAC-SHA256 signature & API key validation
│   ├── models/                   # Pydantic request/response models
│   │   ├── __init__.py
│   │   ├── requests.py           # Request models for webhooks
│   │   └── responses.py          # Response models for webhooks
│   ├── memory/                   # OpenMemory integration
│   │   ├── __init__.py
│   │   ├── client.py             # OpenMemory SDK client wrapper
│   │   ├── profiles.py           # Caller profile management
│   │   └── extraction.py         # Memory extraction from transcripts
│   └── webhooks/                 # Webhook endpoint handlers
│       ├── __init__.py
│       ├── client_data.py        # POST /webhook/client-data (X-Api-Key auth)
│       ├── search_data.py        # POST /webhook/search-data (no auth)
│       └── post_call.py          # POST /webhook/post-call (HMAC auth)
├── tests/                        # Test suite
│   ├── conftest.py               # Pytest configuration and fixtures
│   ├── test_auth.py              # HMAC authentication tests
│   ├── test_config.py            # Configuration validation tests
│   ├── test_models.py            # Request/response model tests
│   ├── test_memory.py            # Memory operations tests
│   ├── test_webhooks.py          # Webhook endpoint tests
│   ├── test_integration.py       # End-to-end integration tests
│   └── fixtures/                 # Test data and fixtures
├── scripts/                      # Utility scripts
│   └── run_local.sh              # Local development server script
├── pyproject.toml                # Project configuration & dev dependencies
├── requirements.txt              # Production dependencies
├── .env.example                  # Environment variables template
└── README.md                     # This file
```

---

## Installation

### Prerequisites

- Python 3.12+
- OpenMemory server (local or remote)
- ElevenLabs account with API access
- ngrok account (for local webhook testing)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/elaoms.git
   cd elaoms
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt

   # For development
   pip install -e ".[dev]"
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```

5. **Run the server**
   ```bash
   # Using the script
   ./scripts/run_local.sh

   # Or directly with uvicorn
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

6. **Expose webhooks for testing (optional)**
   ```bash
   ngrok http 8000
   ```

---

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# ElevenLabs Configuration
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
ELEVENLABS_POST_CALL_KEY=your_post_call_hmac_secret_here        # REQUIRED for post-call webhook auth
ELEVENLABS_CLIENT_DATA_KEY=your_client_data_api_key_here        # REQUIRED for client-data webhook auth
ELEVENLABS_SEARCH_DATA_KEY=your_search_data_hmac_secret_here    # Reserved for future use

# OpenMemory Configuration
OPENMEMORY_KEY=your_openmemory_api_key_here                     # Required for REMOTE mode
OPENMEMORY_PORT=8000                                            # Port or full URL (e.g., http://localhost:8000)
OPENMEMORY_DB_PATH=./data/openmemory.db                         # Path for local mode reference

# Storage Configuration
PAYLOAD_STORAGE_PATH=./payloads                                 # Directory for conversation payloads
```

### Getting API Keys

| Service | Where to Get |
|---------|--------------|
| ElevenLabs API Key | [ElevenLabs Settings](https://elevenlabs.io/app/settings/api-keys) |
| Post-Call HMAC Secret | ElevenLabs Agent webhook configuration panel |
| Client-Data API Key | ElevenLabs Agent webhook configuration panel |
| OpenMemory Key | Your OpenMemory server configuration |

---

## API Endpoints

### Webhook Endpoints

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/webhook/client-data` | POST | X-Api-Key | Conversation initiation personalization |
| `/webhook/search-data` | POST | None | Mid-conversation memory search |
| `/webhook/post-call` | POST | HMAC-SHA256 | Post-call transcript & memory storage |

### Utility Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Root info endpoint |
| `/health` | GET | Health check |
| `/docs` | GET | Swagger UI documentation |
| `/redoc` | GET | ReDoc documentation |

### Example: Client-Data Request/Response

**Request:**
```json
{
  "caller_id": "+16129782029",
  "agent_id": "agent_8501k9r8sbb5fjbbym8c9y1jqt9b",
  "called_number": "+16123241623",
  "call_sid": "CA98d2b6a08ebed6b78880b61ffc0e3299"
}
```

**Response:**
```json
{
  "dynamic_variables": {
    "user_name": "Stefan",
    "user_profile_summary": "Returning customer, prefers email follow-ups",
    "last_call_summary": "Previous conversation: Discussed billing inquiry"
  },
  "conversation_config_override": {
    "agent": {
      "first_message": "Welcome back, Stefan! How can I help you today?"
    }
  }
}
```

---

## How It Works

### 1. Client-Data Webhook (Call Initiation)

When a call begins, ElevenLabs sends caller information:

```
Caller calls → Twilio → ElevenLabs → Client-Data Webhook
                                           ↓
                                    Query OpenMemory for caller profile
                                           ↓
                                    Return personalized variables
                                           ↓
                                    Agent greets with "Welcome back, [Name]!"
```

### 2. Search-Data Webhook (Mid-Call)

During conversation, the agent can search memories:

```
Agent needs context → Server Tool call → Search-Data Webhook
                                              ↓
                                       Query OpenMemory with search term
                                              ↓
                                       Return relevant memories
                                              ↓
                                       Agent uses context in response
```

### 3. Post-Call Webhook (Call Completion)

After the call ends, the system learns:

```
Call ends → ElevenLabs → Post-Call Webhook
                              ↓
                       Extract transcript & data collection results
                              ↓
                       Store as memories in OpenMemory
                              ↓
                       Profile updated for next call
```

---

## Memory Management

### Memory Sectors

| Sector | Content Type | Example |
|--------|--------------|---------|
| **Semantic** | Permanent facts | "Customer name is John Smith" |
| **Episodic** | Time-bound events | "Called on 2024-01-15 about billing" |
| **Procedural** | Interaction patterns | "Prefers email follow-ups" |
| **Emotional** | Affective context | "Expressed frustration with wait times" |
| **Reflective** | Meta-cognitive insights | "High-value customer, 5+ years" |

### Salience Levels

| Level | Value | Use Case |
|-------|-------|----------|
| HIGH_SALIENCE | 0.9 | Profile information, critical facts |
| MEDIUM_SALIENCE | 0.7 | Conversation summaries, preferences |
| LOW_SALIENCE | 0.3 | Routine interactions, general notes |

### Retention Policy

All memories are stored with `decayLambda=0` (zero decay), ensuring permanent retention. Memories are weighted by salience for intelligent retrieval prioritization.

---

## Security

### Authentication Methods

#### X-Api-Key Authentication (Client-Data Webhook)

The client-data webhook uses API key authentication:

- **Header:** `X-Api-Key`
- **Validation:** Compared against `ELEVENLABS_CLIENT_DATA_KEY` environment variable
- **Purpose:** Validates that requests come from authorized sources

#### HMAC-SHA256 Authentication (Post-Call Webhook)

The post-call webhook requires HMAC signature validation:

- **Header:** `elevenlabs-signature`
- **Format:** `t=timestamp,v0=hash`
- **Algorithm:** SHA256 HMAC of `{timestamp}.{body}`
- **Secret:** Uses `ELEVENLABS_POST_CALL_KEY` environment variable
- **Tolerance:** 30-minute timestamp window
- **Protection:** Constant-time comparison prevents timing attacks

### Security Features

| Feature | Implementation |
|---------|----------------|
| Post-Call Authentication | HMAC-SHA256 signature validation |
| Client-Data Authentication | X-Api-Key header validation |
| Secret Management | Environment variables (not committed to git) |
| Timestamp Validation | 30-minute tolerance window for HMAC |
| Per-Caller Isolation | Phone number-based user ID separation |
| Replay Prevention | Timestamp validation prevents replay attacks |

---

## Development

### Code Quality Tools

```bash
# Format code
black app/ tests/

# Lint code
ruff check app/ tests/

# Type checking
mypy app/
```

### Local Development

1. Start the server with hot reload:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

2. Expose via ngrok:
   ```bash
   ngrok http 8000
   ```

3. Configure ElevenLabs Agent webhooks with your ngrok URL:
   - Client-Data: `https://your-ngrok-url.ngrok.io/webhook/client-data`
   - Search-Data: `https://your-ngrok-url.ngrok.io/webhook/search-data`
   - Post-Call: `https://your-ngrok-url.ngrok.io/webhook/post-call`

---

## Testing

### Run All Tests

```bash
pytest
```

### Run Specific Test Files

```bash
# Unit tests
pytest tests/test_auth.py
pytest tests/test_models.py
pytest tests/test_memory.py

# Integration tests
pytest tests/test_integration.py

# Webhook tests
pytest tests/test_webhooks.py
```

### Test with Coverage

```bash
pytest --cov=app --cov-report=html
```

---

## Deployment

### Production Checklist

- [ ] Set all environment variables securely
- [ ] Configure HTTPS (required for webhooks)
- [ ] Set up OpenMemory server
- [ ] Configure ElevenLabs Agent webhooks
- [ ] Enable logging and monitoring
- [ ] Configure CORS if needed

### Docker (Example)

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY .env .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Requirements

- Python 3.12+
- OpenMemory server accessible
- ElevenLabs Agent configured with webhooks
- HTTPS for production webhook URLs

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests before committing
pytest

# Format and lint
black app/ tests/
ruff check app/ tests/
mypy app/
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- [ElevenLabs](https://elevenlabs.io/) - Voice AI Platform
- [OpenMemory](https://github.com/CaviraOSS/openmemory) - Cognitive Memory Engine
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Pydantic](https://docs.pydantic.dev/) - Data validation library

---

## Support

- **Issues:** [GitHub Issues](https://github.com/your-org/elaoms/issues)
- **ElevenLabs Docs:** [ElevenLabs Documentation](https://elevenlabs.io/docs)
- **OpenMemory Docs:** [OpenMemory Documentation](https://github.com/CaviraOSS/openmemory)
