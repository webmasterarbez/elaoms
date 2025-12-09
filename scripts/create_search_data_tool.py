#!/usr/bin/env python3
"""
Create search_data tool via ElevenLabs API

Usage:
    python create_search_data_tool.py

Or with custom values:
    python create_search_data_tool.py --webhook-url https://your-url.com/webhook/search-data
"""

import requests
import json
import argparse

API_KEY = "sk_aa411c875d9182d31437003aa9a552147403180bf43274d6"
DEFAULT_WEBHOOK_URL = "https://rockered-marisol-nonlimitative.ngrok-free.dev/webhook/search-data"
SECRET_ID = "tlQBfIowXZc8rwqDKGmf"


def create_tool(webhook_url: str = DEFAULT_WEBHOOK_URL) -> dict:
    """Create the search_data tool via ElevenLabs API."""

    url = "https://api.elevenlabs.io/v1/convai/tools"

    headers = {
        "xi-api-key": API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "type": "webhook",
        "name": "search_data",
        "description": "Search memories and profile data for the current caller. Returns profile information (name, summary) and relevant memories from previous conversations. Use when you need to recall information about the caller, personalize responses, or continue previous conversation topics.",
        "api_schema": {
            "url": webhook_url,
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
                        "enum": None,
                        "is_system_provided": False,
                        "required": True
                    },
                    {
                        "id": "query",
                        "type": "string",
                        "value_type": "llm_prompt",
                        "description": "Natural language search query to find relevant memories",
                        "dynamic_variable": "",
                        "constant_value": "",
                        "enum": None,
                        "is_system_provided": False,
                        "required": True
                    },
                    {
                        "id": "agent_id",
                        "type": "string",
                        "value_type": "dynamic_variable",
                        "description": "The ElevenLabs agent identifier",
                        "dynamic_variable": "system__agent_id",
                        "constant_value": "",
                        "enum": None,
                        "is_system_provided": False,
                        "required": True
                    }
                ],
                "required": False
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
                    "secret_id": SECRET_ID
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
        "disable_interruptions": False,
        "force_pre_tool_speech": "auto",
        "dynamic_variables": {
            "dynamic_variable_placeholders": {}
        }
    }

    response = requests.post(url, headers=headers, json=payload)

    return {
        "status_code": response.status_code,
        "response": response.json() if response.text else {}
    }


def main():
    parser = argparse.ArgumentParser(description="Create search_data tool via ElevenLabs API")
    parser.add_argument(
        "--webhook-url",
        default=DEFAULT_WEBHOOK_URL,
        help="Webhook URL for the search-data endpoint"
    )
    args = parser.parse_args()

    print(f"Creating search_data tool...")
    print(f"Webhook URL: {args.webhook_url}")
    print()

    result = create_tool(args.webhook_url)

    print(f"Status Code: {result['status_code']}")
    print(f"Response:")
    print(json.dumps(result['response'], indent=2))

    if result['status_code'] == 200:
        print("\n✓ Tool created successfully!")
        if 'id' in result['response']:
            print(f"Tool ID: {result['response']['id']}")
    else:
        print("\n✗ Failed to create tool")


if __name__ == "__main__":
    main()
