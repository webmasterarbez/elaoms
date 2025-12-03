---
name: openmemory
description: "Integration with CaviraOSS OpenMemory - a self-hosted, open-source long-term memory engine for AI agents. Use when: (1) Adding persistent memory to AI applications, (2) Storing and querying memories via REST API or MCP, (3) Setting up OpenMemory backend or dashboard, (4) Using openmemory-py or openmemory-js SDKs, (5) Configuring memory sectors (semantic, episodic, procedural, emotional, reflective), (6) Working with temporal knowledge graphs, (7) Migrating from Zep, Mem0, or Supermemory."
---

# OpenMemory Integration

OpenMemory is a self-hosted AI memory engine providing persistent, semantic, multi-sector memory with automatic decay and graph associations.

**Repo**: https://github.com/CaviraOSS/OpenMemory  
**Docs**: https://openmemory.cavira.app

## Quick Start

### Docker (Recommended)
```bash
git clone https://github.com/caviraoss/openmemory.git
cd openmemory
cp .env.example .env
docker compose up --build -d
```
Backend runs on `http://localhost:8080`.

### Manual Setup
```bash
cd openmemory/backend
npm install
npm run dev
```
Requires Node.js 20+, SQLite 3.40+.

## Core API Operations

### Add Memory
```bash
curl -X POST http://localhost:8080/memory/add \
  -H "Content-Type: application/json" \
  -d '{"content": "User prefers dark mode", "user_id": "user123", "tags": ["preferences"]}'
```

### Query Memory
```bash
curl -X POST http://localhost:8080/memory/query \
  -H "Content-Type: application/json" \
  -d '{"query": "preferences", "k": 5, "filters": {"user_id": "user123"}}'
```

### User Summary
```bash
curl http://localhost:8080/users/user123/summary
```

## Memory Sectors

OpenMemory routes memories to cognitive sectors automatically:

| Sector | Purpose | Example |
|--------|---------|---------|
| **semantic** | Facts & knowledge | "Python uses duck typing" |
| **episodic** | Events & experiences | "Met client at 3pm for Q4 roadmap" |
| **procedural** | Skills & patterns | "User commits before switching branches" |
| **emotional** | Sentiment states | "User frustrated with slow builds" |
| **reflective** | Meta-memory | "Memory system recalculated weights" |

Force sector assignment:
```python
om.add(content="...", metadata={"sector": "semantic"})
```

## Python SDK

```bash
pip install openmemory-py
```

```python
from openmemory import OpenMemory

om = OpenMemory(base_url="http://localhost:8080", api_key="your_key")

# Add memory with salience and decay
om.add(
    content="Database backup runs daily at 2 AM UTC",
    user_id="user123",
    salience=0.9,        # High importance (0-1)
    decay_lambda=0.05,   # Slow decay (lower = slower)
    tags=["critical", "ops"]
)

# Query
results = om.query("backup schedule", user_id="user123", k=5)
```

### Salience & Decay Guidelines

| Use Case | Salience | Decay Lambda |
|----------|----------|--------------|
| System config | 0.95 | 0.03 |
| User preferences | 0.8 | 0.1 |
| General knowledge | 0.6 | 0.15 |
| Session context | 0.5 | 0.15 |
| Temporary data | 0.3 | 0.25 |

## JavaScript SDK

```bash
npm install openmemory-js
```

```javascript
import { OpenMemory } from "openmemory-js"

const om = new OpenMemory({ apiKey: "your_key" })

const result = await om.addMemory({
    content: "GraphQL provides type-safe API queries",
    metadata: { category: "web_development" },
    decayRate: 0.96,
    initialStrength: 0.85
})
```

## MCP Integration

OpenMemory provides an MCP server at `POST /mcp`.

### Claude Desktop (stdio mode)
```bash
node backend/dist/ai/mcp.js
```

### Claude Code (HTTP mode)
```bash
claude mcp add --transport http --scope user openmemory http://localhost:8080/mcp
```

Or add to `~/.claude.json`:
```json
{
  "mcpServers": {
    "openmemory": {
      "type": "http",
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

**Available MCP Tools**:
- `mcp__openmemory__query` - Semantic search
- `mcp__openmemory__store` - Store memory
- `mcp__openmemory__list` - List recent memories
- `mcp__openmemory__get` - Get by ID
- `mcp__openmemory__reinforce` - Boost salience

## CLI Tool (opm)

```bash
cd backend && npm link
```

```bash
opm add "user likes dark mode" --user u123 --tags prefs
opm query "preferences" --user u123 --limit 5
opm list --user u123
opm reinforce <memory-id>
opm stats
opm health
```

## Temporal Knowledge Graph

Track facts that change over time:

```bash
# Insert time-bound fact
curl -X POST http://localhost:8080/api/temporal/fact \
  -H "Content-Type: application/json" \
  -d '{"subject": "CompanyX", "predicate": "has_CEO", "object": "Alice", "valid_from": "2021-01-01"}'

# Query at specific time
curl "http://localhost:8080/api/temporal/fact?subject=CompanyX&predicate=has_CEO&at=2023-01-01"

# Get timeline
curl "http://localhost:8080/api/temporal/timeline?subject=CompanyX&predicate=has_CEO"
```

## Environment Configuration

Key `.env` variables:
```bash
OM_PORT=8080
OM_DB_PATH=./data/openmemory.sqlite
OM_EMBEDDINGS=openai  # openai|gemini|ollama|local
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
OLLAMA_URL=http://localhost:11434
OM_VEC_DIM=768
OM_MIN_SCORE=0.3
OM_DECAY_LAMBDA=0.02
OM_API_KEY=your_secret_key  # Optional auth
```

## LangGraph Mode

Enable for graph-based memory operations:
```bash
OM_MODE=langgraph
OM_LG_NAMESPACE=default
```

Provides `/lgm/*` endpoints.

## Migration

Migrate from other memory systems:
```bash
cd migrate
node index.js --from mem0 --api-key MEM0_KEY --verify
node index.js --from zep --api-key ZEP_KEY --rate-limit 1
node index.js --from supermemory --api-key SM_KEY
```

## API Reference

See [references/api.md](references/api.md) for complete endpoint documentation.
