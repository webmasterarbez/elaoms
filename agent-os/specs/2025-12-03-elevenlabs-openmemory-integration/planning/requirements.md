# Spec Requirements: ElevenLabs OpenMemory Integration

## Initial Description
ElevenLabs Agents Platform integration with OpenMemory for persistent caller profiles and personalized voice AI conversations. This integration will enable:
- Persistent storage of caller profiles using OpenMemory
- Personalized voice AI conversations based on caller history
- ElevenLabs Agents Platform integration capabilities

## Requirements Discussion

### First Round Questions

**Q1:** What is the core architecture for this integration?
**Answer:** FastAPI Python 3.12+ backend with ngrok for local development webhook tunneling. Use ElevenLabs SDK and OpenMemory SDK exclusively (no direct REST APIs). Backend processing only with no frontend. No database required as OpenMemory handles all storage. Primary identifier for users is the caller phone number (`system__caller_id`).

**Q2:** What environment variables are needed?
**Answer:**
- `ELEVENLABS_API_KEY`
- `ELEVENLABS_POST_CALL_KEY` (for HMAC validation)
- `ELEVENLABS_CLIENT_DATA_KEY`
- `ELEVENLABS_SEARCH_DATA_KEY`
- `OPENMEMORY_KEY`
- `OPENMEMORY_PORT`
- `OPENMEMORY_DB_PATH`
- `PAYLOAD_STORAGE_PATH` (configurable directory for conversation payloads)

**Q3:** What webhooks need to be implemented?
**Answer:** Three webhooks are required:
1. POST /webhook/client-data (Conversation Initiation)
2. POST /webhook/search-data (Server Tool - called during conversation)
3. POST /webhook/post-call (Post-Call Processing)

**Q4:** What are the client-data webhook requirements?
**Answer:**
- Input: `caller_id`, `agent_id`, `called_number`, `call_sid`
- NO HMAC authentication required
- Query OpenMemory for user profile using `userId=caller_phone_number`
- Return BOTH `dynamic_variables` AND `conversation_config_override`
- If no profile exists in OpenMemory: return empty/null overrides (let ElevenLabs Agent use defaults)
- Response format: structured JSON with profile data as dynamic variables

**Q5:** What are the search-data webhook requirements?
**Answer:**
- Triggered when ElevenLabs agent invokes a server tool
- NO HMAC authentication required
- Query OpenMemory for relevant memories using the search query
- Response: Structured JSON with profile + relevant memories for dynamic variable injection

**Q6:** What are the post-call webhook requirements?
**Answer:**
- HMAC authentication REQUIRED (30-minute timestamp tolerance)
- Handle THREE webhook types:
  - `post_call_transcription`: Save as `/{conversation_id}/{conversation_id}_transcription.json`
  - `post_call_audio`: Decode base64 MP3, save as `/{conversation_id}/{conversation_id}_audio.mp3`
  - `call_initiation_failure`: Save as `/{conversation_id}/{conversation_id}_failure.json`
- Storage path: Configurable via `PAYLOAD_STORAGE_PATH` env var
- After saving payload, process for OpenMemory:
  - Create/update user profile with relevant info (name from `data_collection_results`, etc.)
  - Store each user message from transcript as individual memory
  - Use `salience=high` and `decayLambda=0` (no decay - permanent memories)
  - Use `userId=caller_phone_number` for multi-tenant isolation

**Q7:** How should OpenMemory be integrated?
**Answer:**
- Use REMOTE mode: `OpenMemory(mode="remote", url=..., apiKey=...)`
- User isolation via `userId` parameter (phone number)
- Automatic sector classification (episodic, semantic, procedural, emotional, reflective)
- Store individual memories (SDK builds profile automatically)
- Retrieve user summary via `/users/{userId}/summary` endpoint
- Key methods: `om.add()`, `om.query()`, user summary endpoints

**Q8:** What HMAC authentication is required?
**Answer:**
- Only required for post-call webhook
- Header: `elevenlabs-signature` with format `t=timestamp,v0=hash`
- Validation: SHA256 HMAC of `{timestamp}.{request_body}`
- Tolerance: 30 minutes
- Secret: `ELEVENLABS_POST_CALL_KEY`

### Existing Code to Reference
No similar existing features identified for reference.

### Follow-up Questions
No follow-up questions were needed.

## Visual Assets

### Files Provided:
No visual assets provided.

### Visual Insights:
N/A - No visual files were provided for this integration specification.

## Requirements Summary

### Functional Requirements
- Three webhook endpoints for ElevenLabs Agent integration
- Client-data webhook for conversation initiation with profile lookup
- Search-data webhook for mid-conversation memory retrieval
- Post-call webhook for transcript/audio storage and memory creation
- OpenMemory SDK integration for persistent caller profiles
- HMAC authentication for post-call webhook security
- Payload storage with configurable directory structure

### Technical Specifications

**Payload Storage Structure:**
```
{PAYLOAD_STORAGE_PATH}/
  {conversation_id}/
    {conversation_id}_transcription.json
    {conversation_id}_audio.mp3
    {conversation_id}_failure.json
```

**Memory Storage Strategy (from post-call transcription):**
1. Extract user info from `data.analysis.data_collection_results` (e.g., first_name: "Stefan")
2. Store profile facts as memories with appropriate metadata
3. Store each `transcript[].role="user"` message as individual memory
4. All memories: `userId=phone_number`, `decayLambda=0` (permanent), high salience

**Client-Data Response Format:**
```json
{
  "dynamic_variables": {
    "user_name": "Stefan",
    "user_profile_summary": "...",
    "last_call_summary": "..."
  },
  "conversation_config_override": {
    "agent": {
      "firstMessage": "Welcome back, Stefan! How can I help you today?"
    }
  }
}
```

**Search-Data Response Format:**
```json
{
  "profile": { "name": "Stefan", "summary": "..." },
  "memories": [
    { "content": "...", "sector": "episodic", "salience": 0.8 }
  ]
}
```

### Reusability Opportunities
- No existing features identified for reuse
- This is a new integration pattern for the codebase

### Scope Boundaries

**In Scope:**
- FastAPI backend with three webhook endpoints
- OpenMemory SDK integration for memory storage and retrieval
- ElevenLabs SDK integration for agent configuration
- HMAC authentication for post-call webhook
- Configurable payload storage directory
- User profile and memory management via phone number
- Dynamic variable injection for personalized conversations
- Conversation config overrides based on caller history

**Out of Scope:**
- Frontend/UI components
- Direct database management (OpenMemory handles storage)
- Direct REST API calls (SDK-only approach)
- Custom memory decay algorithms (using permanent storage)
- Multi-agent orchestration (single agent focus)

### Technical Considerations
- Python 3.12+ required
- FastAPI framework for webhook handling
- ngrok for local development webhook tunneling
- ElevenLabs SDK for agent integration
- OpenMemory SDK in REMOTE mode for memory operations
- SHA256 HMAC for post-call webhook authentication
- Base64 decoding for audio payload handling
- JSON file storage for transcripts and failure logs
- Environment variable configuration for all secrets and paths
