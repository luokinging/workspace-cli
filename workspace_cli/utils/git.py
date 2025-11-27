import subprocess
from pathlib import Path
from typing import List, Optional

class GitError(Exception):
    pass

def run_git_cmd(cmd: List[str], cwd: Path) -> str:
    """Run a git command and return the output."""
    try:
        result = subprocess.run(
            ["git"] + cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise GitError(f"Git command failed: {' '.join(cmd)}\nError: {e.stderr}")

def get_current_branch(repo_path: Path) -> str:
    """Get the current branch name."""
    return run_git_cmd(["rev-parse", "--abbrev-ref", "HEAD"], repo_path)

def is_dirty(repo_path: Path) -> bool:
    """Check if the repo has uncommitted changes."""
    # Check for modified files
    status = run_git_cmd(["status", "--porcelain"], repo_path)
    return bool(status)

def create_worktree(repo_path: Path, branch: str, path: Path) -> None:
    branch_exists = False
    try:
        run_git_cmd(["rev-parse", "--verify", branch], repo_path)
        branch_exists = True
    except GitError:
        branch_exists = False

    if branch_exists:
        try:
            run_git_cmd(["worktree", "add", str(path), branch], repo_path)
        except GitError as e:
            err_msg = str(e)
            if "already checked out" in err_msg:
                # If it's already checked out, we might want to force it or just fail?
                # For `create` command, if we are creating a new workspace, we want a new worktree.
                # Git allows multiple worktrees for same branch? No, usually not unless --force.
                # But wait, `stand` branch is per workspace? 
                # No, `workspace-{name}/stand`. So it should be unique to this workspace.
                # If it exists, it means we might be re-creating the workspace or it was left over.
                # Let's try force if standard add fails.
                run_git_cmd(["worktree", "add", "--force", str(path), branch], repo_path)
            elif "missing but already registered worktree" in err_msg:
                # Worktree registered but missing. Prune and retry.
                run_git_cmd(["worktree", "prune"], repo_path)
                run_git_cmd(["worktree", "add", str(path), branch], repo_path)
            else:
                raise e
    else:
        # Branch doesn't exist, create new
        run_git_cmd(["worktree", "add", "-b", branch, str(path)], repo_path)

def remove_worktree(path: Path) -> None:
    """Remove a worktree."""
    if path.exists():
        try:
            # Try to remove using git command from the worktree itself
            run_git_cmd(["worktree", "remove", "."], path)
        except GitError:
            # If that fails (e.g. forced), try force
            run_git_cmd(["worktree", "remove", "--force", "."], path)

def get_diff_files(repo_path: Path, target_branch: str) -> List[str]:
    """Get list of changed files compared to target branch."""
    output = run_git_cmd(["diff", "--name-only", target_branch], repo_path)
    if not output:
        return []
    return output.splitlines()

def stage_files(repo_path: Path, files: List[str]) -> None:
    """Stage specific files."""
    if not files:
        return
    run_git_cmd(["add"] + files, repo_path)

def checkout_new_branch(repo_path: Path, branch: str, force: bool = True) -> None:
    """Checkout a new branch, optionally forcing it."""
    cmd = ["checkout", "-b", branch]
    if force:
        # If branch exists, reset it? Or delete and recreate?
        # git checkout -B overwrites
        cmd = ["checkout", "-B", branch]
    run_git_cmd(cmd, repo_path)

def clone_repo(url: str, path: Path) -> None:
    """Clone a repository."""
    subprocess.run(["git", "clone", url, str(path)], check=True)
