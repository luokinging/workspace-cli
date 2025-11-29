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
    name: str,
    base: Path = typer.Option(None, help="Path to base workspace (required if config missing)"),
):
    """
    Create a new workspace.

    If a configuration file (workspace.json) does not exist, you must provide --base to create one.
    
    Examples:
    
    # Create a new workspace using existing config
    $ workspace create feature-a
    
    # Create a new workspace and generate config (first run)
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
            # In new architecture, we don't need to specify repos manually.
            # They are defined by git submodules in the base path.
            # But WorkspaceConfig model might still expect a list.
            # We can auto-discover them or just leave it empty for now and let core handle it?
            # Core uses config.repos to iterate.
            # So we SHOULD discover them.
            
            # Auto-discover submodules from .gitmodules
            # This requires parsing .gitmodules or using git command.
            # Let's use git command.
            from workspace_cli.utils.git import get_submodule_status
            try:
                submodules = get_submodule_status(base_path)
                repos = [RepoConfig(name=Path(p).name, path=Path(p)) for p in submodules.keys()]
            except Exception:
                # Fallback or empty?
                repos = []

            config = WorkspaceConfig(
                base_path=base_path,
                repos=repos
            )
            
            save_path = Path.cwd() / "workspace.json"
            save_config(config, save_path)
            typer.echo(f"Created config at {save_path}")

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
            cwd = Path.cwd()
            base_name = config.base_path.name
            
            # Check if we are in a workspace dir: {base_name}-{name}
            # Or if we are in a repo subdir
            
            current_workspace_path = None
            # Check parents up to root
            for parent in [cwd] + list(cwd.parents):
                if (parent.name == base_name or parent.name.startswith(f"{base_name}-")) and parent.parent == config.base_path.parent:
                    current_workspace_path = parent
                    break
            
            if current_workspace_path:
                if current_workspace_path.name == base_name:
                     typer.echo("You are in the Base Workspace. Please specify a target workspace to preview.")
                     raise typer.Exit(code=1)
                workspace = current_workspace_path.name[len(base_name)+1:]
                typer.echo(f"Auto-detected workspace: {workspace}")
            else:
                typer.echo("Could not auto-detect workspace. Please specify --workspace or run from within a workspace.")
                raise typer.Exit(code=1)
            
        sync_core.start_preview(workspace, config, once=once)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

@app.command()
def sync():
    """
    Sync all workspaces.

    Updates Base Workspace from remote main, and propagates changes to all sibling workspaces.
    
    Example:
    
    $ workspace sync
    """
    try:
        config = load_config()
        sync_core.sync_workspaces(config)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
