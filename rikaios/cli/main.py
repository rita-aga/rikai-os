"""
RikaiOS CLI

Command-line interface for RikaiOS - your Personal Context Operating System.

Usage:
    rikai init          Initialize RikaiOS locally
    rikai status        Check system status
    rikai umi status    Check Umi (context lake) status
    rikai ask <query>   Ask your Tama a question
"""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from rikaios import __version__
from rikaios.core.config import get_local_path, ensure_local_path, get_settings

# Create the main app
app = typer.Typer(
    name="rikai",
    help="RikaiOS (理解OS) - Personal Context Operating System",
    add_completion=False,
)

# Create sub-apps
umi_app = typer.Typer(help="Umi (海) - Context Lake commands")
tama_app = typer.Typer(help="Tama (魂) - Agent commands")
connector_app = typer.Typer(help="Connector commands")
app.add_typer(umi_app, name="umi")
app.add_typer(tama_app, name="tama")
app.add_typer(connector_app, name="connector")

# Console for rich output
console = Console()


# =============================================================================
# Main Commands
# =============================================================================


@app.command()
def init() -> None:
    """Initialize RikaiOS locally.

    Creates the ~/.rikai directory and configuration files.
    """
    console.print()
    console.print(
        Panel.fit(
            "[bold blue]RikaiOS (理解OS)[/bold blue]\n"
            "[dim]Personal Context Operating System[/dim]",
            border_style="blue",
        )
    )
    console.print()

    # Create local directory
    local_path = ensure_local_path()
    console.print(f"[green]✓[/green] Created local directory: {local_path}")

    # Create default files
    self_md = local_path / "self.md"
    if not self_md.exists():
        self_md.write_text(
            "# Self\n\n"
            "Your persona, preferences, and who you are.\n\n"
            "## About Me\n\n"
            "<!-- Add your information here -->\n"
        )
        console.print(f"[green]✓[/green] Created {self_md}")

    now_md = local_path / "now.md"
    if not now_md.exists():
        now_md.write_text(
            "# Now\n\n"
            "Current focus and this week's priorities.\n\n"
            "## Current Focus\n\n"
            "<!-- What are you working on? -->\n"
        )
        console.print(f"[green]✓[/green] Created {now_md}")

    memory_md = local_path / "memory.md"
    if not memory_md.exists():
        memory_md.write_text(
            "# Memory\n\n"
            "Accumulated learnings and decisions made.\n\n"
            "## Learnings\n\n"
            "<!-- Your Tama will add learnings here -->\n"
        )
        console.print(f"[green]✓[/green] Created {memory_md}")

    # Create directories
    for subdir in ["projects", "sources/chats", "sources/docs", "sources/voice"]:
        (local_path / subdir).mkdir(parents=True, exist_ok=True)

    console.print()
    console.print("[bold green]RikaiOS initialized successfully![/bold green]")
    console.print()
    console.print("Next steps:")
    console.print("  1. Start infrastructure: [cyan]docker-compose up -d[/cyan]")
    console.print("  2. Check status: [cyan]rikai status[/cyan]")
    console.print("  3. Ask your Tama: [cyan]rikai ask 'What am I working on?'[/cyan]")
    console.print()


@app.command()
def status() -> None:
    """Check RikaiOS system status.

    Shows the status of all components: Umi (context lake) and Tama (agent).
    """
    console.print()
    console.print(
        Panel.fit(
            "[bold blue]RikaiOS Status[/bold blue]",
            border_style="blue",
        )
    )
    console.print()

    # Check local directory
    local_path = get_local_path()
    local_exists = local_path.exists()

    # Create status table
    table = Table(title="Components")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Details")

    # Local directory
    table.add_row(
        "Local (~/.rikai)",
        "[green]✓ Ready[/green]" if local_exists else "[red]✗ Not initialized[/red]",
        str(local_path) if local_exists else "Run 'rikai init'",
    )

    # Check infrastructure (basic connectivity check)
    settings = get_settings()

    # Postgres
    postgres_status = _check_postgres(settings.postgres_url)
    table.add_row(
        "Postgres",
        "[green]✓ Connected[/green]" if postgres_status else "[yellow]○ Not connected[/yellow]",
        settings.postgres_url.split("@")[-1] if "@" in settings.postgres_url else "localhost:5432",
    )

    # Qdrant
    qdrant_status = _check_qdrant(settings.qdrant_url)
    table.add_row(
        "Qdrant",
        "[green]✓ Connected[/green]" if qdrant_status else "[yellow]○ Not connected[/yellow]",
        settings.qdrant_url,
    )

    # MinIO
    minio_status = _check_minio(settings.minio_endpoint)
    table.add_row(
        "MinIO",
        "[green]✓ Connected[/green]" if minio_status else "[yellow]○ Not connected[/yellow]",
        settings.minio_endpoint,
    )

    # Tama (agent) - not implemented yet
    table.add_row(
        "Tama (Agent)",
        "[dim]○ Not configured[/dim]",
        "Coming in Phase 2",
    )

    console.print(table)
    console.print()

    if not local_exists:
        console.print("[yellow]Tip: Run 'rikai init' to initialize RikaiOS[/yellow]")
    elif not (postgres_status and qdrant_status and minio_status):
        console.print(
            "[yellow]Tip: Run 'docker-compose up -d' to start infrastructure[/yellow]"
        )
    console.print()


@app.command()
def ask(
    query: str = typer.Argument(..., help="Question to ask Tama"),
    local: bool = typer.Option(False, "--local", "-l", help="Use local agent (no Letta)"),
) -> None:
    """Ask your Tama a question.

    Uses Letta agent by default, or local mode with --local flag.
    """
    import asyncio
    import os

    console.print()
    console.print(f"[dim]You:[/dim] {query}")
    console.print()

    async def do_ask():
        try:
            if local or not os.getenv("LETTA_API_KEY"):
                # Use local agent (requires ANTHROPIC_API_KEY)
                if not os.getenv("ANTHROPIC_API_KEY"):
                    console.print(
                        Panel(
                            "[yellow]No API keys configured.[/yellow]\n\n"
                            "Set LETTA_API_KEY for Letta agent, or\n"
                            "Set ANTHROPIC_API_KEY for local agent mode.",
                            title="[bold]Configuration Required[/bold]",
                            border_style="yellow",
                        )
                    )
                    return

                from rikaios.tama.agent import LocalTamaAgent

                console.print("[dim]Using local agent mode...[/dim]")
                async with LocalTamaAgent() as tama:
                    response = await tama.chat(query)
                    console.print(Panel(
                        response.message,
                        title="[bold cyan]Tama (魂)[/bold cyan]",
                        border_style="cyan",
                    ))

                    if response.context_used:
                        console.print(f"[dim]Used {len(response.context_used)} context items[/dim]")
            else:
                # Use Letta agent
                from rikaios.tama.agent import TamaAgent

                async with TamaAgent() as tama:
                    response = await tama.chat(query)
                    console.print(Panel(
                        response.message,
                        title="[bold cyan]Tama (魂)[/bold cyan]",
                        border_style="cyan",
                    ))

                    if response.context_used:
                        console.print(f"[dim]Used {len(response.context_used)} context items[/dim]")

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            console.print("[yellow]Make sure infrastructure is running: docker-compose up -d[/yellow]")

    asyncio.run(do_ask())
    console.print()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Show version"),
) -> None:
    """RikaiOS (理解OS) - Personal Context Operating System."""
    if version:
        console.print(f"RikaiOS version {__version__}")
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        console.print()
        console.print(
            Panel.fit(
                "[bold blue]RikaiOS (理解OS)[/bold blue]\n"
                "[dim]Personal Context Operating System[/dim]\n\n"
                f"Version {__version__}",
                border_style="blue",
            )
        )
        console.print()
        console.print("Use [cyan]rikai --help[/cyan] for available commands.")
        console.print()


# =============================================================================
# Umi Commands
# =============================================================================


@umi_app.command("status")
def umi_status() -> None:
    """Check Umi (context lake) status."""
    console.print()
    console.print(
        Panel.fit(
            "[bold cyan]Umi (海) - Context Lake[/bold cyan]",
            border_style="cyan",
        )
    )
    console.print()

    settings = get_settings()

    table = Table(title="Storage Layers")
    table.add_column("Layer", style="cyan")
    table.add_column("Status")
    table.add_column("Endpoint")

    # Postgres
    postgres_status = _check_postgres(settings.postgres_url)
    table.add_row(
        "Postgres (metadata)",
        "[green]✓ Connected[/green]" if postgres_status else "[red]✗ Disconnected[/red]",
        settings.postgres_url.split("@")[-1] if "@" in settings.postgres_url else "localhost:5432",
    )

    # Qdrant
    qdrant_status = _check_qdrant(settings.qdrant_url)
    table.add_row(
        "Qdrant (vectors)",
        "[green]✓ Connected[/green]" if qdrant_status else "[red]✗ Disconnected[/red]",
        settings.qdrant_url,
    )

    # MinIO
    minio_status = _check_minio(settings.minio_endpoint)
    table.add_row(
        "MinIO (objects)",
        "[green]✓ Connected[/green]" if minio_status else "[red]✗ Disconnected[/red]",
        settings.minio_endpoint,
    )

    console.print(table)
    console.print()

    all_connected = postgres_status and qdrant_status and minio_status
    if all_connected:
        console.print("[bold green]Umi is fully operational![/bold green]")
    else:
        console.print("[yellow]Some services are not running. Start with:[/yellow]")
        console.print("  [cyan]docker-compose up -d[/cyan]")
    console.print()


@umi_app.command("sync")
def umi_sync(
    direction: str = typer.Argument("pull", help="Sync direction: 'pull' or 'push'"),
) -> None:
    """Sync between Umi (cloud) and local ~/.rikai/.

    pull: Download from Umi to local markdown files
    push: Upload local changes back to Umi
    """
    import asyncio
    from rikaios.umi import UmiClient
    from rikaios.umi.sync import UmiSync

    console.print()
    console.print(f"[cyan]Syncing ({direction})...[/cyan]")

    async def do_sync():
        try:
            async with UmiClient() as umi:
                sync = UmiSync(umi)
                if direction == "pull":
                    counts = await sync.pull()
                    console.print(
                        f"[green]✓[/green] Pulled {counts['entities']} entities, "
                        f"{counts['documents']} documents"
                    )
                elif direction == "push":
                    counts = await sync.push()
                    console.print(f"[green]✓[/green] Pushed {counts['entities']} entities")
                else:
                    console.print(f"[red]Unknown direction: {direction}[/red]")
        except Exception as e:
            console.print(f"[red]Sync failed: {e}[/red]")
            console.print("[yellow]Is the infrastructure running? Try: docker-compose up -d[/yellow]")

    asyncio.run(do_sync())
    console.print()


@umi_app.command("search")
def umi_search(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(5, "--limit", "-n", help="Number of results"),
) -> None:
    """Semantic search across your context lake."""
    import asyncio
    from rikaios.umi import UmiClient

    console.print()
    console.print(f"[cyan]Searching for:[/cyan] {query}")
    console.print()

    async def do_search():
        try:
            async with UmiClient() as umi:
                results = await umi.search(query, limit=limit)

                if not results:
                    console.print("[dim]No results found[/dim]")
                    return

                table = Table(title="Search Results")
                table.add_column("Score", style="cyan", width=8)
                table.add_column("Type", style="green", width=15)
                table.add_column("Content")

                for result in results:
                    # Truncate content
                    content = result.content[:100] + "..." if len(result.content) > 100 else result.content
                    table.add_row(
                        f"{result.score:.3f}",
                        result.source_type,
                        content,
                    )

                console.print(table)
        except Exception as e:
            console.print(f"[red]Search failed: {e}[/red]")
            console.print("[yellow]Is the infrastructure running? Try: docker-compose up -d[/yellow]")

    asyncio.run(do_search())
    console.print()


# =============================================================================
# Tama Commands
# =============================================================================


@tama_app.command("status")
def tama_status() -> None:
    """Check Tama (agent) status."""
    import os

    console.print()
    console.print(
        Panel.fit(
            "[bold magenta]Tama (魂) - Your Digital Soul[/bold magenta]",
            border_style="magenta",
        )
    )
    console.print()

    table = Table(title="Agent Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Status")
    table.add_column("Details")

    # Letta API Key
    letta_key = os.getenv("LETTA_API_KEY")
    table.add_row(
        "LETTA_API_KEY",
        "[green]✓ Set[/green]" if letta_key else "[yellow]○ Not set[/yellow]",
        "Letta agent mode" if letta_key else "Get one at app.letta.com",
    )

    # Anthropic API Key (for local mode)
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    table.add_row(
        "ANTHROPIC_API_KEY",
        "[green]✓ Set[/green]" if anthropic_key else "[yellow]○ Not set[/yellow]",
        "Local agent mode" if anthropic_key else "For --local mode",
    )

    console.print(table)
    console.print()

    if letta_key:
        console.print("[bold green]Tama is ready with Letta![/bold green]")
        console.print("Use: [cyan]rikai ask 'your question'[/cyan]")
    elif anthropic_key:
        console.print("[bold yellow]Tama available in local mode[/bold yellow]")
        console.print("Use: [cyan]rikai ask --local 'your question'[/cyan]")
    else:
        console.print("[yellow]Set an API key to enable Tama[/yellow]")
    console.print()


@tama_app.command("chat")
def tama_chat(
    local: bool = typer.Option(False, "--local", "-l", help="Use local agent"),
) -> None:
    """Start an interactive chat with Tama."""
    import asyncio
    import os

    console.print()
    console.print(
        Panel.fit(
            "[bold magenta]Tama (魂) - Interactive Chat[/bold magenta]\n"
            "[dim]Type 'quit' or 'exit' to end the conversation[/dim]",
            border_style="magenta",
        )
    )
    console.print()

    async def chat_loop():
        try:
            if local or not os.getenv("LETTA_API_KEY"):
                if not os.getenv("ANTHROPIC_API_KEY"):
                    console.print("[red]No API keys configured[/red]")
                    return

                from rikaios.tama.agent import LocalTamaAgent
                agent_class = LocalTamaAgent
                console.print("[dim]Using local agent mode[/dim]")
            else:
                from rikaios.tama.agent import TamaAgent
                agent_class = TamaAgent
                console.print("[dim]Connected to Letta[/dim]")

            console.print()

            async with agent_class() as tama:
                while True:
                    try:
                        user_input = console.input("[bold cyan]You:[/bold cyan] ")
                    except (KeyboardInterrupt, EOFError):
                        break

                    if user_input.lower() in ("quit", "exit", "bye"):
                        console.print("\n[dim]Goodbye![/dim]")
                        break

                    if not user_input.strip():
                        continue

                    response = await tama.chat(user_input)
                    console.print(f"\n[bold magenta]Tama:[/bold magenta] {response.message}\n")

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    asyncio.run(chat_loop())


@tama_app.command("memory")
def tama_memory() -> None:
    """Show Tama's current memory state."""
    import asyncio
    import os

    console.print()

    async def show_memory():
        if not os.getenv("LETTA_API_KEY"):
            console.print("[yellow]Memory view requires LETTA_API_KEY[/yellow]")
            return

        try:
            from rikaios.tama.agent import TamaAgent

            async with TamaAgent() as tama:
                memory = await tama.get_memory()

                for label, value in memory.items():
                    console.print(Panel(
                        value[:500] + "..." if len(value) > 500 else value,
                        title=f"[bold]{label}[/bold]",
                        border_style="cyan",
                    ))

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    asyncio.run(show_memory())
    console.print()


# =============================================================================
# Connector Commands
# =============================================================================


@connector_app.command("list")
def connector_list() -> None:
    """List available connectors."""
    console.print()
    console.print(
        Panel.fit(
            "[bold yellow]Data Connectors[/bold yellow]",
            border_style="yellow",
        )
    )
    console.print()

    table = Table(title="Available Connectors")
    table.add_column("Name", style="cyan")
    table.add_column("Mode")
    table.add_column("Description")

    connectors = [
        ("files", "push", "Local file watcher - monitors ~/.rikai/sources"),
        ("git", "pull", "Git repository metadata - README, commits, structure"),
        ("chat", "pull", "LLM chat imports - Claude, ChatGPT exports"),
        ("google", "pull", "Google Docs/Drive - requires OAuth setup"),
    ]

    for name, mode, desc in connectors:
        table.add_row(name, mode, desc)

    console.print(table)
    console.print()


@connector_app.command("sync")
def connector_sync(
    name: str = typer.Argument(..., help="Connector name: files, git, chat, google"),
    path: str = typer.Option(None, "--path", "-p", help="Path to sync (for files/git)"),
) -> None:
    """Run a connector sync operation."""
    import asyncio
    from rikaios.umi import UmiClient

    console.print()
    console.print(f"[cyan]Syncing {name} connector...[/cyan]")
    console.print()

    async def do_sync():
        try:
            async with UmiClient() as umi:
                if name == "files":
                    from rikaios.connectors import FilesConnector, FilesConnectorConfig

                    config = FilesConnectorConfig()
                    if path:
                        config.watch_paths = [path]
                    connector = FilesConnector(config)

                elif name == "git":
                    from rikaios.connectors import GitConnector, GitConnectorConfig

                    config = GitConnectorConfig()
                    if path:
                        config.repo_paths = [path]
                    connector = GitConnector(config)

                elif name == "chat":
                    from rikaios.connectors import ChatConnector, ChatConnectorConfig

                    config = ChatConnectorConfig()
                    if path:
                        config.import_paths = [path]
                    connector = ChatConnector(config)

                elif name == "google":
                    from rikaios.connectors import GoogleConnector

                    connector = GoogleConnector()

                else:
                    console.print(f"[red]Unknown connector: {name}[/red]")
                    return

                await connector.initialize(umi)
                result = await connector.sync()

                if result.success:
                    console.print("[green]✓ Sync completed[/green]")
                    console.print(f"  Documents created: {result.documents_created}")
                    console.print(f"  Entities created: {result.entities_created}")
                else:
                    console.print("[red]✗ Sync failed[/red]")

                if result.errors:
                    console.print("[yellow]Errors:[/yellow]")
                    for err in result.errors:
                        console.print(f"  - {err}")

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            console.print("[yellow]Is the infrastructure running? Try: docker-compose up -d[/yellow]")

    asyncio.run(do_sync())
    console.print()


@connector_app.command("import-chat")
def connector_import_chat(
    path: str = typer.Argument(..., help="Path to chat export file or directory"),
) -> None:
    """Import LLM chat exports (Claude or ChatGPT)."""
    import asyncio
    from pathlib import Path as P

    file_path = P(path).expanduser()
    if not file_path.exists():
        console.print(f"[red]File not found: {path}[/red]")
        return

    console.print()
    console.print(f"[cyan]Importing chats from:[/cyan] {file_path}")
    console.print()

    async def do_import():
        try:
            from rikaios.umi import UmiClient
            from rikaios.connectors import ChatConnector, ChatConnectorConfig

            async with UmiClient() as umi:
                config = ChatConnectorConfig(import_paths=[str(file_path)])
                connector = ChatConnector(config)
                await connector.initialize(umi)
                result = await connector.sync()

                if result.success:
                    console.print("[green]✓ Import completed[/green]")
                    console.print(f"  Conversations imported: {result.documents_created}")
                else:
                    console.print("[red]✗ Import failed[/red]")

                if result.errors:
                    for err in result.errors:
                        console.print(f"  [yellow]{err}[/yellow]")

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    asyncio.run(do_import())
    console.print()


@connector_app.command("add-repo")
def connector_add_repo(
    path: str = typer.Argument(..., help="Path to git repository"),
) -> None:
    """Add a git repository to the context lake."""
    import asyncio
    from pathlib import Path as P

    repo_path = P(path).expanduser()
    if not repo_path.exists():
        console.print(f"[red]Path not found: {path}[/red]")
        return

    console.print()
    console.print(f"[cyan]Adding repository:[/cyan] {repo_path}")
    console.print()

    async def do_add():
        try:
            from rikaios.umi import UmiClient
            from rikaios.connectors import GitConnector

            async with UmiClient() as umi:
                connector = GitConnector()
                await connector.initialize(umi)
                result = await connector.add_repo(str(repo_path))

                if result.success:
                    console.print("[green]✓ Repository added[/green]")
                    if result.entities_created:
                        console.print(f"  Created project entity")
                    if result.documents_created:
                        console.print(f"  Stored commit history")
                else:
                    console.print("[red]✗ Failed to add repository[/red]")

                if result.errors:
                    for err in result.errors:
                        console.print(f"  [yellow]{err}[/yellow]")

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    asyncio.run(do_add())
    console.print()


# =============================================================================
# Server Commands
# =============================================================================


@app.command()
def serve(
    port: int = typer.Option(8000, "--port", "-p", help="Port to run the API on"),
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind to"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload"),
) -> None:
    """Start the RikaiOS REST API server."""
    import uvicorn

    console.print()
    console.print(
        Panel.fit(
            "[bold green]Starting RikaiOS API Server[/bold green]\n"
            f"[dim]http://{host}:{port}[/dim]",
            border_style="green",
        )
    )
    console.print()

    console.print(f"[cyan]API Docs:[/cyan] http://{host}:{port}/docs")
    console.print(f"[cyan]Health:[/cyan] http://{host}:{port}/health")
    console.print()
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    console.print()

    uvicorn.run(
        "rikaios.servers.api:app",
        host=host,
        port=port,
        reload=reload,
    )


# =============================================================================
# Helper Functions
# =============================================================================


def _check_postgres(url: str) -> bool:
    """Check if Postgres is reachable."""
    try:
        import socket

        # Extract host and port from URL
        # postgresql://user:pass@host:port/db
        if "@" in url:
            host_port = url.split("@")[1].split("/")[0]
        else:
            host_port = "localhost:5432"

        if ":" in host_port:
            host, port_str = host_port.split(":")
            port = int(port_str)
        else:
            host = host_port
            port = 5432

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def _check_qdrant(url: str) -> bool:
    """Check if Qdrant is reachable."""
    try:
        import socket
        from urllib.parse import urlparse

        parsed = urlparse(url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 6333

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def _check_minio(endpoint: str) -> bool:
    """Check if MinIO is reachable."""
    try:
        import socket

        if ":" in endpoint:
            host, port_str = endpoint.split(":")
            port = int(port_str)
        else:
            host = endpoint
            port = 9000

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


if __name__ == "__main__":
    app()
