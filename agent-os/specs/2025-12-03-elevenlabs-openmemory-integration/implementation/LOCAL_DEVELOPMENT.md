# Local Development Setup Guide

This guide covers setting up and running the ElevenLabs OpenMemory Integration for local development and testing.

## Prerequisites

- Python 3.12+
- ngrok account (for webhook tunneling)
- ElevenLabs account with API access
- OpenMemory server running (local or remote)

## Initial Setup

### 1. Clone and Install Dependencies

```bash
# Navigate to project directory
cd elevenlabs_agents_open_memory_system

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env
```

Edit `.env` with your credentials:

```bash
# ElevenLabs Configuration
ELEVENLABS_API_KEY=your_elevenlabs_api_key
ELEVENLABS_POST_CALL_KEY=your_hmac_secret_for_post_call
ELEVENLABS_CLIENT_DATA_KEY=your_client_data_key
ELEVENLABS_SEARCH_DATA_KEY=your_search_data_key

# OpenMemory Configuration
OPENMEMORY_KEY=your_openmemory_api_key
OPENMEMORY_PORT=8080  # or full URL: http://localhost:8080
OPENMEMORY_DB_PATH=/path/to/openmemory/db

# Storage Configuration
PAYLOAD_STORAGE_PATH=/tmp/elevenlabs_payloads
```

### 3. Start the Local Server

```bash
# Using the provided script
./scripts/run_local.sh

# Or manually with uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The server will start at `http://localhost:8000`.

## Setting Up ngrok for Webhook Tunneling

ngrok creates a public URL that tunnels to your local server, allowing ElevenLabs to send webhooks to your development machine.

### 1. Install ngrok

```bash
# macOS with Homebrew
brew install ngrok

# Or download from https://ngrok.com/download
```

### 2. Authenticate ngrok

```bash
# Get your auth token from https://dashboard.ngrok.com/auth
ngrok authtoken YOUR_AUTH_TOKEN
```

### 3. Start ngrok Tunnel

```bash
# Start tunnel to local server
ngrok http 8000
```

ngrok will display output like:

```
Session Status                online
Forwarding                    https://abc123.ngrok.io -> http://localhost:8000
```

Copy the HTTPS forwarding URL (e.g., `https://abc123.ngrok.io`).

### 4. Configure ElevenLabs Webhook URLs

In your ElevenLabs Agent configuration, set the webhook URLs:

| Webhook Type | URL |
|-------------|-----|
| Client Data | `https://your-ngrok-url.ngrok.io/webhook/client-data` |
| Search Data | `https://your-ngrok-url.ngrok.io/webhook/search-data` |
| Post Call | `https://your-ngrok-url.ngrok.io/webhook/post-call` |

**Important:** Update these URLs each time you restart ngrok (unless using a reserved subdomain).

## Testing the Webhooks

### Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy", "service": "elevenlabs-openmemory-integration", "timestamp": "..."}
```

### Test Client Data Webhook

```bash
curl -X POST http://localhost:8000/webhook/client-data \
  -H "Content-Type: application/json" \
  -d '{"caller_id": "+16129782029", "agent_id": "agent_test", "called_number": "+16123241623", "call_sid": "CA_test"}'
```

### Test Search Data Webhook

```bash
curl -X POST http://localhost:8000/webhook/search-data \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the users name?", "user_id": "+16129782029", "agent_id": "agent_test"}'
```

### API Documentation

Access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_integration.py -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=term-missing
```

## Troubleshooting

### Common Issues

#### 1. ngrok Tunnel Not Working

**Symptom:** ElevenLabs webhooks returning connection errors

**Solutions:**
- Verify ngrok is running: `ngrok status`
- Check local server is running on the correct port
- Ensure ngrok URL is correctly configured in ElevenLabs
- Check for firewall blocking connections

#### 2. HMAC Authentication Failing (401 Errors)

**Symptom:** Post-call webhook returns 401 Unauthorized

**Solutions:**
- Verify `ELEVENLABS_POST_CALL_KEY` matches the secret configured in ElevenLabs
- Check that the timestamp is within 30-minute tolerance
- Ensure the request body is not modified between signature generation and verification

#### 3. OpenMemory Connection Errors

**Symptom:** Memory operations failing with connection errors

**Solutions:**
- Verify OpenMemory server is running
- Check `OPENMEMORY_PORT` configuration
- Verify `OPENMEMORY_KEY` is correct
- Test OpenMemory connectivity directly

#### 4. Payloads Not Saving

**Symptom:** Post-call transcription/audio not saved to disk

**Solutions:**
- Verify `PAYLOAD_STORAGE_PATH` directory exists and is writable
- Check for disk space
- Review application logs for file system errors

### Viewing Logs

```bash
# Uvicorn logs (when running with --reload)
# Logs appear in the terminal where the server is running

# Increase log verbosity
LOG_LEVEL=debug ./scripts/run_local.sh
```

### ngrok Tips

1. **Reserved Subdomain:** Use ngrok's paid plan to get a stable URL that doesn't change on restart.

2. **Inspect Requests:** ngrok provides a web interface at `http://localhost:4040` to inspect all requests.

3. **Replay Requests:** Use the ngrok inspector to replay webhook requests for debugging.

## Manual Integration Testing Checklist

When testing the full integration:

- [ ] Start local server (`./scripts/run_local.sh`)
- [ ] Start ngrok tunnel (`ngrok http 8000`)
- [ ] Update ElevenLabs webhook URLs
- [ ] Make a test call to your ElevenLabs agent
- [ ] Verify client-data webhook receives the call
- [ ] Verify search-data webhook works during conversation (if agent uses tools)
- [ ] Verify post-call webhook receives and processes transcription
- [ ] Check payload files are saved to `PAYLOAD_STORAGE_PATH`
- [ ] Make another call to verify returning caller is recognized
- [ ] Verify personalized greeting is used for returning caller