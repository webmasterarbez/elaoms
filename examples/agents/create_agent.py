#!/usr/bin/env python3
"""
ElevenLabs Agent Creation Script

Create ElevenLabs voice agents from JSON configuration files.

Usage:
    python create_agent.py <config_file.json>
    python create_agent.py 01-customer-support.json
    python create_agent.py --list                      # List available configs
    python create_agent.py --all                       # Create all agents

Environment Variables Required:
    ELEVENLABS_API_KEY: Your ElevenLabs API key

Optional:
    ELEVENLABS_VOICE_ID: Override the voice_id in config files
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: 'requests' library required. Install with: pip install requests")
    sys.exit(1)


API_ENDPOINT = "https://api.elevenlabs.io/v1/convai/agents/create"
SCRIPT_DIR = Path(__file__).parent


def get_api_key() -> str:
    """Get API key from environment."""
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        print("Error: ELEVENLABS_API_KEY environment variable not set")
        print("\nSet it with:")
        print("  export ELEVENLABS_API_KEY=your_api_key_here")
        sys.exit(1)
    return api_key


def list_configs() -> list[Path]:
    """List all available JSON config files."""
    configs = sorted(SCRIPT_DIR.glob("*.json"))
    return configs


def load_config(config_path: Path) -> dict:
    """Load and parse JSON configuration file."""
    try:
        with open(config_path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {config_path}: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)


def override_voice_id(config: dict, voice_id: str) -> dict:
    """Override voice_id in config if specified."""
    if voice_id and "conversation_config" in config:
        if "tts" in config["conversation_config"]:
            config["conversation_config"]["tts"]["voice_id"] = voice_id
    return config


def create_agent(config: dict, api_key: str) -> dict:
    """Create an agent via the ElevenLabs API."""
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }

    response = requests.post(API_ENDPOINT, headers=headers, json=config)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: API request failed with status {response.status_code}")
        print(f"Response: {response.text}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Create ElevenLabs voice agents from JSON configs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_agent.py 01-customer-support.json
  python create_agent.py --list
  python create_agent.py --all
  ELEVENLABS_VOICE_ID=abc123 python create_agent.py 02-sales.json
        """
    )
    parser.add_argument(
        "config",
        nargs="?",
        help="JSON config file to use"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available config files"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Create all agents from available configs"
    )
    parser.add_argument(
        "--voice-id", "-v",
        help="Override voice_id in config"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be created without calling API"
    )

    args = parser.parse_args()

    # List available configs
    if args.list:
        configs = list_configs()
        if configs:
            print("Available agent configurations:\n")
            for config in configs:
                data = load_config(config)
                name = data.get("name", "Unnamed")
                tags = ", ".join(data.get("tags", []))
                print(f"  {config.name}")
                print(f"    Name: {name}")
                if tags:
                    print(f"    Tags: {tags}")
                print()
        else:
            print("No JSON config files found in:", SCRIPT_DIR)
        return

    # Determine which configs to process
    configs_to_process = []

    if args.all:
        configs_to_process = list_configs()
        if not configs_to_process:
            print("No JSON config files found")
            return
    elif args.config:
        config_path = Path(args.config)
        if not config_path.is_absolute():
            # Check in script directory first
            script_dir_path = SCRIPT_DIR / config_path
            if script_dir_path.exists():
                config_path = script_dir_path
            elif not config_path.exists():
                # Try adding .json extension
                if (SCRIPT_DIR / f"{config_path}.json").exists():
                    config_path = SCRIPT_DIR / f"{config_path}.json"
        configs_to_process = [config_path]
    else:
        parser.print_help()
        return

    # Get API key (skip for dry-run)
    api_key = None if args.dry_run else get_api_key()

    # Override voice_id from environment if set
    voice_id = args.voice_id or os.environ.get("ELEVENLABS_VOICE_ID")

    # Process each config
    results = []
    for config_path in configs_to_process:
        print(f"Processing: {config_path.name}")

        config = load_config(config_path)
        agent_name = config.get("name", "Unnamed Agent")

        if voice_id:
            config = override_voice_id(config, voice_id)
            print(f"  Using voice_id: {voice_id}")

        if args.dry_run:
            print(f"  [DRY RUN] Would create agent: {agent_name}")
            print(f"  Config preview:")
            print(f"    Tags: {config.get('tags', [])}")
            tts = config.get("conversation_config", {}).get("tts", {})
            print(f"    Voice ID: {tts.get('voice_id', 'Not set')}")
            print(f"    TTS Model: {tts.get('model_id', 'Not set')}")
            llm = config.get("conversation_config", {}).get("agent", {}).get("prompt", {})
            print(f"    LLM: {llm.get('llm', 'Not set')}")
            print()
            continue

        result = create_agent(config, api_key)

        if result:
            agent_id = result.get("agent_id")
            print(f"  Created: {agent_name}")
            print(f"  Agent ID: {agent_id}")
            results.append({
                "config": config_path.name,
                "name": agent_name,
                "agent_id": agent_id
            })
        else:
            print(f"  Failed to create: {agent_name}")
            results.append({
                "config": config_path.name,
                "name": agent_name,
                "agent_id": None,
                "error": True
            })

        print()

    # Summary
    if not args.dry_run and len(results) > 1:
        print("\n" + "=" * 50)
        print("Summary:")
        print("=" * 50)
        successes = [r for r in results if r.get("agent_id")]
        failures = [r for r in results if not r.get("agent_id")]

        if successes:
            print(f"\nSuccessfully created {len(successes)} agent(s):")
            for r in successes:
                print(f"  - {r['name']}: {r['agent_id']}")

        if failures:
            print(f"\nFailed to create {len(failures)} agent(s):")
            for r in failures:
                print(f"  - {r['name']}")


if __name__ == "__main__":
    main()
