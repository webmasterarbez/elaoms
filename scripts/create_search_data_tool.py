#!/usr/bin/env python3
"""
Create search_data tool via ElevenLabs API

Usage:
    python create_search_data_tool.py

Or with custom values:
    python create_search_data_tool.py --webhook-url https://your-url.com/webhook/search-data
    python create_search_data_tool.py --api-key YOUR_API_KEY
"""

import requests
import json
import argparse
import os

DEFAULT_WEBHOOK_URL = "https://rockered-marisol-nonlimitative.ngrok-free.dev/webhook/search-data"
DEFAULT_SECRET_ID = "tlQBfIowXZc8rwqDKGmf"


def create_tool(
    api_key: str,
    webhook_url: str = DEFAULT_WEBHOOK_URL,
    secret_id: str = DEFAULT_SECRET_ID
) -> dict:
    """Create the search_data tool via ElevenLabs API."""

    url = "https://api.elevenlabs.io/v1/convai/tools"

    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }

    # API format differs from Dashboard UI format
    # - Wrapped in tool_config
    # - Properties as object (not array)
    # - request_headers as object (not array)
    # - Omit empty path_params_schema and query_params_schema
    payload = {
        "tool_config": {
            "type": "webhook",
            "name": "search_data",
            "description": "Search memories and profile data for the current caller. Returns profile information (name, summary) and relevant memories from previous conversations.",
            "api_schema": {
                "url": webhook_url,
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
                    "X-Api-Key": "{{" + secret_id + "}}"
                }
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
            "execution_mode": "immediate",
            "dynamic_variables": {
                "dynamic_variable_placeholders": {}
            }
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
        "--api-key",
        default=os.getenv("ELEVENLABS_API_KEY"),
        help="ElevenLabs API key (or set ELEVENLABS_API_KEY env var)"
    )
    parser.add_argument(
        "--webhook-url",
        default=DEFAULT_WEBHOOK_URL,
        help="Webhook URL for the search-data endpoint"
    )
    parser.add_argument(
        "--secret-id",
        default=DEFAULT_SECRET_ID,
        help="ElevenLabs secret ID for X-Api-Key header"
    )
    args = parser.parse_args()

    if not args.api_key:
        print("Error: API key required. Use --api-key or set ELEVENLABS_API_KEY")
        return

    print(f"Creating search_data tool...")
    print(f"Webhook URL: {args.webhook_url}")
    print()

    result = create_tool(args.api_key, args.webhook_url, args.secret_id)

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
