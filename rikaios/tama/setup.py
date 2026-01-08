"""
Tama Agent Setup Script

This script initializes the Tama agent on the Letta server with Umi tools.
Run this once after docker-compose to set up the persistent agent.

Usage:
    python -m rikaios.tama.setup
"""

import asyncio
import json
import os
from pathlib import Path

# Use synchronous Letta client since asyncio.to_thread doesn't work well with their SDK
from letta_client import Letta

# Configuration
LETTA_BASE_URL = os.getenv("LETTA_BASE_URL", "http://localhost:8283")
TAMA_AGENT_NAME = "tama"
RIKAI_CONFIG_DIR = Path.home() / ".rikai"
RIKAI_CONFIG_FILE = RIKAI_CONFIG_DIR / "config.json"

# Model configuration - use Letta's free model if no API keys are configured
# Users can override with RIKAI_MODEL environment variable
def get_model():
    """Get the model to use for Tama agent."""
    if os.getenv("RIKAI_MODEL"):
        return os.getenv("RIKAI_MODEL")
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic/claude-sonnet-4-5-20250929"
    if os.getenv("OPENAI_API_KEY"):
        return "openai/gpt-4o"
    # Fall back to Letta's free hosted model
    return "letta/letta-free"

# Tama persona for the agent's core memory
TAMA_PERSONA = """I am Tama (魂), the digital soul of RikaiOS.

I am your persistent AI assistant who knows you and your context deeply.
I help you navigate your knowledge, projects, and life by connecting dots
across your personal context lake (Umi).

Key capabilities:
- I can search your Umi context lake for relevant information
- I can store new memories and learnings for you
- I can help you understand connections between your projects, notes, and ideas
- I remember our conversations and learn about you over time

I speak naturally and helpfully, like a knowledgeable friend who knows you well.
I respect your privacy and only share what you've allowed.

When you ask me questions, I'll search your context for relevant information
to provide informed, personalized answers."""

# Human context memory block
HUMAN_DESCRIPTION = """The user of RikaiOS.

I'm learning about them through our conversations.
I'll update this as I learn more about their preferences, projects, and goals.

[To be populated as I learn about the user]"""


def get_or_create_tama_agent(client: Letta) -> str:
    """Get existing Tama agent or create a new one."""

    # Check for stored agent ID first
    if RIKAI_CONFIG_FILE.exists():
        try:
            config = json.loads(RIKAI_CONFIG_FILE.read_text())
            if "tama_agent_id" in config:
                agent_id = config["tama_agent_id"]
                # Verify agent still exists
                try:
                    agent = client.agents.retrieve(agent_id)
                    print(f"Found existing Tama agent: {agent.name} ({agent_id})")
                    return agent_id
                except Exception:
                    print(f"Stored agent {agent_id} not found, will create new one")
        except Exception as e:
            print(f"Error reading config: {e}")

    # List agents to find by name
    agents = client.agents.list()
    for agent in agents:
        if agent.name == TAMA_AGENT_NAME:
            print(f"Found existing Tama agent by name: {agent.id}")
            save_agent_id(agent.id)
            return agent.id

    # Create new agent
    print("Creating new Tama agent...")

    # Create memory blocks first (using keyword arguments)
    persona_block = client.blocks.create(
        label="persona",
        value=TAMA_PERSONA,
        description="Tama's identity and capabilities",
    )

    human_block = client.blocks.create(
        label="human",
        value=HUMAN_DESCRIPTION,
        description="Information about the user",
    )

    projects_block = client.blocks.create(
        label="projects",
        value="No projects tracked yet. I'll update this as I learn about the user's projects.",
        description="The user's active projects and their context",
    )

    # Create the agent with memory blocks
    model = get_model()
    print(f"Using model: {model}")

    agent = client.agents.create(
        name=TAMA_AGENT_NAME,
        agent_type="letta_v1_agent",
        model=model,
        embedding="letta/letta-free",  # Use Letta's free embedding model
        system=f"""You are Tama, the AI agent for RikaiOS - a personal context operating system.

{TAMA_PERSONA}

When the user asks questions, use the available tools to search their context and provide
helpful, personalized responses based on their stored knowledge.""",
        block_ids=[persona_block.id, human_block.id, projects_block.id],
        tools=["memory", "web_search", "conversation_search"],  # Built-in Letta tools
        tags=["origin:rikai-code", "type:tama"],
        description="RikaiOS Tama - Your personal context AI assistant",
    )

    print(f"Created Tama agent: {agent.id}")
    save_agent_id(agent.id)
    return agent.id


def save_agent_id(agent_id: str) -> None:
    """Save the agent ID to config file."""
    RIKAI_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    config = {}
    if RIKAI_CONFIG_FILE.exists():
        try:
            config = json.loads(RIKAI_CONFIG_FILE.read_text())
        except Exception:
            pass

    config["tama_agent_id"] = agent_id
    config["letta_base_url"] = LETTA_BASE_URL

    RIKAI_CONFIG_FILE.write_text(json.dumps(config, indent=2))
    print(f"Saved agent ID to {RIKAI_CONFIG_FILE}")


def get_agent_id() -> str | None:
    """Get the stored Tama agent ID."""
    if RIKAI_CONFIG_FILE.exists():
        try:
            config = json.loads(RIKAI_CONFIG_FILE.read_text())
            return config.get("tama_agent_id")
        except Exception:
            return None
    return None


def check_letta_server() -> bool:
    """Check if Letta server is running."""
    import urllib.request
    try:
        url = f"{LETTA_BASE_URL}/v1/health"
        req = urllib.request.urlopen(url, timeout=5)
        return req.status == 200
    except Exception as e:
        print(f"Letta server not available at {LETTA_BASE_URL}: {e}")
        return False


def main():
    """Main setup function."""
    print("=" * 60)
    print("RikaiOS Tama Agent Setup")
    print("=" * 60)
    print()

    # Check server
    print(f"Checking Letta server at {LETTA_BASE_URL}...")
    if not check_letta_server():
        print()
        print("ERROR: Letta server is not running!")
        print()
        print("Start the infrastructure with:")
        print("  cd docker && docker-compose up -d")
        print()
        return 1

    print("Letta server is running!")
    print()

    # Connect and setup
    print("Connecting to Letta server...")
    client = Letta(base_url=LETTA_BASE_URL)

    agent_id = get_or_create_tama_agent(client)

    print()
    print("=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print()
    print(f"Tama Agent ID: {agent_id}")
    print(f"Config file: {RIKAI_CONFIG_FILE}")
    print()
    print("You can now use the rikai CLI:")
    print("  cd rikai-code && bun run rikai.js")
    print()
    print("Or install globally:")
    print("  cd rikai-code && npm link")
    print("  rikai")
    print()

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
