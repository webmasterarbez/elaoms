# Specification: ElevenLabs OpenMemory Integration

## Goal
Build a FastAPI backend that integrates ElevenLabs Agents Platform with OpenMemory to enable persistent caller profiles and personalized voice AI conversations using phone numbers as the primary identifier.

## User Stories
- As a Voice AI Provider, I want callers to be recognized instantly by phone number so that personalized greetings and context-aware conversations begin without friction
- As a Conversational AI Developer, I want a simple webhook architecture with SDK-based integration so that I can deploy memory-enabled voice AI without managing databases

## Specific Requirements

**Environment Configuration**
- Load all configuration from environment variables using python-dotenv
- Required variables: `ELEVENLABS_API_KEY`, `ELEVENLABS_POST_CALL_KEY`, `ELEVENLABS_CLIENT_DATA_KEY`, `ELEVENLABS_SEARCH_DATA_KEY`, `OPENMEMORY_KEY`, `OPENMEMORY_PORT`, `OPENMEMORY_DB_PATH`, `PAYLOAD_STORAGE_PATH`
- Validate all required environment variables on application startup
- Fail fast with descriptive error messages if configuration is invalid

**OpenMemory Client Initialization**
- Initialize OpenMemory SDK in REMOTE mode with `url` and `apiKey` from environment
- Configure memory operations with `decayLambda=0` for permanent retention
- Use `userId=caller_phone_number` for multi-tenant isolation
- Primary methods: `om.add()` for storing memories, `om.query()` for retrieval
- Retrieve user summaries via `/users/{userId}/summary` endpoint

**Client Data Webhook (POST /webhook/client-data)**
- Input fields: `caller_id`, `agent_id`, `called_number`, `call_sid`
- NO HMAC authentication required for this endpoint
- Query OpenMemory for user profile using `userId=caller_phone_number`
- Return `dynamic_variables` object with `user_name`, `user_profile_summary`, `last_call_summary`
- Return `conversation_config_override` with personalized `firstMessage` for returning callers
- For new callers (no profile): return empty/null overrides to use ElevenLabs defaults

**Search Data Webhook (POST /webhook/search-data)**
- Triggered when ElevenLabs agent invokes a server tool during conversation
- NO HMAC authentication required
- Extract search query from request payload
- Query OpenMemory using `om.query()` with the search query and `userId`
- Return structured JSON with `profile` object and `memories` array containing relevant memories

**Post-Call Webhook (POST /webhook/post-call)**
- HMAC authentication REQUIRED using `ELEVENLABS_POST_CALL_KEY`
- Handle three webhook types: `post_call_transcription`, `post_call_audio`, `call_initiation_failure`
- Extract `conversation_id` and create directory structure under `PAYLOAD_STORAGE_PATH`
- Save transcription as `/{conversation_id}/{conversation_id}_transcription.json`
- Decode base64 audio and save as `/{conversation_id}/{conversation_id}_audio.mp3`
- Save failures as `/{conversation_id}/{conversation_id}_failure.json`

**HMAC Authentication Implementation**
- Parse `elevenlabs-signature` header with format `t=timestamp,v0=hash`
- Compute SHA256 HMAC of `{timestamp}.{request_body}` using `ELEVENLABS_POST_CALL_KEY`
- Compare computed hash with `v0` value from header
- Enforce 30-minute timestamp tolerance window
- Return 401 Unauthorized for failed validation

**Memory Storage from Post-Call Processing**
- Extract caller phone number from `data.conversation_initiation_client_data.dynamic_variables.system__caller_id`
- Extract user info from `data.analysis.data_collection_results` (e.g., `first_name`)
- Store profile facts as memories with `salience=high` and `decayLambda=0`
- Store each `transcript[].role="user"` message as individual memory
- All memories tagged with `userId=phone_number` for isolation

**Pydantic Request/Response Models**
- Create strict Pydantic models for all webhook request payloads
- Create response models for `dynamic_variables` and `conversation_config_override`
- Use appropriate field validation (e.g., phone number format, required fields)
- Document fields with descriptions for OpenAPI schema generation

## Visual Design
No visual assets provided - this is a backend-only integration with no UI components.

## Existing Code to Leverage

**Sample Post-Call Transcription Payload (`/home/ubuntu/12022025/elevenlabs_agents_open_memory_system/payloads/post_call_transcription.json`)**
- Contains actual ElevenLabs webhook payload structure
- Shows transcript array format with `role`, `message`, `time_in_call_secs`
- Demonstrates `data_collection_results` structure for extracting user info
- Shows `dynamic_variables` with `system__caller_id` phone number path
- Use this as reference for Pydantic model definitions

**Sample Client Data Payload (`/home/ubuntu/12022025/elevenlabs_agents_open_memory_system/payloads/client_data.json`)**
- Documents input fields: `caller_id`, `agent_id`, `called_number`, `call_sid`
- Use as reference for client-data webhook request model

**Project Structure from Tech Stack (`/home/ubuntu/12022025/elevenlabs_agents_open_memory_system/agent-os/product/tech-stack.md`)**
- Follow prescribed directory layout: `app/`, `webhooks/`, `memory/`, `auth/`, `models/`
- Use established patterns for configuration loading and module organization

**Backend Standards (`/home/ubuntu/12022025/elevenlabs_agents_open_memory_system/agent-os/standards/backend/api.md`)**
- Apply RESTful design principles with appropriate HTTP status codes
- Use consistent naming conventions for endpoints

## Out of Scope
- Frontend/UI components - backend processing only
- Direct database management - OpenMemory handles all storage internally
- Direct REST API calls to ElevenLabs or OpenMemory - SDK-only approach required
- Custom memory decay algorithms - using permanent storage with `decayLambda=0`
- Multi-agent orchestration - single agent focus for this integration
- WebSocket or streaming endpoints - webhook-based architecture only
- User authentication beyond HMAC - no user login or session management
- Audio transcription processing - ElevenLabs provides transcripts
- Custom voice synthesis - using ElevenLabs default voice configuration
- Rate limiting implementation - rely on upstream service limits
