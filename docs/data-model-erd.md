# Data Model - Entity Relationship Diagram

## ElevenLabs Agents + OpenMemory Integration

This document provides a comprehensive Entity Relationship Diagram (ERD) for the voice AI agent system with persistent memory capabilities.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              ELEVENLABS AGENTS                                  │
│                           (Voice AI Platform)                                   │
└─────────────────────────────────────────────────────────────────────────────────┘
                │                    │                    │
                ▼                    ▼                    ▼
    ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
    │  Client-Data      │ │   Search-Data     │ │   Post-Call       │
    │  Webhook          │ │   Webhook         │ │   Webhook         │
    └─────────┬─────────┘ └─────────┬─────────┘ └─────────┬─────────┘
              │                     │                     │
              ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           APPLICATION LAYER                                     │
│              (FastAPI Webhooks + Request/Response Models)                       │
└─────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              OPENMEMORY                                         │
│                    (Persistent Long-Term Memory Engine)                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐           │
│  │   Semantic   │ │   Episodic   │ │  Procedural  │ │  Emotional   │           │
│  │   Memory     │ │   Memory     │ │   Memory     │ │   Memory     │           │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘           │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              REQUEST MODELS                                     │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────┐     ┌─────────────────────────────┐
│    ClientDataRequest        │     │    SearchDataRequest        │
├─────────────────────────────┤     ├─────────────────────────────┤
│ PK caller_id: str (E.164)   │     │    query: str               │
│    agent_id: str            │     │ PK user_id: str (E.164)     │
│    called_number: str       │     │    agent_id: str            │
│    call_sid: str            │     │    conversation_id: str?    │
└─────────────────────────────┘     │    context: dict?           │
              │                     └─────────────────────────────┘
              │                                   │
              │  triggers                         │  triggers
              ▼                                   ▼
┌─────────────────────────────┐     ┌─────────────────────────────┐
│    ClientDataResponse       │     │    SearchDataResponse       │
├─────────────────────────────┤     ├─────────────────────────────┤
│    dynamic_variables:       │     │    profile: ProfileData?    │────┐
│      DynamicVariables?      │     │    memories: MemoryItem[]   │────┼──┐
│    conversation_config_     │     └─────────────────────────────┘    │  │
│      override:              │                                        │  │
│      ConversationConfig?    │                                        │  │
└─────────────────────────────┘                                        │  │
              │                                                        │  │
              ▼                                                        │  │
┌─────────────────────────────┐     ┌─────────────────────────────┐   │  │
│    DynamicVariables         │     │    ProfileData              │◄──┘  │
├─────────────────────────────┤     ├─────────────────────────────┤      │
│    user_name: str?          │     │    name: str?               │      │
│    user_profile_summary: ?  │     │    summary: str?            │      │
│    last_call_summary: str?  │     │    phone_number: str?       │      │
└─────────────────────────────┘     └─────────────────────────────┘      │
                                                                          │
              ┌─────────────────────────────────────────────────────────┘
              ▼
┌─────────────────────────────┐
│    MemoryItem               │
├─────────────────────────────┤
│    content: str             │
│    sector: MemorySector     │
│    salience: float (0-1)    │
│    timestamp: datetime?     │
└─────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────────┐
│                           POST-CALL WEBHOOK MODELS                              │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────┐
│    PostCallWebhookRequest       │
├─────────────────────────────────┤
│    type: WebhookType            │ ◄── "post_call_transcription" | "post_call_audio" | "call_initiation_failure"
│    event_timestamp: int         │
│    data: PostCallData           │────────┐
└─────────────────────────────────┘        │
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│    PostCallData                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│ PK agent_id: str                                                                │
│ PK conversation_id: str                                                         │
│    status: str                                                                  │
│    user_id: str?                                                                │
│    branch_id: str?                                                              │
│    has_audio: bool                                                              │
│    has_user_audio: bool                                                         │
│    has_response_audio: bool                                                     │
└─────────────────────────────────────────────────────────────────────────────────┘
              │                    │                    │                    │
              │                    │                    │                    │
    ┌─────────┘         ┌──────────┘         ┌─────────┘         ┌──────────┘
    ▼                   ▼                    ▼                   ▼
┌────────────┐   ┌────────────────┐   ┌────────────┐   ┌─────────────────────────┐
│ transcript │   │   metadata     │   │  analysis  │   │ conversation_initiation │
│ []         │   │                │   │            │   │ _client_data            │
└─────┬──────┘   └───────┬────────┘   └──────┬─────┘   └────────────┬────────────┘
      │                  │                   │                      │
      ▼                  ▼                   ▼                      ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────┐
│ TranscriptEntry │ │  CallMetadata   │ │    Analysis     │ │ConversationInit...  │
├─────────────────┤ ├─────────────────┤ ├─────────────────┤ ├─────────────────────┤
│ role: agent|    │ │ start_time: int?│ │ evaluation_     │ │ conversation_config │
│       user      │ │ end_time: int?  │ │   criteria_     │ │   _override: ...?   │
│ message: str    │ │ call_duration:? │ │   results:dict  │ │ custom_llm_extra_   │
│ time_in_call:   │ │ cost: float?    │ │ data_collection │ │   body: dict        │
│   int           │ │ termination_    │ │   _results:dict │ │ user_id: str?       │
│ tool_calls: []  │ │   reason: str?  │ │ call_successful │ │ source_info:        │
│ tool_results: []│ │ error: str?     │ │   : str?        │ │   SourceInfo?       │
│ interrupted:    │ │ warnings: []    │ │ transcript_     │ │ dynamic_variables:  │
│   bool          │ │ main_language:? │ │   summary: str? │ │   dict              │
│ source_medium:? │ │ text_only: bool │ │ call_summary_   │ └─────────────────────┘
│ llm_usage: dict?│ │ timezone: str?  │ │   title: str?   │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐    │    │    │    │    ┌─────────────────────────┐
│ AgentMetadata   │    │    │    │    │    │ DataCollectionResult    │
├─────────────────┤    │    │    │    │    ├─────────────────────────┤
│ agent_id: str   │    │    │    │    │    │ data_collection_id: str │
│ branch_id: str? │    │    │    │    │    │ value: Any?             │
│ workflow_node_  │    │    │    │    │    │ json_schema:            │
│   id: str?      │    │    │    │    │    │   DataCollectionJson?   │
└─────────────────┘    │    │    │    │    │ rationale: str?         │
                       │    │    │    │    └────────────┬────────────┘
┌─────────────────┐    │    │    │    │                 │
│ConversationTurn │    │    │    │    │                 ▼
│  Metrics        │    │    │    │    │    ┌─────────────────────────┐
├─────────────────┤    │    │    │    │    │ DataCollectionJsonSchema│
│ metrics: dict   │    │    │    │    │    ├─────────────────────────┤
└─────────────────┘    │    │    │    │    │ type: str               │
                       │    │    │    │    │ description: str?       │
                       ▼    ▼    ▼    ▼    │ enum: str[]?            │
                  CallMetadata Contains:   │ is_system_provided:bool │
                  ┌────────────────────┐   │ dynamic_variable: str?  │
                  │ deletion_settings  │   │ constant_value: str?    │
                  │ feedback           │   └─────────────────────────┘
                  │ phone_call         │
                  │ features_usage     │
                  └─────────┬──────────┘
                            │
        ┌───────────┬───────┴───────┬───────────┐
        ▼           ▼               ▼           ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────────────┐
│ Deletion     │ │ Metadata     │ │ PhoneCall    │ │ FeaturesUsage      │
│ Settings     │ │ Feedback     │ │ Info         │ ├────────────────────┤
├──────────────┤ ├──────────────┤ ├──────────────┤ │ language_detection │
│ deletion_    │ │ type: str?   │ │ type: str    │ │ transfer_to_agent  │
│   time: int? │ │ overall_     │ │ stream_sid:? │ │ transfer_to_number │
│ deleted_logs │ │   score: ?   │ │ call_sid: ?  │ │ multivoice         │
│   _at: int?  │ │ likes: int   │ └──────────────┘ │ dtmf_tones         │
│ deleted_audio│ │ dislikes: int│                  │ external_mcp_      │
│   _at: int?  │ │ rating: ?    │                  │   servers          │
│ deleted_     │ │ comment: str?│                  │ tool_dynamic_var_  │
│   transcript │ └──────────────┘                  │   updates          │
│   _at: int?  │                                   │ voicemail_         │
│ delete_      │                                   │   detection        │
│   transcript │                                   │ workflow:          │
│   _and_pii:  │                                   │   WorkflowFeatures?│
│   bool       │                                   │ agent_testing:     │
│ delete_audio │                                   │   AgentTesting?    │
│   : bool     │                                   └────────────────────┘
└──────────────┘


┌─────────────────────────────────────────────────────────────────────────────────┐
│                           OPENMEMORY MODELS                                     │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                                   User                                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│ PK userId: str (phone number E.164)                                             │
│    name: str?                                                                   │
│    summary: str?                                                                │
│    memoryCount: int                                                             │
└─────────────────────────────────────────────────────────────────────────────────┘
              │
              │ 1:N
              ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                 Memory                                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│ PK id: str (auto-generated)                                                     │
│ FK userId: str (phone number E.164)                                             │
│    content: str                                                                 │
│    sector: MemorySector                                                         │
│    salience: float (0.0 - 1.0)                                                  │
│    decayLambda: int (0 = permanent)                                             │
│    tags: str[]                                                                  │
│    metadata: dict                                                               │
│    createdAt: datetime                                                          │
│    lastAccessedAt: datetime?                                                    │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────┐
│    MemorySector (Enum)          │
├─────────────────────────────────┤
│  • semantic   - Facts/knowledge │
│  • episodic   - Events/convos   │
│  • procedural - How-to/skills   │
│  • emotional  - Feelings        │
│  • reflective - Meta-thoughts   │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│    Salience Levels              │
├─────────────────────────────────┤
│  HIGH_SALIENCE   = 0.9          │
│  MEDIUM_SALIENCE = 0.7          │
│  LOW_SALIENCE    = 0.3          │
└─────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────────────────┐
│                           CONFIGURATION MODELS                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                                 Settings                                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ELEVENLABS_API_KEY: str              │  Primary API key for ElevenLabs         │
│  ELEVENLABS_POST_CALL_KEY: str        │  HMAC secret for post-call webhook      │
│  ELEVENLABS_CLIENT_DATA_KEY: str      │  HMAC secret for client-data webhook    │
│  ELEVENLABS_SEARCH_DATA_KEY: str      │  HMAC secret for search-data webhook    │
│  OPENMEMORY_KEY: str                  │  OpenMemory API key                     │
│  OPENMEMORY_PORT: str                 │  OpenMemory service port/URL            │
│  OPENMEMORY_DB_PATH: str              │  Path to OpenMemory database            │
│  PAYLOAD_STORAGE_PATH: str            │  Directory for conversation payloads    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Relationships

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           CONVERSATION LIFECYCLE                                │
└─────────────────────────────────────────────────────────────────────────────────┘

                            CALL INITIATED
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                    1. CLIENT-DATA WEBHOOK                       │
    │  ┌─────────────────────────────────────────────────────────┐   │
    │  │  ClientDataRequest                                       │   │
    │  │  ├── caller_id (phone) ──────────┐                       │   │
    │  │  ├── agent_id                    │                       │   │
    │  │  ├── called_number               │                       │   │
    │  │  └── call_sid                    │                       │   │
    │  └──────────────────────────────────┼───────────────────────┘   │
    │                                     │                           │
    │                                     ▼                           │
    │                          ┌──────────────────┐                   │
    │                          │   OpenMemory     │                   │
    │                          │   Query Profile  │                   │
    │                          └────────┬─────────┘                   │
    │                                   │                             │
    │                                   ▼                             │
    │  ┌─────────────────────────────────────────────────────────┐   │
    │  │  ClientDataResponse                                      │   │
    │  │  ├── dynamic_variables                                   │   │
    │  │  │   ├── user_name                                       │   │
    │  │  │   ├── user_profile_summary                            │   │
    │  │  │   └── last_call_summary                               │   │
    │  │  └── conversation_config_override                        │   │
    │  │      └── agent.first_message                             │   │
    │  └─────────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                           CONVERSATION ACTIVE
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │              2. SEARCH-DATA WEBHOOK (During Call)               │
    │  ┌─────────────────────────────────────────────────────────┐   │
    │  │  SearchDataRequest                                       │   │
    │  │  ├── query ─────────────────────┐                        │   │
    │  │  ├── user_id (phone)            │                        │   │
    │  │  ├── agent_id                   │                        │   │
    │  │  └── conversation_id            │                        │   │
    │  └─────────────────────────────────┼────────────────────────┘   │
    │                                    │                            │
    │                                    ▼                            │
    │                          ┌──────────────────┐                   │
    │                          │   OpenMemory     │                   │
    │                          │   Search Memories│                   │
    │                          └────────┬─────────┘                   │
    │                                   │                             │
    │                                   ▼                             │
    │  ┌─────────────────────────────────────────────────────────┐   │
    │  │  SearchDataResponse                                      │   │
    │  │  ├── profile                                             │   │
    │  │  │   ├── name                                            │   │
    │  │  │   ├── summary                                         │   │
    │  │  │   └── phone_number                                    │   │
    │  │  └── memories[]                                          │   │
    │  │      ├── content                                         │   │
    │  │      ├── sector                                          │   │
    │  │      ├── salience                                        │   │
    │  │      └── timestamp                                       │   │
    │  └─────────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                            CALL COMPLETED
                                  │
                                  ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                   3. POST-CALL WEBHOOK                          │
    │  ┌─────────────────────────────────────────────────────────┐   │
    │  │  PostCallWebhookRequest                                  │   │
    │  │  ├── type: "post_call_transcription"                     │   │
    │  │  ├── event_timestamp                                     │   │
    │  │  └── data: PostCallData                                  │   │
    │  │      ├── transcript[]                                    │   │
    │  │      ├── analysis.data_collection_results                │   │
    │  │      │   ├── first_name                                  │   │
    │  │      │   ├── email                                       │   │
    │  │      │   └── preferences...                              │   │
    │  │      └── conversation_initiation_client_data             │   │
    │  │          └── dynamic_variables.system__caller_id         │   │
    │  └─────────────────────────────────┬────────────────────────┘   │
    │                                    │                            │
    │                                    ▼                            │
    │                          ┌──────────────────┐                   │
    │                          │   OpenMemory     │                   │
    │                          │   Store Memories │                   │
    │                          └────────┬─────────┘                   │
    │                                   │                             │
    │                                   ▼                             │
    │             ┌─────────────────────────────────────────┐         │
    │             │  Memories Created:                      │         │
    │             │  • Profile (semantic, salience=0.9)     │         │
    │             │  • Conversation (episodic, salience=0.7)│         │
    │             └─────────────────────────────────────────┘         │
    └─────────────────────────────────────────────────────────────────┘
```

---

## UI Data Models

For frontend applications consuming this API, the following TypeScript interfaces are recommended:

```typescript
// User/Caller Identity
interface User {
  phoneNumber: string;      // E.164 format (+16129782029)
  name?: string;
  profileSummary?: string;
  lastCallSummary?: string;
}

// Memory Display
interface MemoryDisplay {
  content: string;
  sector: 'semantic' | 'episodic' | 'procedural' | 'emotional' | 'reflective';
  salience: number;         // 0.0 - 1.0
  timestamp?: Date;
  salienceLabel: 'High' | 'Medium' | 'Low';
}

// Conversation Transcript
interface TranscriptMessage {
  role: 'agent' | 'user';
  message: string;
  timeInCallSecs: number;
  interrupted: boolean;
}

// Call Summary
interface CallSummary {
  conversationId: string;
  agentId: string;
  status: string;
  duration?: number;
  cost?: number;
  summary?: string;
  title?: string;
  successful?: boolean;
}

// Analytics Dashboard
interface CallAnalytics {
  totalCalls: number;
  successRate: number;
  avgDuration: number;
  totalCost: number;
  dataCollected: {
    fieldId: string;
    value: any;
    count: number;
  }[];
}
```

---

## Relationship Summary

| Relationship | Type | Description |
|--------------|------|-------------|
| User → Memory | 1:N | Each user can have multiple memories |
| PostCallData → TranscriptEntry | 1:N | Each call has multiple transcript entries |
| PostCallData → Analysis | 1:1 | Each call has one analysis result |
| Analysis → DataCollectionResult | 1:N | Analysis contains multiple collected fields |
| CallMetadata → DeletionSettings | 1:1 | Each call has deletion settings |
| CallMetadata → FeaturesUsage | 1:1 | Each call tracks feature usage |
| FeaturesUsage → FeatureUsageItem | 1:N | Multiple feature items per call |

---

## Key Identifiers

| Entity | Primary Key | Format | Example |
|--------|-------------|--------|---------|
| User | phoneNumber | E.164 | +16129782029 |
| Call | call_sid | Twilio SID | CA123... |
| Conversation | conversation_id | UUID | 550e8400-e29b... |
| Agent | agent_id | ElevenLabs ID | agent_abc123 |
| Memory | id | Auto-generated | mem_xyz789 |

---

## Validation Rules

| Field | Rule | Pattern |
|-------|------|---------|
| phoneNumber | E.164 format | `^\+[1-9]\d{1,14}$` |
| salience | Range | 0.0 - 1.0 |
| sector | Enum | semantic, episodic, procedural, emotional, reflective |
| timestamp | Unix epoch | Seconds since 1970-01-01 |
| webhook type | Enum | post_call_transcription, post_call_audio, call_initiation_failure |