# Tech Stack

## Runtime Environment

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Language | Python | 3.12+ | Primary development language |
| Runtime | CPython | 3.12+ | Python interpreter |
| Package Manager | pip / uv | Latest | Dependency management |

## Backend Framework

| Component | Technology | Purpose |
|-----------|------------|---------|
| Web Framework | FastAPI | High-performance async API framework for webhook endpoints |
| ASGI Server | Uvicorn | Production-grade async server for FastAPI |
| Data Validation | Pydantic | Request/response validation and serialization |

## External Services and SDKs

| Component | Technology | Purpose |
|-----------|------------|---------|
| Voice AI Platform | ElevenLabs Agents Platform | Conversational AI agents with speech synthesis |
| ElevenLabs Integration | ElevenLabs Python SDK | SDK-based integration (NOT direct REST API) |
| Memory System | OpenMemory | Cognitive memory engine for persistent caller profiles |
| OpenMemory Integration | OpenMemory Python SDK | SDK-based integration (NOT direct REST API) |
| Telephony Provider | Twilio (via ElevenLabs) | Inbound/outbound call handling and caller ID |

## Development Tools

| Component | Technology | Purpose |
|-----------|------------|---------|
| Local Tunneling | ngrok | Expose local webhooks for ElevenLabs integration testing |
| Environment Management | python-dotenv | Load environment variables from .env files |
| Code Formatting | Black | Python code formatting |
| Linting | Ruff | Fast Python linter |
| Type Checking | mypy | Static type analysis |

## Configuration Management

### Environment Variables (.env)

```bash
# ElevenLabs API Configuration
ELEVENLABS_API_KEY=           # Primary API key for ElevenLabs SDK
ELEVENLABS_POST_CALL_KEY=     # HMAC secret for post-call webhook validation
ELEVENLABS_CLIENT_DATA_KEY=   # HMAC secret for client-data webhook validation
ELEVENLABS_SEARCH_DATA_KEY=   # HMAC secret for search-data webhook validation

# OpenMemory Configuration
OPENMEMORY_KEY=               # OpenMemory authentication key
OPENMEMORY_PORT=              # OpenMemory service port (local mode)
OPENMEMORY_DB_PATH=           # Path to OpenMemory database file
```

## Architecture Constraints

### Required Patterns

| Constraint | Requirement |
|------------|-------------|
| SDK Usage | MUST use ElevenLabs SDK and OpenMemory SDK; DO NOT use direct REST APIs |
| Primary Identifier | Caller phone number is the universal memory key |
| Data Storage | OpenMemory handles all storage internally; DO NOT implement external databases |
| Memory Retention | Configure zero-decay lambda to prevent memory loss |

### Explicitly Excluded

| Component | Reason |
|-----------|--------|
| Frontend | Backend processing only; no UI required |
| Database | OpenMemory manages storage; no PostgreSQL, MySQL, Redis, etc. |
| Direct REST Calls | SDKs provide cleaner, type-safe integration |
| Custom ORM | No database means no ORM needed |

## API Endpoints

### Webhook Endpoints

| Endpoint | Method | Purpose | ElevenLabs Feature |
|----------|--------|---------|-------------------|
| `/webhook/client-data` | POST | Conversation initiation personalization | Client Data Webhook |
| `/webhook/search-data` | POST | Mid-conversation memory retrieval | Server Tools |
| `/webhook/post-call` | POST | Post-conversation memory storage | Post-Call Webhook |

### Utility Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Service health check |

## Security

| Component | Implementation |
|-----------|----------------|
| Webhook Authentication | HMAC-SHA256 signature validation |
| Secret Management | Environment variables via .env (not committed to git) |
| Timestamp Validation | 30-minute tolerance window for webhook signatures |
| Per-Caller Isolation | Phone number-based user ID for memory separation |

## Project Structure

```
/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Environment configuration loading
│   ├── webhooks/
│   │   ├── __init__.py
│   │   ├── client_data.py   # /webhook/client-data handler
│   │   ├── search_data.py   # /webhook/search-data handler
│   │   └── post_call.py     # /webhook/post-call handler
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── client.py        # OpenMemory SDK client wrapper
│   │   ├── profiles.py      # Caller profile management
│   │   └── extraction.py    # Memory extraction from transcripts
│   ├── auth/
│   │   ├── __init__.py
│   │   └── hmac.py          # HMAC signature validation
│   └── models/
│       ├── __init__.py
│       ├── requests.py      # Pydantic request models
│       └── responses.py     # Pydantic response models
├── tests/
│   ├── __init__.py
│   ├── test_webhooks.py
│   ├── test_memory.py
│   └── fixtures/            # Sample ElevenLabs payloads
├── .env                     # Environment variables (not committed)
├── .env.example             # Environment variable template
├── requirements.txt         # Python dependencies
├── pyproject.toml           # Project metadata and tool configuration
└── README.md                # Setup and deployment instructions
```

## Dependencies

### Production Dependencies

```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
python-dotenv>=1.0.0
elevenlabs>=1.0.0
openmemory>=0.1.0
httpx>=0.26.0
```

### Development Dependencies

```
pytest>=7.4.0
pytest-asyncio>=0.23.0
black>=24.0.0
ruff>=0.1.0
mypy>=1.8.0
ngrok>=0.12.0
```

## OpenMemory Configuration

### Memory Sectors Used

| Sector | Content Type | Example |
|--------|--------------|---------|
| Episodic | Time-bound call events | "Called on 2024-01-15 about billing issue" |
| Semantic | Permanent facts | "Customer name is John Smith" |
| Procedural | Interaction patterns | "Prefers email follow-ups" |
| Emotional | Affective context | "Expressed frustration with wait times" |
| Reflective | Meta-cognitive insights | "High-value customer, 5+ years" |

### Retention Configuration

```python
# OpenMemory initialization with permanent retention
om = OpenMemory(
    mode="local",
    path=os.getenv("OPENMEMORY_DB_PATH"),
    tier="deep"
)

# Memory storage with zero decay (permanent retention)
om.add(
    content="Customer preference data",
    userId=caller_phone_number,
    salience=1.0,      # High importance
    decay_lambda=0.0   # No decay - permanent memory
)
```

## ElevenLabs Integration Points

### Client Data Webhook Response Format

```json
{
  "type": "conversation_initiation_client_data",
  "dynamic_variables": {
    "caller_name": "John Smith",
    "caller_history": "Previous calls: billing inquiry, product support",
    "caller_preferences": "Prefers concise responses"
  },
  "conversation_config_override": {
    "agent": {
      "prompt": {
        "prompt": "You are speaking with a returning customer..."
      },
      "first_message": "Welcome back, John! How can I help you today?"
    }
  }
}
```

### Post-Call Webhook Payload Fields Used

| Field | Path | Purpose |
|-------|------|---------|
| Caller ID | `data.metadata.caller_id` | Primary memory key |
| Transcript | `data.transcript` | Conversation content for memory extraction |
| Summary | `data.analysis.summary` | High-level call summary |
| Duration | `data.metadata.call_duration` | Call metrics |
| Timestamp | `event_timestamp` | Memory temporal context |
