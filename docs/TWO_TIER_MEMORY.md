# Two-Tier Memory Architecture

This document explains the two-tier memory architecture used in ELAOMS for managing caller profiles and agent-specific conversation states.

## Overview

ELAOMS uses a two-tier memory system to enable:
1. **Cross-agent caller recognition** - Any agent can recognize a returning caller
2. **Per-agent relationship continuity** - Each agent maintains its own relationship history with each caller

```
┌─────────────────────────────────────────────────────────────────┐
│                    ELAOMS Memory Architecture                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              TIER 1: Universal User Profile               │   │
│  │                    (Cross-Agent Shared)                   │   │
│  │                                                           │   │
│  │  Storage Key: user:{phone_number}:profile                 │   │
│  │                                                           │   │
│  │  ┌─────────────────────────────────────────────────────┐ │   │
│  │  │ • name: "Stefan"                                     │ │   │
│  │  │ • phone_number: "+16125551234"                       │ │   │
│  │  │ • first_seen: "2024-01-15T10:00:00Z"                │ │   │
│  │  │ • total_interactions: 7                              │ │   │
│  │  └─────────────────────────────────────────────────────┘ │   │
│  │                                                           │   │
│  │  Accessible by: ALL agents                                │   │
│  │  Created: First call to ANY agent                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │           TIER 2: Agent-Specific Conversation State       │   │
│  │                      (Per-Agent Isolated)                 │   │
│  │                                                           │   │
│  │  Storage Key: user:{phone}:agent:{agent_id}:next_greeting │   │
│  │                                                           │   │
│  │  ┌─────────────────┐  ┌─────────────────┐                │   │
│  │  │   Agent: Margaret│  │   Agent: Dr. Sarah│              │   │
│  │  │                  │  │                   │              │   │
│  │  │ next_greeting:   │  │ next_greeting:    │              │   │
│  │  │ "Hi Stefan!..."  │  │ "Welcome back..." │              │   │
│  │  │                  │  │                   │              │   │
│  │  │ key_topics:      │  │ key_topics:       │              │   │
│  │  │ - founding story │  │ - health concerns │              │   │
│  │  │ - childhood      │  │ - medication      │              │   │
│  │  │                  │  │                   │              │   │
│  │  │ sentiment:       │  │ sentiment:        │              │   │
│  │  │ "engaged"        │  │ "satisfied"       │              │   │
│  │  │                  │  │                   │              │   │
│  │  │ conv_count: 3    │  │ conv_count: 2     │              │   │
│  │  └─────────────────┘  └─────────────────┘                │   │
│  │                                                           │   │
│  │  Accessible by: ONLY the specific agent                   │   │
│  │  Created: After first call with each agent                │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Why Two-Tier Architecture?

### The Problem with Single-Tier

A single-tier approach where all data is shared creates issues:
- Agent A's conversation context bleeds into Agent B's responses
- No way to maintain unique "relationships" between each agent and caller
- Generic greetings that don't reflect agent-specific history

### The Solution

Two-tier architecture solves this by separating:
- **Identity data** (who is this person?) - Shared across agents
- **Relationship data** (what's our history?) - Isolated per agent

## Tier 1: Universal User Profile

### Purpose
Basic caller identity information shared by ALL agents for recognition.

### Storage Pattern
```
Key: user:{phone_number}:profile
Tags: ["universal_profile", "name", "first_seen", "total_interactions"]
```

### Contents
| Field | Type | Description |
|-------|------|-------------|
| `name` | string \| null | Caller's name (extracted from any conversation) |
| `phone_number` | string | E.164 formatted phone number |
| `first_seen` | string | ISO timestamp of first interaction with any agent |
| `total_interactions` | int | Count of calls across ALL agents |

### Lifecycle
1. **Created**: On first call to ANY agent in the system
2. **Updated**: After each call (increment interactions, update name if discovered)
3. **Name Protection**: Once a name is set, it's never overwritten

### Access Pattern
- **Read**: All agents query this to recognize returning callers
- **Write**: Post-call webhook updates after each conversation

## Tier 2: Agent-Specific Conversation State

### Purpose
Each agent's personalized relationship with a specific caller, including the pre-generated greeting for their next call.

### Storage Pattern
```
Key: user:{phone_number}:agent:{agent_id}:next_greeting
Tags: ["agent_state", "{agent_id}", "next_greeting"]
```

### Contents
| Field | Type | Description |
|-------|------|-------------|
| `next_greeting` | string \| null | OpenAI-generated personalized greeting |
| `key_topics` | list[string] | 3-5 specific topics from last conversation |
| `sentiment` | string | Caller sentiment: satisfied/neutral/frustrated/confused |
| `conversation_summary` | string | One-sentence summary of last call |
| `last_call_date` | string | ISO timestamp of last call with THIS agent |
| `conversation_count` | int | Number of calls with THIS specific agent |

### Lifecycle
1. **Created**: After first conversation with a specific agent
2. **Updated**: After each subsequent conversation
3. **Generated By**: OpenAI analyzes transcript + context to create next greeting

### Access Pattern
- **Read**: Only the specific agent reads its own state
- **Write**: Post-call webhook generates and stores after each call

## OpenAI Greeting Generation

The greeting generation happens in the post-call webhook using OpenAI's GPT-4o-mini model.

### Input Data
```python
{
    "agent_profile": {
        "agent_id": "agent_xyz",
        "agent_name": "Margaret",
        "first_message": "Hello, I'm Margaret...",
        "system_prompt": "You are a memoir interviewer..."
    },
    "user_profile": {
        "name": "Stefan",
        "phone_number": "+16125551234",
        "total_interactions": 5
    },
    "transcript": "Agent: Hello!...\nUser: Hi, my name is Stefan...",
    "conversation_metadata": {
        "duration": 180,
        "last_call_date": "2024-01-15T10:00:00Z"
    }
}
```

### Output Format
```json
{
    "next_greeting": "Hi Stefan! I've been thinking about your Arbez founding story - ready to continue where we left off?",
    "key_topics": ["Arbez founding details", "childhood memories", "business challenges"],
    "sentiment": "engaged",
    "conversation_summary": "Explored early entrepreneurial journey and formative childhood experiences."
}
```

### Prompt Engineering
The prompt uses XML formatting for structured data:
- `<agent_profile>` - Agent identity and personality
- `<caller_profile>` - User information
- `<conversation_transcript>` - Full conversation text
- `<explicit_instructions>` - Clear generation rules
- `<constraints>` - What NOT to do
- `<examples>` - Good vs bad examples

## Multi-Agent Scenarios

### Scenario: Caller Uses Multiple Agents

```
Day 1: Stefan calls Margaret (memoir agent)
  → Tier 1: Profile created (name: Stefan, interactions: 1)
  → Tier 2: Margaret state created (greeting about founding story)

Day 2: Stefan calls Dr. Sarah (health agent)
  → Tier 1: Updated (interactions: 2), name already known
  → Tier 2: Dr. Sarah state created (greeting about health topics)
  → Dr. Sarah uses default message BUT can say "Hi Stefan"

Day 3: Stefan calls Margaret again
  → Tier 1: Query returns name
  → Tier 2: Query returns Margaret's stored greeting
  → Margaret says: "Hi Stefan! Ready to continue your Arbez story?"

Day 4: Stefan calls Dr. Sarah again
  → Tier 1: Query returns name
  → Tier 2: Query returns Dr. Sarah's stored greeting
  → Dr. Sarah says: "Welcome back Stefan! How are you feeling since our last chat about your medication?"
```

### Key Benefits
1. **Name Recognition Everywhere**: Stefan is recognized by both agents
2. **Context Isolation**: Margaret doesn't mention health topics; Dr. Sarah doesn't mention founding story
3. **Continuity Per Agent**: Each agent picks up where THEIR last conversation ended

## Data Flow Diagrams

### Client-Data Webhook (Call Initiation)
```
Incoming Call
     │
     ▼
┌─────────────────────┐
│ Query Tier 1        │◄─── Get universal profile
│ (Universal Profile) │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Query Tier 2        │◄─── Get agent-specific state
│ (Agent State)       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│           Decision Tree                  │
├─────────────────────────────────────────┤
│ Has agent greeting? → Override message  │
│ Has name only?      → Name in variables │
│ No data?            → Empty (defaults)  │
└──────────┬──────────────────────────────┘
           │
           ▼
    Response to ElevenLabs
       (< 200ms)
```

### Post-Call Webhook (Learning)
```
Call Ends
     │
     ▼
┌─────────────────────┐
│ Extract Transcript  │
│ + Metadata          │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Get/Create Tier 1   │◄─── Universal profile
│ Extract Name        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Fetch Agent Profile │◄─── From cache or ElevenLabs API
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ OpenAI Generation   │◄─── Generate next greeting
│ (5-15 seconds)      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Store Tier 2 State  │◄─── Save for next call
└──────────┬──────────┘
           │
           ▼
   Ready for Next Call
```

## Performance Considerations

### Client-Data Webhook (Must Be Fast)
- **Target**: < 200ms response time
- **No LLM Calls**: Pure database queries only
- **Graceful Degradation**: Return empty on errors

### Post-Call Webhook (Can Be Slow)
- **Async Processing**: Caller already hung up
- **OpenAI Latency**: 5-15 seconds acceptable
- **Background Tasks**: Non-blocking processing

### Agent Profile Caching
- **TTL**: 24 hours
- **Purpose**: Avoid repeated ElevenLabs API calls
- **Hit Rate Target**: > 80%

## Storage in OpenMemory

### Tier 1 Memory Structure
```python
{
    "content": "Universal profile: name = Stefan",
    "tags": ["universal_profile", "name"],
    "metadata": {
        "field": "name",
        "value": "Stefan",
        "profile_type": "universal"
    },
    "user_id": "+16125551234",
    "salience": 0.9,
    "decay_lambda": 0  # Permanent
}
```

### Tier 2 Memory Structure
```python
{
    "content": "Agent agent_xyz conversation state: Next greeting prepared...",
    "tags": ["agent_state", "agent_xyz", "next_greeting"],
    "metadata": {
        "agent_id": "agent_xyz",
        "next_greeting": "Hi Stefan! Ready to continue...",
        "key_topics": ["founding story", "childhood"],
        "sentiment": "engaged",
        "conversation_summary": "Explored entrepreneurial journey...",
        "last_call_date": "2024-01-15T10:00:00Z",
        "conversation_count": 3,
        "profile_type": "agent_specific"
    },
    "user_id": "+16125551234",
    "salience": 0.9,
    "decay_lambda": 0  # Permanent
}
```

## API Reference

### Profile Functions

```python
# Tier 1 Functions
async def get_universal_user_profile(phone_number: str) -> dict | None
async def store_universal_user_profile(phone_number: str, name: str | None, increment_interactions: bool = True) -> bool

# Tier 2 Functions
async def get_agent_conversation_state(phone_number: str, agent_id: str) -> dict | None
async def store_agent_conversation_state(phone_number: str, agent_id: str, greeting_data: dict) -> bool

# Utilities
def extract_name_from_transcript(transcript: str) -> str | None
```

### OpenAI Service

```python
async def generate_next_greeting(
    agent_profile: dict,
    user_profile: dict,
    transcript: str,
    conversation_metadata: dict | None = None
) -> dict | None
```

## Troubleshooting

### Greeting Not Appearing
1. Check if Tier 2 state exists for the agent-user pair
2. Verify OpenAI API key is configured
3. Check post-call webhook logs for generation errors

### Name Not Recognized
1. Check if Tier 1 profile exists
2. Verify name extraction patterns match transcript format
3. Check if name was overwritten (should never happen)

### Slow Response Times
1. Verify client-data webhook has no LLM calls
2. Check OpenMemory connection latency
3. Monitor agent cache hit rate
