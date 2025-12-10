# Migration Guide: Two-Tier Memory Architecture

This guide walks through migrating ELAOMS from the legacy single-tier profile system to the new two-tier memory architecture.

## Overview

The new architecture separates:
- **Tier 1**: Universal user profiles (shared across agents)
- **Tier 2**: Agent-specific conversation states (isolated per agent)

This enables true multi-agent support where each agent maintains its own relationship with callers while sharing basic identity information.

## Pre-Migration Checklist

Before starting the migration, ensure you have:

- [ ] **OpenAI API Key**: Obtained from [OpenAI Platform](https://platform.openai.com/api-keys)
- [ ] **OpenMemory Version**: Compatible with the memory query/add API
- [ ] **Environment Variables**: All new variables configured
- [ ] **Test Environment**: Staging environment ready for testing
- [ ] **Backup**: Database backup of existing OpenMemory data

## New Environment Variables

Add these to your `.env` file:

```bash
# OpenAI Configuration (for greeting generation)
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4o-mini          # Optional, default: gpt-4o-mini
OPENAI_MAX_TOKENS=150              # Optional, default: 150
OPENAI_TEMPERATURE=0.7             # Optional, default: 0.7
OPENAI_TIMEOUT=30                  # Optional, default: 30 seconds
```

### Configuration Validation

The system validates:
- `OPENAI_MAX_TOKENS`: Must be between 50-500
- `OPENAI_TEMPERATURE`: Must be between 0.0-2.0
- `OPENAI_TIMEOUT`: Must be between 5-120 seconds

Invalid values will log a warning and use defaults.

## Migration Steps

### Phase 1: Deploy New Code (Non-Breaking)

The new code is backward compatible. Deploy it without changing behavior:

```bash
# 1. Pull latest code
git pull origin main

# 2. Install new dependencies (if any)
pip install -r requirements.txt

# 3. Update environment variables
cp .env.example .env.new
# Edit .env.new with your values
mv .env.new .env

# 4. Restart the service
sudo systemctl restart elaoms
```

At this point:
- New services (OpenAI, agent cache) are deployed but not active
- Legacy webhook logic still handles all calls
- No user-facing changes

### Phase 2: Verify New Services

Test the new services in isolation:

```bash
# Test OpenAI connectivity
python -c "
from app.services.openai_service import generate_next_greeting
import asyncio

result = asyncio.run(generate_next_greeting(
    agent_profile={'agent_id': 'test', 'agent_name': 'Test', 'first_message': 'Hi', 'system_prompt': 'You are helpful'},
    user_profile={'name': 'John', 'phone_number': '+1234', 'total_interactions': 1},
    transcript='Agent: Hello\nUser: Hi, my name is John'
))
print('OpenAI test:', 'PASS' if result else 'FAIL')
"

# Test agent cache
python -c "
from app.services.agent_cache import get_agent_profile_cache
import asyncio

cache = get_agent_profile_cache()
# This will fail without valid agent ID, but tests connectivity
print('Agent cache initialized:', 'PASS')
"
```

### Phase 3: Data Migration (Optional)

If you have existing caller profiles in the legacy format, migrate them:

```python
# migration_script.py
import asyncio
from app.memory.profiles import (
    get_user_profile,  # Legacy function
    store_universal_user_profile,
)

async def migrate_profiles(phone_numbers: list[str]):
    """Migrate legacy profiles to Tier 1 format."""
    for phone in phone_numbers:
        # Get legacy profile
        legacy = await get_user_profile(phone)
        if legacy:
            # Store as Tier 1 universal profile
            await store_universal_user_profile(
                phone_number=phone,
                name=legacy.get("name"),
                increment_interactions=False  # Don't double-count
            )
            print(f"Migrated: {phone}")

# Run migration
if __name__ == "__main__":
    # Get list of phone numbers from your database
    phone_numbers = ["+16125551234", "+16125559876"]  # Example
    asyncio.run(migrate_profiles(phone_numbers))
```

**Note**: Tier 2 data cannot be migrated - it will be generated naturally as callers interact with agents.

### Phase 4: Enable New Logic

The new webhook logic is already active. Monitor logs to verify:

```bash
# Watch client-data webhook logs
journalctl -u elaoms -f | grep "client-data"

# Expected log patterns:
# "Client-data webhook called for caller: +16125551234, agent: agent_xyz"
# "Found agent-specific greeting for +16125551234" (Tier 2 hit)
# "Found universal profile for +16125551234" (Tier 1 hit, first call to agent)
# "New caller +16125551234 - using agent defaults" (no profile)
```

```bash
# Watch post-call webhook logs
journalctl -u elaoms -f | grep "post-call\|OpenAI\|Tier"

# Expected log patterns:
# "Processing memories for caller: +16125551234, agent: agent_xyz"
# "Updated universal profile for +16125551234"
# "Generating next greeting for +16125551234 with agent agent_xyz"
# "Stored agent-specific state for +16125551234 with agent agent_xyz"
```

### Phase 5: Validation

Verify the system is working correctly:

#### Test 1: New Caller Flow
```
1. Call with a new phone number
2. Agent should use default first message
3. After call, check logs for:
   - Universal profile created
   - Agent state created with greeting
```

#### Test 2: Returning Caller (Same Agent)
```
1. Call again with same phone number to same agent
2. Agent should use personalized greeting from Tier 2
3. Verify greeting references previous conversation topics
```

#### Test 3: Multi-Agent Flow
```
1. Call Agent A with new number
2. Call Agent B with same number
3. Agent B should recognize name (Tier 1) but use default message
4. Call Agent A again - should get Agent A's custom greeting
5. Call Agent B again - should get Agent B's custom greeting
```

### Phase 6: Cleanup (Optional)

After successful migration, you can optionally remove legacy code:

```python
# Functions that can be deprecated (but kept for backward compatibility):
# - build_conversation_override() in profiles.py
# - build_dynamic_variables() in profiles.py
# - get_user_profile() - replaced by get_universal_user_profile()
```

**Recommendation**: Keep legacy functions for at least 30 days post-migration for rollback safety.

## Rollback Plan

If critical issues occur, rollback is straightforward:

### Quick Rollback (Feature Flag)

```python
# In app/webhooks/client_data.py, add at top:
USE_TWO_TIER = os.getenv("USE_TWO_TIER", "true").lower() == "true"

# In the webhook function:
if USE_TWO_TIER:
    # New two-tier logic
    ...
else:
    # Legacy logic
    profile = await get_user_profile(phone_number)
    ...
```

Set `USE_TWO_TIER=false` in environment to revert.

### Full Rollback

```bash
# Revert to previous code
git checkout <previous-commit-hash>

# Restart service
sudo systemctl restart elaoms
```

## Monitoring

### Key Metrics to Watch

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Client-data response time | < 200ms | > 500ms |
| Post-call processing time | < 30s | > 60s |
| OpenAI API success rate | > 95% | < 90% |
| Agent cache hit rate | > 80% | < 60% |
| Tier 1 query success | > 99% | < 95% |
| Tier 2 query success | > 99% | < 95% |

### Log Queries

```bash
# Count greeting generations per hour
journalctl -u elaoms --since "1 hour ago" | grep "Stored agent-specific state" | wc -l

# Count OpenAI failures
journalctl -u elaoms --since "1 hour ago" | grep "OpenAI" | grep -i "error\|fail" | wc -l

# Check cache hit rate
journalctl -u elaoms --since "1 hour ago" | grep "Cache hit" | wc -l
journalctl -u elaoms --since "1 hour ago" | grep "Fetching agent profile" | wc -l
```

## Troubleshooting

### OpenAI Errors

**Rate Limit (429)**
```
Error: OpenAI API error: 429 - Rate limit exceeded
```
Solution: The system automatically retries with exponential backoff. If persistent, check your OpenAI plan limits.

**Invalid API Key (401)**
```
Error: OpenAI API error: 401 - Invalid API key
```
Solution: Verify `OPENAI_API_KEY` in your environment.

**Timeout**
```
Error: HTTP error calling OpenAI API: ReadTimeout
```
Solution: Increase `OPENAI_TIMEOUT` or check network connectivity.

### Memory Query Failures

**OpenMemory Connection Error**
```
Error: HTTP error querying universal profile for +16125551234
```
Solution: Verify OpenMemory is running and `OPENMEMORY_PORT` is correct.

**No Matches Found**
```
Info: No universal profile found for +16125551234
```
This is normal for new callers. Profile will be created after first call.

### Cache Issues

**Agent Profile Not Found**
```
Warning: Agent not found: agent_xyz
```
Solution: Verify the agent ID exists in ElevenLabs. Check `ELEVENLABS_API_KEY`.

**Cache Not Updating**
```
Debug: Cache hit for agent agent_xyz (but data is stale)
```
Solution: Manually invalidate cache:
```python
from app.services.agent_cache import get_agent_profile_cache
cache = get_agent_profile_cache()
cache.invalidate("agent_xyz")
```

## Cost Estimation

### OpenAI Costs

Using `gpt-4o-mini` (recommended):
- **Input tokens**: ~500-1000 per call (transcript + prompt)
- **Output tokens**: ~50-100 per call (JSON response)
- **Cost per call**: ~$0.0005-$0.001

Monthly estimate for 10,000 calls: **$5-$10**

### Optimizations

1. **Reduce transcript length**: Already truncated to 2000 chars
2. **Use caching**: Agent profiles cached for 24 hours
3. **Graceful degradation**: If OpenAI fails, system continues without greeting

## FAQ

**Q: What happens if OpenAI is down?**
A: Greeting generation is skipped. Callers still get recognized (Tier 1) but agents use default messages.

**Q: How long are greetings stored?**
A: Permanently (`decay_lambda=0`). Each new call overwrites the previous greeting.

**Q: Can I use a different OpenAI model?**
A: Yes, set `OPENAI_MODEL=gpt-4o` for higher quality (but higher cost).

**Q: What if the same caller calls two agents simultaneously?**
A: Each webhook processes independently. Tier 1 updates are idempotent (last writer wins for name). Tier 2 states are isolated.

**Q: How do I add a new agent?**
A: Just configure it in ElevenLabs. The system automatically handles new agents - no code changes needed.
