# Workspace CLI Design Document

## 1. Architecture Overview

The system will transition from a set of independent CLI scripts to a **Client-Server (C/S) Architecture**.

### 1.1 Components

- **Daemon Service (Server)**:
  - A long-running process managed by `FastAPI`.
  - Acts as the **Single Source of Truth** for workspace state.
  - Handles all heavy lifting: Git operations, File Watching, Subprocess management.
  - Uses **In-Memory Locks** (`asyncio.Lock`) to ensure concurrency safety. No file locks.
- **CLI (Client)**:
  - A thin wrapper using `Typer`.
  - Responsible for parsing arguments and sending HTTP requests to the Daemon.
  - Displays responses and streams logs from the Daemon.

### 1.2 Technology Stack

- **Language**: Python 3.9+
- **Server Framework**: FastAPI (Async support, easy API definition)
- **CLI Framework**: Typer
- **File Watching**: Watchdog
- **Git Operations**: Subprocess (wrapped in a `GitProvider` abstraction)

---

## 2. Core Concepts & Abstractions

### 2.1 WorkspaceManager

A singleton class within the Daemon that manages the lifecycle of workspaces.

- **State**: Tracks `current_workspace`, `is_syncing`, `active_processes`.
- **Methods**: `switch_workspace()`, `sync_workspace()`, `get_status()`.

### 2.2 GitProvider (Interface)

To ensure testability, all Git operations are abstracted behind a Protocol.

- **Real Implementation**: `ShellGitProvider` (calls `git` binary).
- **Mock Implementation**: `MockGitProvider` (for Unit/E2E testing).
- **Key Operations**: `checkout`, `fetch`, `reset`, `clean`, `get_common_base`.

### 2.3 Preview Flow (Optimized)

The new preview flow eliminates `git pull` to ensure speed and stability.

1.  **Stop**: Terminate running preview processes.
2.  **Clean**: Reset Preview Workspace to a clean state.
3.  **Base**: Find the common ancestor commit between `Target Feature` and `Main`.
4.  **Checkout**: Switch Preview Workspace to this base commit (Local operation).
5.  **Sync**: Copy file differences from `Target Feature` to `Preview Workspace`.
6.  **Watch**: Start file watcher and `npm run dev` (or configured command).

---

## 3. Command Design

### 3.1 `workspace daemon`

Starts the background service.

- `--port`: Specify port (default: 8000).
- `--foreground`: Run in foreground for debugging.

### 3.2 `workspace create [NAMES]...`

Creates new feature workspaces.

- Sends request to Daemon to create worktrees and update config.
- `--base`: Path to base workspace (for first run).

### 3.3 `workspace preview [NAME]`

Switches the preview environment.

- **No Git Pull**: Purely local operation.
- `--once`: Run sync once and exit (for CI/Testing).
- `--rebuild`: Force full clean and rebuild.

### 3.4 `workspace sync`

Explicitly updates code from remote.

- **Feature Workspace**: `git pull --rebase origin main`.
- **Base Workspace**: `git pull origin main`.
- `--all`: Sync all workspaces.
- `--push`: Push changes after sync.

### 3.5 `workspace delete [NAME]`

Removes a workspace and its worktree.

### 3.6 `workspace status`

Shows Daemon status, active preview, and managed workspaces.

---

## 4. Testing Strategy

### 4.1 Philosophy

- **Testable by Design**: Use Dependency Injection (`GitProvider`) to decouple logic from external systems.
- **Fast Feedback**: Unit tests should run in milliseconds.
- **Reliable E2E**: E2E tests run against a local, isolated Daemon instance with local temporary git repos.

### 4.2 Workflow

1.  **Unit Tests (`tests/unit`)**:
    - Verify logic using `MockGitProvider`.
    - Cover `WorkspaceManager` state transitions.
2.  **E2E Tests (`tests/e2e`)**:
    - **Setup**: Create a temp directory, init bare git repo, start Daemon.
    - **Execution**: Use `httpx` or the CLI to send requests to the Daemon.
    - **Verification**: Check file existence and content in the temp directory.
    - **Git Push**: Verified by checking the state of the local bare repo.

### 4.3 Development Process

1.  Modify Code.
2.  Run `pytest tests/unit`.
3.  Run `pytest tests/e2e`.
4.  Commit.

---

## 5. Migration Plan (Removing Legacy)

- Remove `core/sync.py` (Split into `Server/SyncService` and `Server/Watcher`).
- Remove `core/runner.py` (Replaced by `Server/ProcessManager`).
- Remove PID file logic.
- Remove Socket IPC logic (Replaced by HTTP).
