# E2E Test Documentation (Client-Server Architecture)

This document details the End-to-End (E2E) test cases for the refactored **Client-Server** architecture of `workspace-cli`.

## Test Environment Preparation

1.  **Work Directory**: `test-e2e-work-root`.
    - **Create**: Ensure this directory is created before running tests.
    - **Cleanup**: Delete this directory after tests complete successfully.
2.  **Script Validation**:
    - Ensure the test script (`tests/e2e/test_full_scenario.py`) covers **all** scenarios listed below.
    - If a scenario is missing or outdated, update the script before running.
3.  **Prerequisites**:
    - `workspace-cli` installed (or runnable via `python -m workspace_cli.main`).
    - Git environment available.
    - Python 3.9+.

## Test Cases

### Case 1: Environment Initialization (Setup)

**Goal**: Simulate a real remote repository environment with main repo and submodules.

**Steps**:

1.  **Create Remote Submodules**:
    - Create `remote-backend` repo, commit initial files.
    - Create `remote-frontend` repo, commit initial files.
2.  **Create Remote Main Repo**:
    - Create `remote-main` repo.
    - Add `remote-backend` and `remote-frontend` as submodules.
    - Commit and push.
3.  **Clone Base Workspace**:
    - `git clone --recursive remote-main base-workspace`.
    - This serves as the "Base Workspace" (and default Preview Target).

### Case 2: Daemon Lifecycle (Daemon)

**Goal**: Verify Daemon start, status query, and shutdown.

**Steps**:

1.  **Start Daemon**:
    - Run `workspace daemon --port 8000` in background.
2.  **Check Status**:
    - Run `workspace status`.
    - **Verify**: Output shows "Daemon Status: Idle" and lists workspaces (initially empty or just base).
3.  **Keep Running**:
    - The Daemon must remain running for subsequent steps.

### Case 3: Create Workspace (Create)

**Goal**: Verify creating a new Worktree Workspace via Daemon.

**Steps**:

1.  **Execute Command**: `workspace create A --base $(pwd)/base-workspace`
2.  **Verify**:
    - Directory `base-workspace-A` exists.
    - It is a Git Worktree of `base-workspace`.
    - Current branch is `workspace-A/stand`.
    - Submodules are initialized.
    - `workspace status` shows `A` as an active workspace.

### Case 4: Global Sync (Sync)

**Goal**: Verify `sync` command triggers Daemon to sync workspaces.

**Steps**:

1.  **Simulate Remote Change**:
    - Update submodule pointer in `remote-main`.
    - Push to `main`.
2.  **Execute Sync**:
    - Run `workspace sync --all`.
3.  **Verify**:
    - Daemon logs/status indicate syncing.
    - `base-workspace-A` pulls the new changes from `main`.

### Case 5: Preview Switching (Preview)

**Goal**: Verify `preview` command triggers Daemon to sync files to Base Workspace.

**Steps**:

1.  **Prepare Changes**:
    - Modify `backend/README.md` in `base-workspace-A`.
2.  **Execute Preview**:
    - Run `workspace preview --workspace A`.
3.  **Verify**:
    - **Base Workspace (Target)**:
      - `backend/README.md` content matches `A`.
      - Daemon starts a `Watcher` to sync future changes.
    - `workspace status` shows `Active Preview: A`.

### Case 6: Live Watch (Watch)

**Goal**: Verify real-time file syncing (Incremental).

**Steps**:

1.  **Modify File**:
    - Change `frontend/main.js` in `base-workspace-A`.
2.  **Verify**:
    - Change is automatically reflected in `base-workspace/frontend/main.js` (within seconds).
    - **Note**: Only the modified file should be synced (incremental update).

### Case 7: Switch Workspace (Switch)

**Goal**: Verify switching preview to another workspace interrupts previous one.

**Steps**:

1.  **Create Workspace B**:
    - `workspace create B`.
    - Make different changes in `B`.
2.  **Switch Preview**:
    - `workspace preview --workspace B`.
3.  **Verify**:
    - **Interruption**: Preview for `A` is stopped (watcher stopped).
    - **Cleanup**: Base Workspace is reset.
    - **Sync**: Base Workspace now reflects `B` content.
    - `A` changes are gone from Base Workspace.
    - `workspace status` shows `Active Preview: B`.

### Case 8: Delete Workspace (Delete)

**Goal**: Verify workspace deletion.

**Steps**:

1.  **Execute Delete**:
    - `workspace delete A`.
2.  **Verify**:
    - Directory `base-workspace-A` is removed.
    - Worktree is pruned.
    - `workspace status` no longer lists `A`.

### Case 9: Daemon Shutdown

**Goal**: Clean shutdown.

**Steps**:

1.  **Stop Daemon**:
    - Send SIGTERM/SIGINT to Daemon process.
2.  **Verify**:
    - Process exits.
    - `workspace status` reports "Daemon is not running".
