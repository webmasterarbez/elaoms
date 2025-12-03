# Product Roadmap

1. [ ] Environment Configuration Setup — Create `.env` file structure with all required environment variables (ElevenLabs API keys, webhook secrets, OpenMemory configuration) and implement configuration loading with validation. `XS`

2. [ ] OpenMemory Client Integration — Initialize OpenMemory SDK client with local mode configuration, implement helper functions for memory operations (add, query, update), and configure zero-decay lambda settings for permanent memory retention. `S`

3. [ ] FastAPI Application Foundation — Create FastAPI application with proper project structure, implement health check endpoint, configure CORS middleware, and set up request/response logging for debugging. `S`

4. [ ] Webhook Authentication Middleware — Implement HMAC-SHA256 signature validation for ElevenLabs webhooks using timestamp and request body verification, with configurable tolerance window and per-endpoint secret keys. `S`

5. [ ] Client Data Webhook (POST /webhook/client-data) — Implement conversation initiation webhook that receives caller phone number, queries OpenMemory for existing caller profile, and returns dynamic variables with optional conversation config overrides for personalization. `M`

6. [ ] Search Data Server Tool Webhook (POST /webhook/search-data) — Implement server tool webhook that receives mid-conversation memory search requests, queries OpenMemory with contextual filters, and returns relevant memories for real-time agent context. `M`

7. [ ] Post-Call Webhook (POST /webhook/post-call) — Implement post-call webhook that receives conversation transcripts and metadata, extracts key information (summary, topics, preferences), and stores structured memories in OpenMemory with appropriate salience weights. `M`

8. [ ] Memory Extraction and Classification — Implement logic to parse post-call transcripts and automatically classify extracted information into appropriate OpenMemory sectors (episodic events, semantic facts, emotional context, preferences). `M`

9. [ ] Caller Profile Management — Implement caller profile creation for new phone numbers, profile updates for returning callers, and profile retrieval with aggregated memory context for personalization injection. `S`

10. [ ] Payload Logging and Debugging — Implement configurable payload logging to specified file paths for all webhook requests and responses, supporting development debugging and production audit trails. `S`

11. [ ] ngrok Local Development Integration — Document and script ngrok tunnel setup for local webhook testing, including dynamic URL configuration and ElevenLabs dashboard webhook registration workflow. `XS`

12. [ ] End-to-End Integration Testing — Create test suite covering full conversation lifecycle: initiation personalization, mid-call memory search, and post-call storage, with mock ElevenLabs payloads and OpenMemory verification. `M`

13. [ ] Error Handling and Retry Logic — Implement comprehensive error handling for OpenMemory failures, webhook timeouts, and malformed payloads, with appropriate HTTP status codes and error logging. `S`

14. [ ] Production Deployment Configuration — Create production-ready configuration with environment-specific settings, proper secret management, and deployment documentation for cloud hosting platforms. `S`

> Notes
> - Order reflects technical dependencies: configuration and clients must be established before webhooks can be implemented
> - Each webhook represents an end-to-end functional feature that can be tested independently
> - Memory extraction (item 8) depends on post-call webhook structure being finalized
> - Integration testing (item 12) should be performed after all three webhooks are functional
> - Production configuration (item 14) is final phase after local development is validated
