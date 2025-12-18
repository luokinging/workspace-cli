import typer
from pathlib import Path
from typing import List, Optional
from workspace_cli.config import load_config
from workspace_cli.config import load_config

app = typer.Typer()

@app.callback()
def main(
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode"),
    log_file: Path = typer.Option(None, "--log-file", help="Path to log file")
):
    """
    Workspace CLI
    """
    from workspace_cli.utils.logger import setup_logging
    setup_logging(debug, log_file)
    if debug:
        from workspace_cli.utils.logger import get_logger
        logger = get_logger()
        logger.debug("Debug mode enabled")

@app.command()
def create(
    names: List[str] = typer.Argument(..., help="List of workspace names to create"),
    base: Path = typer.Option(None, help="Path to base workspace (required if config missing)"),
):
    """
    Create new workspace(s).

    If a configuration file (workspace.json) does not exist, you must provide --base to create one.
    
    Examples:
    
    # Create a single workspace
    $ workspace create feature-a
    
    # Create multiple workspaces
    $ workspace create feature-a feature-b feature-c
    
    # Create with base path (first run)
    $ workspace create feature-a --base /path/to/base
    """
    import asyncio
    from workspace_cli.config import find_config_root, load_config
    from workspace_cli.server.manager import WorkspaceManager
    from workspace_cli.client.api import DaemonClient
    
    config_path = find_config_root()
    client = DaemonClient()
    
    use_daemon = False
    if config_path and client.is_running():
        use_daemon = True
    
    try:
        if use_daemon:
            if base:
                client.create_workspaces(names, base_path=str(base.resolve()))
            else:
                client.create_workspaces(names)
            typer.echo(f"Created workspaces via daemon: {', '.join(names)}")
        else:
            # Local execution
            if not config_path:
                if not base:
                    typer.echo("Error: No workspace.json found. You must provide --base to initialize the project.", err=True)
                    raise typer.Exit(code=1)
                
                manager = WorkspaceManager.get_instance(base)
                asyncio.run(manager.initialize_project(base))
                typer.echo(f"Initialized new project at {base}")
            else:
                # Load existing config for local manager
                config = load_config(config_path)
                manager = WorkspaceManager.get_instance(config.base_path)
                asyncio.run(manager.initialize())

            asyncio.run(manager.create_workspace(names))
            typer.echo(f"Created workspaces locally: {', '.join(names)}")
            
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        # import traceback
        # traceback.print_exc()
        raise typer.Exit(code=1)

@app.command()
def delete(name: str):
    """
    Delete a workspace.

    Removes the workspace directory and its associated worktrees.
    
    Example:
    
    $ workspace delete feature-a
    """
    import asyncio
    from workspace_cli.client.api import DaemonClient
    from workspace_cli.config import load_config, find_config_root
    from workspace_cli.server.manager import WorkspaceManager
    
    config_path = find_config_root()
    client = DaemonClient()
    use_daemon = config_path and client.is_running()

    try:
        if use_daemon:
            client.delete_workspace(name)
            typer.echo(f"Deleted workspace via daemon: {name}")
        else:
            if not config_path:
                typer.echo("Error: No workspace configuration found.", err=True)
                raise typer.Exit(code=1)
            
            config = load_config(config_path)
            manager = WorkspaceManager.get_instance(config.base_path)
            asyncio.run(manager.initialize())
            asyncio.run(manager.delete_workspace(name))
            typer.echo(f"Deleted workspace locally: {name}")
            
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

@app.command()
def status():
    """
    Show workspace status.
    """
    from workspace_cli.client.api import DaemonClient
    from workspace_cli.config import load_config, find_config_root
    from workspace_cli.models import Workspace
    
    client = DaemonClient()
    daemon_running = client.is_running()
    
    try:
        if daemon_running:
            status = client.get_status()
            typer.echo(f"Daemon Status: {'Syncing' if status.is_syncing else 'Idle'} (Running)")
            if status.active_preview:
                typer.echo(f"Active Preview: {status.active_preview}")
            
            typer.echo("\nWorkspaces:")
            for ws in status.workspaces:
                typer.echo(f"- {ws.name} ({ws.path}) [{'Active' if ws.is_active else 'Inactive'}]")
        else:
            typer.echo("Daemon is not running.")
            config_path = find_config_root()
            if config_path:
                config = load_config(config_path)
                typer.echo("\nWorkspaces (from config):")
                for name, entry in config.workspaces.items():
                    # Map config entry to Workspace model for display
                    ws_path = Path(entry.path)
                    if not ws_path.is_absolute():
                        ws_path = (config.base_path / ws_path).resolve()
                    typer.echo(f"- {name} ({ws_path}) [Inactive]")
            else:
                typer.echo("No workspace config found.")
                
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

@app.command()
def daemon(
    host: str = typer.Option("127.0.0.1", help="Host to bind"),
    port: int = typer.Option(9000, help="Port to bind"),
    reload: bool = typer.Option(False, help="Enable auto-reload"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging")
):
    """
    Start the Workspace Daemon.
    """
    import uvicorn
    import os
    
    if debug:
        os.environ["WORKSPACE_DEBUG"] = "1"
        typer.echo("Debug mode enabled")

    typer.echo(f"Starting daemon on {host}:{port}...")
    uvicorn.run("workspace_cli.server.app:app", host=host, port=port, reload=reload)

@app.command()
def preview(
    workspace: str = typer.Option(None, help="Target workspace name"),
    once: bool = typer.Option(False, "--once", help="Run sync once and exit (no live watch)"),
    rebuild: bool = typer.Option(False, "--rebuild", help="Force rebuild of preview")
):
    """
    Start preview sync.
    """

    try:
        from workspace_cli.client.api import DaemonClient
        client = DaemonClient()
        
        if not workspace:
            from workspace_cli.config import detect_current_workspace
            workspace = detect_current_workspace()
            
            if not workspace:
                typer.echo("Could not auto-detect workspace. Please specify --workspace.")
                raise typer.Exit(code=1)
            
            if workspace == "base":
                 typer.echo("You are in the Base Workspace. Please specify a feature workspace to preview.")
                 raise typer.Exit(code=1)
                 
            typer.echo(f"Auto-detected workspace: {workspace}")

        client.switch_preview(workspace, rebuild=rebuild)
        typer.echo(f"Preview switched to {workspace}")
        
        if not once:
            typer.echo("Streaming logs... (Ctrl+C to stop)")
            from rich.console import Console
            console = Console()
            try:
                for line in client.stream_logs():
                    console.print(line)
            except KeyboardInterrupt:
                typer.echo("Stopping preview...")
                # Optional: Send stop request? Or just disconnect?
                # If we disconnect, server might keep running until next switch.
                # But requirement says "resident command line will automatically exit".
                # If user Ctrl+C, they exit.
                pass
            except Exception as e:
                # If server closes connection (e.g. new preview), we might get here or just loop ends.
                typer.echo(f"Disconnected: {e}")
        
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

@app.command()
def sync(
    all: bool = typer.Option(False, "--all", help="Sync all workspaces (current + siblings)"),
    rebuild_preview: bool = typer.Option(True, "--rebuild-preview/--no-rebuild-preview", help="Clean and rebuild preview after sync")
):
    """
    Sync workspaces.

    By default, syncs only the current workspace (pulls from origin).
    Use --all to sync all workspaces (Base + Siblings).
    
    If --rebuild-preview is set (default), it will also:
    1. Clean the preview workspace (stop process, reset to main).
    2. Perform the git sync.
    3. Rebuild the preview content (if inside a workspace).
    """
    import asyncio
    from workspace_cli.client.api import DaemonClient
    from workspace_cli.config import load_config, find_config_root, detect_current_workspace
    from workspace_cli.server.manager import WorkspaceManager
    
    config_path = find_config_root()
    client = DaemonClient()
    use_daemon = config_path and client.is_running()

    try:
        # Determine workspace
        workspace_name = None
        if not all:
            workspace_name = detect_current_workspace()
            
            if not workspace_name:
                typer.echo("Could not auto-detect workspace. Please run from within a workspace or use --all.")
                raise typer.Exit(code=1)
        
        target = workspace_name if workspace_name and workspace_name != "base" else None

        if use_daemon:
            client.sync_workspace(
                workspace_name=target if target else "dummy", 
                sync_all=all, 
                rebuild_preview=rebuild_preview
            )
            typer.echo("Sync completed via daemon.")
        else:
            if not config_path:
                typer.echo("Error: No workspace configuration found.", err=True)
                raise typer.Exit(code=1)
                
            config = load_config(config_path)
            manager = WorkspaceManager.get_instance(config.base_path)
            asyncio.run(manager.initialize())
            asyncio.run(manager.sync_workspace(
                workspace_name=target if target else "dummy",
                sync_all=all,
                rebuild_preview=rebuild_preview
            ))
            typer.echo("Sync completed locally.")
        
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
