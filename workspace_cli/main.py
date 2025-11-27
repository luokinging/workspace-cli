import typer
from pathlib import Path
from typing import List
from workspace_cli.config import load_config
from workspace_cli.core import workspace as workspace_core
from workspace_cli.core import sync as sync_core

app = typer.Typer()

@app.command()
def create(
    name: str,
    base: Path = typer.Option(None, help="Path to base workspace (required if config missing)"),
    repo: List[str] = typer.Option(None, help="List of repo names (required if config missing)")
):
    """
    Create a new workspace.

    If a configuration file (workspace.json) does not exist, you must provide --base and --repo to create one.
    
    Examples:
    
    # Create a new workspace using existing config
    $ workspace create feature-a
    
    # Create a new workspace and generate config (first run)
    $ workspace create feature-a --base /path/to/base --repo frontend --repo backend
    """
    try:
        try:
            config = load_config()
        except FileNotFoundError:
            if not base or not repo:
                typer.echo("Config not found. Please provide --base and --repo to create one.", err=True)
                raise typer.Exit(code=1)
            
            # Create new config
            from workspace_cli.models import WorkspaceConfig, RepoConfig
            from workspace_cli.config import save_config
            
            # Assume base path is absolute or relative to CWD
            base_path = base.resolve()
            repos = [RepoConfig(name=r, path=Path(r)) for r in repo]
            
            config = WorkspaceConfig(
                base_path=base_path,
                repos=repos
            )
            
            # Save to workspace.json in the parent of base_path (Work Root)
            # Or current directory? 
            # Requirement: "create automatically creates config file"
            # Let's save it in the current directory if we are running from root, 
            # or maybe better: save it where load_config looks for it.
            # load_config looks in CWD and parents.
            # Let's save to CWD/workspace.json for simplicity and predictability.
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
def preview(workspace: str = typer.Option(None, help="Target workspace name")):
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
        # If workspace is not provided, try to infer from current directory
        if not workspace:
            # TODO: Infer logic
            typer.echo("Please specify --workspace")
            raise typer.Exit(code=1)
            
        sync_core.start_preview(workspace, config)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

@app.command()
def syncrule():
    """
    Sync rules repo.

    Commits and pushes changes in the rules repo from the current workspace, then merges them to other workspaces.
    
    Example:
    
    $ workspace syncrule
    """
    try:
        config = load_config()
        sync_core.sync_rules(config)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
