#!/bin/bash
# Create search_data tool via ElevenLabs API
# Usage: ./create-search-data-tool.sh

API_KEY="sk_aa411c875d9182d31437003aa9a552147403180bf43274d6"
WEBHOOK_URL="https://rockered-marisol-nonlimitative.ngrok-free.dev/webhook/search-data"
SECRET_ID="tlQBfIowXZc8rwqDKGmf"

curl -X POST "https://api.elevenlabs.io/v1/convai/tools" \
  -H "xi-api-key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
  "type": "webhook",
  "name": "search_data",
  "description": "Search memories and profile data for the current caller. Returns profile information (name, summary) and relevant memories from previous conversations. Use when you need to recall information about the caller, personalize responses, or continue previous conversation topics.",
  "api_schema": {
    "url": "'"${WEBHOOK_URL}"'",
    "method": "POST",
    "path_params_schema": [],
    "query_params_schema": [],
    "request_body_schema": {
      "id": "search_data_body",
      "description": "Request body for searching caller memories and profile data",
      "type": "object",
      "properties": [
        {
          "id": "user_id",
          "type": "string",
          "value_type": "dynamic_variable",
          "description": "Caller phone number in E.164 format",
          "dynamic_variable": "system__caller_id",
          "constant_value": "",
          "enum": null,
          "is_system_provided": false,
          "required": true
        },
        {
          "id": "query",
          "type": "string",
          "value_type": "llm_prompt",
          "description": "Natural language search query to find relevant memories",
          "dynamic_variable": "",
          "constant_value": "",
          "enum": null,
          "is_system_provided": false,
          "required": true
        },
        {
          "id": "agent_id",
          "type": "string",
          "value_type": "dynamic_variable",
          "description": "The ElevenLabs agent identifier",
          "dynamic_variable": "system__agent_id",
          "constant_value": "",
          "enum": null,
          "is_system_provided": false,
          "required": true
        }
      ],
      "required": false
    },
    "request_headers": [
      {
        "type": "value",
        "name": "Content-Type",
        "value": "application/json"
      },
      {
        "type": "secret",
        "name": "X-Api-Key",
        "secret_id": "'"${SECRET_ID}"'"
      }
    ]
  },
  "response_timeout_secs": 10,
  "assignments": [
    {
      "source": "response",
      "dynamic_variable": "profile",
      "value_path": "profile"
    },
    {
      "source": "response",
      "dynamic_variable": "memories",
      "value_path": "memories"
    }
  ],
  "tool_call_sound": "typing",
  "tool_call_sound_behavior": "auto",
  "execution_mode": "immediate",
  "disable_interruptions": false,
  "force_pre_tool_speech": "auto",
  "dynamic_variables": {
    "dynamic_variable_placeholders": {}
  }
}'

echo ""
echo "Tool creation request sent!"
