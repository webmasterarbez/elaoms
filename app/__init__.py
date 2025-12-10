"""ElevenLabs OpenMemory Integration Service (ELAOMS).

A FastAPI application that integrates ElevenLabs voice agents with OpenMemory
for persistent caller profiles and personalized conversations.

Package Structure:
- webhooks/: ElevenLabs webhook handlers (client-data, search-data, post-call)
- memory/: OpenMemory API integration for profile and memory management
- services/: OpenAI greeting generation and agent profile caching
- models/: Pydantic request/response models with validation
- auth/: HMAC signature verification for webhook security
- utils/: Shared utilities (logging, HTTP clients)
"""
