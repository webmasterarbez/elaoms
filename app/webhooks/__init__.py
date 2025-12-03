"""Webhook handlers for ElevenLabs Agent integration.

This module exports the webhook routers for:
- client_data: Conversation initiation webhook
- search_data: Mid-conversation memory search webhook
- post_call: Post-call processing webhook (transcription, audio, failures)
"""

from app.webhooks.client_data import router as client_data_router
from app.webhooks.search_data import router as search_data_router
from app.webhooks.post_call import router as post_call_router

__all__ = [
    "client_data_router",
    "search_data_router",
    "post_call_router",
]