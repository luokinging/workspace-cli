# Refactoring Plan: Workspace CLI (Spec-Driven)

> Based on `doc.md` requirements.

## 1. Architecture Specification

### 1.1. Core Concept

- **Workspace Repo**: The top-level folder is now a Git repository.
- **Submodules**: Child repositories are managed exclusively via `.gitmodules`.
- **Configuration**: `workspace.json` is simplified. It no longer defines the repo list (source of truth is `.gitmodules`), but may still hold preferences like `workspace_expand_folder`.

### 1.2. Directory Structure

```text
/Project/
  BaseWorkspace/ (Git Repo, Main Branch)
    .git/
    .gitmodules
    backend/ (Submodule)
    frontend/ (Submodule)

  BaseWorkspace-featureA/ (Git Worktree of BaseWorkspace)
    .git (file, pointing to BaseWorkspace/.git/worktrees/...)
    backend/ (Submodule, initialized)
    frontend/ (Submodule, initialized)
```

## 2. Functional Specifications

### 2.1. Git Utilities (`utils/git.py`)

- **New Capabilities**:
  - `get_merge_base(repo_path, commit_a, commit_b)`: Find common ancestor.
  - `submodule_update(repo_path, init=True, recursive=True)`: Wrapper for `git submodule update`.
  - `get_submodule_status(repo_path)`: List submodules and their current commits.
  - `fetch_remote(repo_path, remote="origin")`: Fetch updates.
  - `merge_branch(repo_path, source_branch)`: Merge source into current.

### 2.2. Command: `create`

- **Input**: `name` (Workspace Name), `base` (Base Workspace Path).
- **Pre-condition**: `base` must be a valid git repo.
- **Logic**:
  1.  Validate `base` has `.git`.
  2.  Calculate `new_path = base.parent / "{base.name}-{name}"`.
  3.  Run `git worktree add -b workspace-{name}/stand {new_path}` in `base`.
  4.  Run `git submodule update --init --recursive` in `new_path`.
  5.  (Optional) Create/Update `workspace.json` in `new_path` if needed for other configs.

### 2.3. Command: `preview`

- **Input**: `workspace` (Target Workspace Name).
- **Logic**:
  1.  **Context**: Identify `Source` (Current) and `Target` (Preview) workspaces.
  2.  **Prep Target**:
      - In `Target`, for each submodule: `git fetch origin main` -> `git merge origin/main`.
  3.  **Sync Loop** (for each submodule):
      - **Source**: Get current commit/state.
      - **Target**:
        - Find `common_root = git merge-base source_commit target_main`.
        - `git checkout -B preview common_root` (Reset/Create preview branch at common root).
      - **Copy**: `shutil.copytree(source_files, target_files, dirs_exist_ok=True)` (Overwrite target with source files).
  4.  **Watch**: Start file watcher (existing logic, adapted to new paths).
  5.  **Cleanup**: On exit, checkout `main` in Target submodules and delete `preview` branch.

### 2.4. Command: `sync` (New)

- **Input**: None (runs on current workspace context).
- **Logic**:
  1.  **Identify Base**: Find the root git repo (Base Workspace).
  2.  **Update Base**: `git pull origin main` in Base.
  3.  **Update Siblings**: Iterate all peer worktrees (workspaces).
  4.  **Per Workspace**:
      - `git merge origin/main` (Merge updates into current `stand` branch).
      - `git submodule update --init --recursive` (Sync submodules to new pointers).

## 3. Testing Plan

### 3.1. Unit Tests

- Mock `subprocess.run` to verify correct Git commands are issued for submodules and worktrees.
- Test `get_merge_base` logic parsing.

### 3.2. Functional/E2E Tests (`tests/functional/`)

- **Setup**:
  - Create a temporary "Remote" repo with submodules.
  - Clone it as "Base Workspace".
- **Test `create`**:
  - Run `workspace create test-ws`.
  - Verify directory exists, is a worktree, and submodules are populated.
- **Test `sync`**:
  - Push update to "Remote".
  - Run `workspace sync`.
  - Verify "Base" and "test-ws" have the update.
- **Test `preview`**:
  - Modify file in "test-ws" (Source).
  - Run `workspace preview`.
  - Verify file copied to "Base" (Target) and submodule is on `preview` branch.

## 4. Documentation Updates

- **README.md**:
  - **Breaking Change Warning**: Explain the shift to Git-native workspaces.
  - **Setup Guide**: How to set up the Base Workspace (clone recursive).
  - **Command Reference**:
    - Update `create` (no repo list needed).
    - Add `sync`.
    - Remove `syncrule`.
