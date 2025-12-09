#!/bin/bash
# Create search_data tool via ElevenLabs API
#
# Usage:
#   ./create-search-data-tool.sh
#
# Or with environment variables:
#   ELEVENLABS_API_KEY=sk_xxx ./create-search-data-tool.sh
#
# Note: API format differs from Dashboard UI format

API_KEY="${ELEVENLABS_API_KEY:-YOUR_API_KEY_HERE}"
WEBHOOK_URL="${WEBHOOK_URL:-https://rockered-marisol-nonlimitative.ngrok-free.dev/webhook/search-data}"
SECRET_ID="${SECRET_ID:-tlQBfIowXZc8rwqDKGmf}"

if [ "$API_KEY" = "YOUR_API_KEY_HERE" ]; then
    echo "Error: Set ELEVENLABS_API_KEY environment variable"
    echo "Usage: ELEVENLABS_API_KEY=sk_xxx ./create-search-data-tool.sh"
    exit 1
fi

echo "Creating search_data tool..."
echo "Webhook URL: ${WEBHOOK_URL}"
echo ""

curl -X POST "https://api.elevenlabs.io/v1/convai/tools" \
  -H "xi-api-key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
  "tool_config": {
    "type": "webhook",
    "name": "search_data",
    "description": "Search memories and profile data for the current caller. Returns profile information (name, summary) and relevant memories from previous conversations.",
    "api_schema": {
      "url": "'"${WEBHOOK_URL}"'",
      "method": "POST",
      "request_body_schema": {
        "type": "object",
        "description": "Request body for searching caller memories",
        "properties": {
          "user_id": {
            "type": "string",
            "description": "Caller phone number in E.164 format"
          },
          "query": {
            "type": "string",
            "description": "Natural language search query"
          },
          "agent_id": {
            "type": "string",
            "description": "ElevenLabs agent ID"
          }
        },
        "required": ["user_id", "query", "agent_id"]
      },
      "request_headers": {
        "Content-Type": "application/json",
        "X-Api-Key": "{{'"${SECRET_ID}"'}}"
      }
    },
    "response_timeout_secs": 10,
    "assignments": [
      {"source": "response", "dynamic_variable": "profile", "value_path": "profile"},
      {"source": "response", "dynamic_variable": "memories", "value_path": "memories"}
    ],
    "tool_call_sound": "typing",
    "execution_mode": "immediate",
    "dynamic_variables": {"dynamic_variable_placeholders": {}}
  }
}'

echo ""
echo "Done!"
