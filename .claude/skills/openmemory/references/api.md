# OpenMemory API Reference

Base URL: `http://localhost:8080` (default)

## Authentication

Optional API key via header:
```
Authorization: Bearer your_api_key_here
```
Or header: `x-api-key: your_api_key`

---

## Memory Endpoints

### POST /memory/add
Add a new memory.

**Request:**
```json
{
  "content": "string (required)",
  "user_id": "string (optional)",
  "tags": ["string"] ,
  "metadata": {},
  "salience": 0.8,
  "decay_lambda": 0.1
}
```

**Response:**
```json
{
  "id": "mem_7k9n2x4p8q",
  "primary_sector": "semantic",
  "sectors": ["semantic", "procedural"]
}
```

### POST /memory/query
Semantic search across memories.

**Request:**
```json
{
  "query": "string (required)",
  "k": 5,
  "filters": {
    "user_id": "string",
    "sector": "semantic|episodic|procedural|emotional|reflective",
    "tags": ["string"]
  }
}
```

**Response:**
```json
{
  "results": [
    {
      "id": "mem_xxx",
      "content": "...",
      "score": 0.89,
      "sector": "semantic",
      "metadata": {}
    }
  ]
}
```

### GET /memory/:id
Get memory by ID.

### PATCH /memory/:id
Update memory content or metadata.

### DELETE /memory/:id
Delete a memory.

### POST /memory/reinforce
Boost memory salience.

**Request:**
```json
{
  "id": "mem_xxx",
  "boost": 0.2
}
```

---

## User Endpoints

### GET /users/:user_id/summary
Get AI-generated summary of user's memories.

### GET /users/:user_id/memories
List all memories for a user.

**Query params:**
- `limit` (default: 50)
- `offset` (default: 0)
- `sector` (optional filter)

### DELETE /users/:user_id
Delete all memories for a user.

---

## Temporal Knowledge Graph

### POST /api/temporal/fact
Insert or update time-bound fact.

**Request:**
```json
{
  "subject": "CompanyX",
  "predicate": "has_CEO",
  "object": "Alice",
  "valid_from": "2021-01-01",
  "valid_to": null,
  "confidence": 0.98
}
```

### GET /api/temporal/fact
Query fact at specific time.

**Query params:**
- `subject` (required)
- `predicate` (required)
- `at` (ISO date, optional - defaults to now)

### GET /api/temporal/fact/current
Get current fact for subject-predicate pair.

### GET /api/temporal/timeline
Get complete timeline for an entity.

**Query params:**
- `subject` (required)
- `predicate` (optional)

### GET /api/temporal/compare
Compare facts between two time points.

**Query params:**
- `subject` (required)
- `time1` (ISO date)
- `time2` (ISO date)

### POST /api/temporal/decay
Apply confidence decay to old facts.

### GET /api/temporal/volatile
Get most frequently changing facts.

### GET /api/temporal/stats
Get temporal graph statistics.

---

## System Endpoints

### GET /health
Health check.

### GET /stats
System statistics including memory count, sector distribution, and performance metrics.

---

## MCP Endpoint

### POST /mcp
Model Context Protocol endpoint for AI tool integration.

**Tools exposed:**
- `openmemory_query` - Semantic search
- `openmemory_store` - Store memory
- `openmemory_list` - List memories
- `openmemory_get` - Get by ID
- `openmemory_reinforce` - Boost salience

---

## LangGraph Endpoints (when OM_MODE=langgraph)

### POST /lgm/add
Add memory in LangGraph namespace.

### POST /lgm/query
Query within namespace context.

### GET /lgm/context
Get context window for current namespace.

---

## Error Responses

```json
{
  "error": "ValidationError",
  "message": "Content cannot be empty",
  "code": 400
}
```

Common codes:
- `400` - Validation error
- `401` - Unauthorized
- `404` - Not found
- `500` - Server error
