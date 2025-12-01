import typer
from pathlib import Path
from typing import List, Optional
from workspace_cli.config import load_config
from workspace_cli.core import workspace as workspace_core
from workspace_cli.core import sync as sync_core

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
        try:
            config = load_config()
        except FileNotFoundError:
            if not base:
                typer.echo("Config not found. Please provide --base to create one.", err=True)
                raise typer.Exit(code=1)
            
            # Create new config
            from workspace_cli.models import WorkspaceConfig, RepoConfig
            from workspace_cli.config import save_config
            
            # Assume base path is absolute or relative to CWD
            base_path = base.resolve()
            config = WorkspaceConfig(
                base_path=base_path,
                workspaces={}
            )
            
            save_path = Path.cwd() / "workspace.json"
            save_config(config, save_path)
            typer.echo(f"Created config at {save_path}")

            typer.echo(f"Created config at {save_path}")

        for name in names:
            workspace_core.create_workspace(name, config)
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
        config = load_config()
        workspace_core.delete_workspace(name, config)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

@app.command()
def status():
    """
    Show workspace status.

    Lists all active workspaces and their paths.
    
    Example:
    
    $ workspace status
    """
    try:
        config = load_config()
        workspace_core.get_status(config)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

@app.command()
def preview(
    workspace: str = typer.Option(None, help="Target workspace name"),
    once: bool = typer.Option(False, "--once", help="Run sync once and exit (no live watch)")
):
    """
    Start preview sync.

    Syncs the specified workspace (or current workspace) to the preview environment and starts live watching.
    
    Examples:
    
    # Preview current workspace (must be run inside a workspace)
    $ workspace preview
    
    # Preview specific workspace
    $ workspace preview --workspace feature-a
    """
    try:
        config = load_config()
        
        # Auto-detection logic
        if not workspace:
            # Check if we are in a known workspace from config
            current_workspace_name = None
            for name, entry in config.workspaces.items():
                # Resolve path
                if not Path(entry.path).is_absolute():
                    ws_path = (config.base_path / entry.path).resolve()
                else:
                    ws_path = Path(entry.path).resolve()
                
                # Check if cwd is inside ws_path
                try:
                    Path.cwd().relative_to(ws_path)
                    current_workspace_name = name
                    break
                except ValueError:
                    continue
            
            if current_workspace_name:
                workspace = current_workspace_name
                typer.echo(f"Auto-detected workspace: {workspace}")
            else:
                typer.echo("Could not auto-detect workspace. Please specify --workspace or run from within a workspace.")
                raise typer.Exit(code=1)
            
        sync_core.start_preview(workspace, config, once=once)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

@app.command()
def clean_preview():
    """
    Clean preview workspace.
    
    Stops any running preview process, resets the base workspace to main,
    and removes untracked files.
    """
    try:
        config = load_config()
        sync_core.clean_preview(config)
        typer.secho("Preview workspace cleaned.", fg=typer.colors.GREEN)
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
        config = load_config()
        
        if rebuild_preview:
            sync_core.clean_preview(config)
            
        sync_core.sync_workspaces(config, sync_all=all)
        
        if rebuild_preview:
             # Detect workspace to rebuild preview for
            current_workspace_name = None
            for name, entry in config.workspaces.items():
                if not Path(entry.path).is_absolute():
                    ws_path = (config.base_path / entry.path).resolve()
                else:
                    ws_path = Path(entry.path).resolve()
                
                try:
                    Path.cwd().relative_to(ws_path)
                    current_workspace_name = name
                    break
                except ValueError:
                    continue
            
            if current_workspace_name:
                typer.secho(f"Rebuilding preview for {current_workspace_name}...", fg=typer.colors.BLUE)
                sync_core.rebuild_preview(current_workspace_name, config)
                typer.secho("Preview rebuilt.", fg=typer.colors.GREEN)

    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
