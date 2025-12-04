from typing import Protocol, List, Optional
from pathlib import Path
import subprocess
import shutil

class GitError(Exception):
    pass

class GitProvider(Protocol):
    def get_current_branch(self, path: Path) -> str:
        ...
    
    def create_worktree(self, repo_path: Path, branch: str, path: Path) -> None:
        ...
    
    def remove_worktree(self, path: Path) -> None:
        ...
        
    def get_commit_hash(self, path: Path, ref: str = "HEAD") -> str:
        ...

    def get_common_base(self, path: Path, commit1: str, commit2: str) -> str:
        ...
        
    def checkout(self, path: Path, ref: str, force: bool = False) -> None:
        ...
        
    def clean(self, path: Path) -> None:
        ...
        
    def fetch(self, path: Path) -> None:
        ...
        
    def pull(self, path: Path, rebase: bool = False) -> None:
        ...

    def push(self, path: Path, remote: str = "origin", branch: str = "main") -> None:
        ...

    def update_submodules(self, path: Path) -> None:
        ...

    def set_upstream(self, path: Path, branch: str, upstream: str) -> None:
        ...

class ShellGitProvider:
    def _run(self, args: List[str], cwd: Path) -> str:
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise GitError(f"Git command failed: {e.stderr}") from e

    def get_current_branch(self, path: Path) -> str:
        return self._run(["rev-parse", "--abbrev-ref", "HEAD"], path)

    def create_worktree(self, repo_path: Path, branch: str, path: Path) -> None:
        # Check if branch exists
        try:
            self._run(["rev-parse", "--verify", branch], repo_path)
            exists = True
        except GitError:
            exists = False

        cmd = ["worktree", "add", "-f"]
        if not exists:
            cmd.extend(["-b", branch, str(path)])
        else:
            cmd.extend([str(path), branch])
            
        self._run(cmd, repo_path)

    def remove_worktree(self, path: Path) -> None:
        # Prune worktrees from the base repo context? 
        # Usually we delete the directory and then prune.
        # But here we might be inside the worktree or outside.
        # Assuming we are calling this from outside or we just delete the dir.
        # Proper way: git worktree remove <path>
        # But we need to be in a valid git repo.
        if path.exists():
            # We need to run this from the main repo or another worktree
            # For now, let's assume we just remove the directory and prune later if needed,
            # OR we try to run worktree remove from the path itself if it exists?
            # Actually, `git worktree remove .` works inside.
            try:
                self._run(["worktree", "remove", "--force", "."], path)
            except GitError:
                # Fallback to rm -rf if git fails (e.g. already broken)
                if path.exists():
                    shutil.rmtree(path)

    def get_commit_hash(self, path: Path, ref: str = "HEAD") -> str:
        return self._run(["rev-parse", ref], path)

    def get_common_base(self, path: Path, commit1: str, commit2: str) -> str:
        return self._run(["merge-base", commit1, commit2], path)

    def checkout(self, path: Path, ref: str, force: bool = False) -> None:
        args = ["checkout", ref]
        if force:
            args.insert(1, "-f")
        self._run(args, path)

    def clean(self, path: Path) -> None:
        self._run(["clean", "-fdx"], path)
        self._run(["reset", "--hard", "HEAD"], path)

    def fetch(self, path: Path) -> None:
        self._run(["fetch", "--all"], path)

    def pull(self, path: Path, rebase: bool = False) -> None:
        args = ["pull"]
        if rebase:
            args.append("--rebase")
        self._run(args, path)

    def push(self, path: Path, remote: str = "origin", branch: str = "main") -> None:
        self._run(["push", remote, branch], path)

    def update_submodules(self, path: Path) -> None:
        self._run(["submodule", "update", "--init", "--recursive"], path)

    def set_upstream(self, path: Path, branch: str, upstream: str) -> None:
        self._run(["branch", "--set-upstream-to", upstream, branch], path)

class MockGitProvider:
    def __init__(self):
        self.calls = []
        self.responses = {}
        self.worktrees = {} # path -> branch

    def get_current_branch(self, path: Path) -> str:
        self.calls.append(("get_current_branch", path))
        return self.responses.get("get_current_branch", "main")

    def create_worktree(self, repo_path: Path, branch: str, path: Path) -> None:
        self.calls.append(("create_worktree", repo_path, branch, path))
        self.worktrees[str(path)] = branch

    def remove_worktree(self, path: Path) -> None:
        self.calls.append(("remove_worktree", path))
        if str(path) in self.worktrees:
            del self.worktrees[str(path)]

    def get_commit_hash(self, path: Path, ref: str = "HEAD") -> str:
        self.calls.append(("get_commit_hash", path, ref))
        return self.responses.get(f"get_commit_hash:{ref}", "hash123")

    def get_common_base(self, path: Path, commit1: str, commit2: str) -> str:
        self.calls.append(("get_common_base", path, commit1, commit2))
        return self.responses.get("get_common_base", "base_hash")

    def checkout(self, path: Path, ref: str, force: bool = False) -> None:
        self.calls.append(("checkout", path, ref, force))

    def clean(self, path: Path) -> None:
        self.calls.append(("clean", path))

    def fetch(self, path: Path) -> None:
        self.calls.append(("fetch", path))

    def pull(self, path: Path, rebase: bool = False) -> None:
        self.calls.append(("pull", path, rebase))

    def push(self, path: Path, remote: str = "origin", branch: str = "main") -> None:
        self.calls.append(("push", path, remote, branch))

    def update_submodules(self, path: Path) -> None:
        self.calls.append(("update_submodules", path))

    def set_upstream(self, path: Path, branch: str, upstream: str) -> None:
        self.calls.append(("set_upstream", path, branch, upstream))
