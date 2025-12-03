# Task Breakdown: ElevenLabs OpenMemory Integration

## Overview
Total Tasks: 42
Total Task Groups: 6

This integration builds a FastAPI backend connecting ElevenLabs Agents Platform with OpenMemory for persistent caller profiles and personalized voice AI conversations using phone numbers as the primary identifier.

## Task List

### Project Foundation

#### Task Group 1: Project Setup and Configuration
**Dependencies:** None

- [x] 1.0 Complete project setup and configuration
  - [x] 1.1 Write 4 focused tests for configuration module
    - Test environment variable loading with all required vars present
    - Test validation fails when required vars are missing
    - Test config object properly exposes all settings
    - Test .env file loading via python-dotenv
  - [x] 1.2 Create project directory structure
    - Create `/app/` directory with `__init__.py`
    - Create `/app/webhooks/` directory with `__init__.py`
    - Create `/app/memory/` directory with `__init__.py`
    - Create `/app/auth/` directory with `__init__.py`
    - Create `/app/models/` directory with `__init__.py`
    - Create `/tests/` directory with `__init__.py`
    - Create `/tests/fixtures/` directory
  - [x] 1.3 Create `/requirements.txt` with production dependencies
    - fastapi>=0.109.0
    - uvicorn[standard]>=0.27.0
    - pydantic>=2.5.0
    - python-dotenv>=1.0.0
    - elevenlabs>=1.0.0
    - openmemory-sdk (or mem0ai for OpenMemory)
    - httpx>=0.26.0
  - [x] 1.4 Create `/pyproject.toml` with project metadata and dev dependencies
    - pytest>=7.4.0
    - pytest-asyncio>=0.23.0
    - black>=24.0.0
    - ruff>=0.1.0
    - mypy>=1.8.0
  - [x] 1.5 Create `/.env.example` template file
    - Document all required environment variables with descriptions
    - Include placeholder values for reference
  - [x] 1.6 Create `/app/config.py` configuration module
    - Load environment variables using python-dotenv
    - Define Settings class with all required variables:
      - `ELEVENLABS_API_KEY`
      - `ELEVENLABS_POST_CALL_KEY`
      - `ELEVENLABS_CLIENT_DATA_KEY`
      - `ELEVENLABS_SEARCH_DATA_KEY`
      - `OPENMEMORY_KEY`
      - `OPENMEMORY_PORT`
      - `OPENMEMORY_DB_PATH`
      - `PAYLOAD_STORAGE_PATH`
    - Implement startup validation with descriptive error messages
    - Export singleton settings instance
  - [x] 1.7 Ensure configuration tests pass
    - Run ONLY the 4 tests written in 1.1
    - Verify all configuration loading works correctly

**Acceptance Criteria:**
- All 4 configuration tests pass
- Project structure matches tech-stack.md specification
- All dependencies installable via `pip install -r requirements.txt`
- Configuration fails fast with clear errors when env vars missing

**Files to Create/Modify:**
- `/app/__init__.py`
- `/app/config.py`
- `/app/webhooks/__init__.py`
- `/app/memory/__init__.py`
- `/app/auth/__init__.py`
- `/app/models/__init__.py`
- `/tests/__init__.py`
- `/requirements.txt`
- `/pyproject.toml`
- `/.env.example`

---

### Pydantic Models Layer

#### Task Group 2: Request and Response Models
**Dependencies:** Task Group 1

- [ ] 2.0 Complete Pydantic models for all webhooks
  - [ ] 2.1 Write 6 focused tests for Pydantic models
    - Test ClientDataRequest validation with valid input
    - Test ClientDataResponse serialization with all fields
    - Test PostCallTranscriptionPayload parsing from sample JSON
    - Test SearchDataRequest validation
    - Test invalid phone number format rejection
    - Test optional field handling (null/missing values)
  - [ ] 2.2 Create `/app/models/requests.py` with request models
    - `ClientDataRequest`: caller_id, agent_id, called_number, call_sid
    - `SearchDataRequest`: query, user_id, agent_id, context fields
    - `PostCallWebhookRequest`: type, event_timestamp, data (nested models)
    - `TranscriptEntry`: role, message, time_in_call_secs, tool_calls, etc.
    - `PostCallData`: agent_id, conversation_id, transcript, metadata, analysis
    - `DataCollectionResult`: data_collection_id, value, json_schema, rationale
    - `ConversationInitiationClientData`: dynamic_variables, conversation_config_override
    - Reference: `/home/ubuntu/12022025/elevenlabs_agents_open_memory_system/payloads/post_call_transcription.json`
  - [ ] 2.3 Create `/app/models/responses.py` with response models
    - `DynamicVariables`: user_name, user_profile_summary, last_call_summary
    - `ConversationConfigOverride`: agent config with firstMessage
    - `ClientDataResponse`: dynamic_variables, conversation_config_override
    - `MemoryItem`: content, sector, salience, timestamp
    - `ProfileData`: name, summary, phone_number
    - `SearchDataResponse`: profile, memories array
  - [ ] 2.4 Add field validation and documentation
    - Phone number format validation (E.164 format)
    - Required vs optional field annotations
    - Field descriptions for OpenAPI schema generation
    - Use Pydantic v2 syntax (model_validator, field_validator)
  - [ ] 2.5 Copy sample payloads to test fixtures
    - Copy `/home/ubuntu/12022025/elevenlabs_agents_open_memory_system/payloads/post_call_transcription.json` to `/tests/fixtures/`
    - Create additional sample payloads for client-data and search-data
  - [ ] 2.6 Ensure Pydantic model tests pass
    - Run ONLY the 6 tests written in 2.1
    - Verify models correctly parse sample payloads

**Acceptance Criteria:**
- All 6 model tests pass
- Models correctly parse actual ElevenLabs webhook payloads
- OpenAPI schema generates documentation for all fields
- Validation errors provide clear feedback

**Files to Create/Modify:**
- `/app/models/requests.py`
- `/app/models/responses.py`
- `/app/models/__init__.py`
- `/tests/fixtures/post_call_transcription.json`
- `/tests/fixtures/client_data_request.json`
- `/tests/fixtures/search_data_request.json`

---

### Authentication Layer

#### Task Group 3: HMAC Authentication
**Dependencies:** Task Group 1

- [ ] 3.0 Complete HMAC authentication middleware
  - [ ] 3.1 Write 5 focused tests for HMAC authentication
    - Test valid signature passes verification
    - Test invalid signature returns 401
    - Test expired timestamp (>30 min) returns 401
    - Test malformed signature header returns 401
    - Test missing signature header returns 401
  - [ ] 3.2 Create `/app/auth/hmac.py` with HMAC validation
    - Parse `elevenlabs-signature` header format: `t=timestamp,v0=hash`
    - Extract timestamp and hash components
    - Compute SHA256 HMAC of `{timestamp}.{request_body}`
    - Use `ELEVENLABS_POST_CALL_KEY` as the secret
    - Compare computed hash with `v0` value using constant-time comparison
  - [ ] 3.3 Implement timestamp validation
    - Parse Unix timestamp from signature header
    - Enforce 30-minute (1800 seconds) tolerance window
    - Reject requests outside tolerance with 401 status
  - [ ] 3.4 Create FastAPI dependency for HMAC verification
    - Create async dependency function `verify_hmac_signature`
    - Read raw request body for signature computation
    - Return 401 Unauthorized with descriptive error on failure
    - Make dependency injectable for protected endpoints
  - [ ] 3.5 Ensure HMAC authentication tests pass
    - Run ONLY the 5 tests written in 3.1
    - Verify authentication logic works correctly

**Acceptance Criteria:**
- All 5 HMAC tests pass
- Valid signatures pass authentication
- Invalid/expired signatures return 401 with clear error message
- Timing-safe comparison prevents timing attacks

**Files to Create/Modify:**
- `/app/auth/hmac.py`
- `/app/auth/__init__.py`

---

### Memory Integration Layer

#### Task Group 4: OpenMemory Client and Memory Operations
**Dependencies:** Task Group 1, Task Group 2

- [ ] 4.0 Complete OpenMemory integration layer
  - [ ] 4.1 Write 6 focused tests for memory operations
    - Test OpenMemory client initialization in REMOTE mode
    - Test memory add operation with correct parameters
    - Test memory query operation returns structured results
    - Test user summary retrieval
    - Test userId isolation (phone number as user ID)
    - Test memory storage with decayLambda=0 (permanent retention)
  - [ ] 4.2 Create `/app/memory/client.py` with OpenMemory client wrapper
    - Initialize OpenMemory SDK in REMOTE mode
    - Configure with `url` from OPENMEMORY_PORT and `apiKey` from OPENMEMORY_KEY
    - Export singleton client instance
    - Handle connection errors gracefully
  - [ ] 4.3 Create `/app/memory/profiles.py` for caller profile management
    - `get_user_profile(phone_number)`: Query OpenMemory for user data
    - `get_user_summary(phone_number)`: Retrieve `/users/{userId}/summary`
    - `build_dynamic_variables(profile)`: Format profile data for ElevenLabs response
    - `build_conversation_override(profile)`: Generate personalized firstMessage
    - Handle new callers (no profile) - return None/empty values
  - [ ] 4.4 Create `/app/memory/extraction.py` for transcript processing
    - `extract_user_info(data_collection_results)`: Extract name, etc. from analysis
    - `extract_user_messages(transcript)`: Filter transcript for role="user" messages
    - `create_profile_memories(user_info, phone_number)`: Store profile facts with high salience
    - `store_conversation_memories(messages, phone_number)`: Store each user message
    - All memories: `userId=phone_number`, `decayLambda=0`, appropriate salience
  - [ ] 4.5 Implement memory query for search-data webhook
    - `search_memories(query, phone_number)`: Query OpenMemory with search query
    - Return structured results with profile and memories array
    - Handle empty results gracefully
  - [ ] 4.6 Ensure memory layer tests pass
    - Run ONLY the 6 tests written in 4.1
    - Verify OpenMemory integration works correctly

**Acceptance Criteria:**
- All 6 memory tests pass
- OpenMemory client connects successfully in REMOTE mode
- Memories stored with correct userId and decayLambda=0
- Profile retrieval returns structured data or None for new callers

**Files to Create/Modify:**
- `/app/memory/client.py`
- `/app/memory/profiles.py`
- `/app/memory/extraction.py`
- `/app/memory/__init__.py`

---

### Webhook Endpoints Layer

#### Task Group 5: FastAPI Webhook Handlers
**Dependencies:** Task Group 2, Task Group 3, Task Group 4

- [ ] 5.0 Complete all webhook endpoint handlers
  - [ ] 5.1 Write 8 focused tests for webhook endpoints
    - Test POST /webhook/client-data returns profile for known caller
    - Test POST /webhook/client-data returns empty for new caller
    - Test POST /webhook/search-data returns relevant memories
    - Test POST /webhook/post-call accepts valid HMAC signature
    - Test POST /webhook/post-call rejects invalid signature
    - Test POST /webhook/post-call saves transcription payload
    - Test POST /webhook/post-call saves audio payload (base64 decode)
    - Test GET /health returns healthy status
  - [ ] 5.2 Create `/app/main.py` FastAPI application entry point
    - Initialize FastAPI app with title and description
    - Import and configure startup validation from config
    - Create /health endpoint for service health check
    - Include webhook routers
    - Configure CORS if needed for development
  - [ ] 5.3 Create `/app/webhooks/client_data.py` handler
    - POST /webhook/client-data endpoint
    - NO HMAC authentication (as specified)
    - Parse ClientDataRequest from request body
    - Extract caller phone number from caller_id field
    - Query OpenMemory for user profile using phone number as userId
    - Build DynamicVariables with user_name, user_profile_summary, last_call_summary
    - Build ConversationConfigOverride with personalized firstMessage for returning callers
    - Return empty/null values for new callers (let ElevenLabs use defaults)
    - Return ClientDataResponse
  - [ ] 5.4 Create `/app/webhooks/search_data.py` handler
    - POST /webhook/search-data endpoint
    - NO HMAC authentication (as specified)
    - Parse SearchDataRequest from request body
    - Extract search query and user context
    - Query OpenMemory using om.query() with search query and userId
    - Return SearchDataResponse with profile and memories array
  - [ ] 5.5 Create `/app/webhooks/post_call.py` handler
    - POST /webhook/post-call endpoint
    - HMAC authentication REQUIRED (use verify_hmac_signature dependency)
    - Parse PostCallWebhookRequest from request body
    - Handle three webhook types based on `type` field:
      - `post_call_transcription`: Process and save transcription
      - `post_call_audio`: Decode base64 and save audio
      - `call_initiation_failure`: Save failure log
  - [ ] 5.6 Implement payload storage in post_call.py
    - Extract conversation_id from payload
    - Create directory: `{PAYLOAD_STORAGE_PATH}/{conversation_id}/`
    - Save transcription as `{conversation_id}_transcription.json`
    - Decode base64 audio and save as `{conversation_id}_audio.mp3`
    - Save failures as `{conversation_id}_failure.json`
    - Handle file system errors gracefully
  - [ ] 5.7 Implement memory processing in post_call.py
    - Extract caller phone number from `data.conversation_initiation_client_data.dynamic_variables.system__caller_id`
    - Extract user info from `data.analysis.data_collection_results`
    - Store profile facts as memories with salience=high, decayLambda=0
    - Store each transcript entry where role="user" as individual memory
    - Tag all memories with userId=phone_number
  - [ ] 5.8 Ensure webhook tests pass
    - Run ONLY the 8 tests written in 5.1
    - Verify all endpoints respond correctly

**Acceptance Criteria:**
- All 8 webhook tests pass
- /webhook/client-data returns personalized data for known callers
- /webhook/search-data returns relevant memories from OpenMemory
- /webhook/post-call validates HMAC and processes all webhook types
- Payloads saved to correct file paths with proper naming
- Memories extracted and stored in OpenMemory with correct metadata

**Files to Create/Modify:**
- `/app/main.py`
- `/app/webhooks/client_data.py`
- `/app/webhooks/search_data.py`
- `/app/webhooks/post_call.py`
- `/app/webhooks/__init__.py`

---

### Testing and Integration

#### Task Group 6: Test Review, Gap Analysis, and Local Development
**Dependencies:** Task Groups 1-5

- [ ] 6.0 Review existing tests and fill critical gaps
  - [ ] 6.1 Review tests from Task Groups 1-5
    - Review 4 tests from Task Group 1 (configuration)
    - Review 6 tests from Task Group 2 (Pydantic models)
    - Review 5 tests from Task Group 3 (HMAC auth)
    - Review 6 tests from Task Group 4 (memory operations)
    - Review 8 tests from Task Group 5 (webhooks)
    - Total existing tests: approximately 29 tests
  - [ ] 6.2 Analyze test coverage gaps for integration
    - Identify critical end-to-end workflows lacking coverage
    - Focus on integration points between memory and webhooks
    - Prioritize full conversation lifecycle testing
    - Do NOT assess entire application coverage
  - [ ] 6.3 Write up to 8 additional integration tests
    - Test full client-data flow: request -> OpenMemory query -> response
    - Test full post-call flow: auth -> payload save -> memory store
    - Test returning caller personalization end-to-end
    - Test new caller handling end-to-end
    - Test error handling for OpenMemory connection failures
    - Test error handling for invalid payload formats
    - Add tests only for critical gaps identified
    - Maximum 8 new tests
  - [ ] 6.4 Create `/tests/conftest.py` with shared fixtures
    - Mock OpenMemory client fixture
    - Sample request payload fixtures
    - Test client fixture for FastAPI
    - Environment variable fixtures
  - [ ] 6.5 Run all feature-specific tests
    - Run all tests from Task Groups 1-5 plus new integration tests
    - Expected total: approximately 35-37 tests
    - Verify all tests pass
    - Fix any failing tests
  - [ ] 6.6 Create local development setup documentation
    - Document ngrok setup for webhook tunneling
    - Provide example ngrok commands
    - Document how to configure ElevenLabs webhook URLs
    - Add troubleshooting tips for common issues
  - [ ] 6.7 Create `/scripts/run_local.sh` for local development
    - Start uvicorn server with hot reload
    - Configure appropriate host/port bindings
    - Load environment from .env file
  - [ ] 6.8 Manual integration testing checklist
    - Test with ngrok tunnel and live ElevenLabs agent
    - Verify client-data webhook receives calls
    - Verify search-data webhook works during conversation
    - Verify post-call webhook receives and processes transcriptions
    - Verify memories persist and are retrieved on subsequent calls

**Acceptance Criteria:**
- All feature tests pass (approximately 35-37 total)
- Critical integration workflows have test coverage
- Local development setup documented and functional
- ngrok tunneling works for webhook testing
- Manual testing checklist completed successfully

**Files to Create/Modify:**
- `/tests/conftest.py`
- `/tests/test_config.py`
- `/tests/test_models.py`
- `/tests/test_auth.py`
- `/tests/test_memory.py`
- `/tests/test_webhooks.py`
- `/tests/test_integration.py`
- `/scripts/run_local.sh`

---

## Execution Order

Recommended implementation sequence:

```
1. Task Group 1: Project Setup and Configuration
   - Foundation for all other work
   - No dependencies

2. Task Group 2: Pydantic Models
   - Required for webhook handlers
   - Depends on: Task Group 1

3. Task Group 3: HMAC Authentication
   - Required for post-call webhook
   - Depends on: Task Group 1
   - Can run in parallel with Task Group 2

4. Task Group 4: OpenMemory Client and Memory Operations
   - Core memory functionality
   - Depends on: Task Group 1, Task Group 2

5. Task Group 5: Webhook Endpoints
   - Main feature implementation
   - Depends on: Task Groups 2, 3, 4

6. Task Group 6: Test Review and Local Development
   - Final validation and integration testing
   - Depends on: Task Groups 1-5
```

## Parallel Execution Opportunities

The following task groups can be worked on in parallel:
- Task Group 2 (Pydantic Models) and Task Group 3 (HMAC Auth) - both depend only on Task Group 1
- Within Task Group 5, different webhook handlers can be developed in parallel after models and auth are complete

## Key File References

### Sample Payloads (for model development)
- `/home/ubuntu/12022025/elevenlabs_agents_open_memory_system/payloads/post_call_transcription.json`
- `/home/ubuntu/12022025/elevenlabs_agents_open_memory_system/payloads/client_data.json`

### Standards and Patterns
- `/home/ubuntu/12022025/elevenlabs_agents_open_memory_system/agent-os/product/tech-stack.md`
- `/home/ubuntu/12022025/elevenlabs_agents_open_memory_system/agent-os/standards/backend/api.md`

### Specification Documents
- `/home/ubuntu/12022025/elevenlabs_agents_open_memory_system/agent-os/specs/2025-12-03-elevenlabs-openmemory-integration/spec.md`
- `/home/ubuntu/12022025/elevenlabs_agents_open_memory_system/agent-os/specs/2025-12-03-elevenlabs-openmemory-integration/planning/requirements.md`

## Environment Variables Summary

```bash
# ElevenLabs Configuration
ELEVENLABS_API_KEY=           # Primary API key for ElevenLabs SDK
ELEVENLABS_POST_CALL_KEY=     # HMAC secret for post-call webhook (required)
ELEVENLABS_CLIENT_DATA_KEY=   # HMAC secret for client-data webhook (optional, not used)
ELEVENLABS_SEARCH_DATA_KEY=   # HMAC secret for search-data webhook (optional, not used)

# OpenMemory Configuration
OPENMEMORY_KEY=               # OpenMemory API key for authentication
OPENMEMORY_PORT=              # OpenMemory service port/URL
OPENMEMORY_DB_PATH=           # Path to OpenMemory database (local mode reference)

# Storage Configuration
PAYLOAD_STORAGE_PATH=         # Directory for saving conversation payloads
```
