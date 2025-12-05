# Workspace CLI

Workspace CLI is a powerful command-line tool designed to streamline development in complex, multi-repository environments. It leverages a **Client-Server Architecture** and **Git Worktrees** to provide isolated development workspaces, efficient synchronization, and instant preview switching.

## 📖 Introduction

In modern development, managing multiple feature branches and keeping them in sync with a shared preview environment can be challenging. Workspace CLI solves this by:

- **Isolating Environments**: Each feature gets its own Git Worktree, ensuring clean separation of dependencies and build artifacts.
- **Unified Preview**: A single "Base Workspace" acts as the preview target. You can instantly switch the preview to any feature workspace without re-cloning or slow checkouts.
- **Real-time Sync**: A background Daemon watches for file changes and syncs them to the preview environment instantly.
- **Centralized Management**: A long-running Daemon manages the state of all workspaces, ensuring consistency and concurrency safety.

## 🤖 Designed for AI & Parallel Development

Workspace CLI is specifically architected to support **AI Agents** and **Parallel Development Workflows**:

- **Multi-Repo Context**: By managing submodules (e.g., `frontend`, `backend`) within a single workspace, AI agents can view and modify the entire stack in one cohesive context, avoiding context switching overhead.
- **Agent Isolation**: Multiple AI agents can work on different tasks (e.g., "Feature A", "Bugfix B") simultaneously in separate workspaces without interfering with each other or the stable Base Workspace.
- **Safe Verification**: Agents can use the `preview` command to verify their changes in the Base Workspace (which mimics production) before submitting code, ensuring high-quality contributions.
- **Concurrency Safety**: The Daemon ensures that even if multiple agents trigger commands simultaneously, the system remains consistent and race-free.

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Git installed and available in PATH

### Installation

```bash
# Install from source
git clone https://github.com/your-repo/workspace-cli.git
cd workspace-cli
pip install -e .
```

### 1. Start the Daemon

The Daemon is the heart of Workspace CLI. It must be running for most commands to work.

```bash
# Start in background (default port 8000)
workspace daemon

# Or run in foreground for debugging
workspace daemon --foreground

# Enable detailed debug logs (file events, process lifecycle)
workspace daemon --debug
```

### 2. Initialize Base Workspace

Clone your main repository (recursively if it has submodules). This will be your **Base Workspace**.

```bash
git clone --recursive https://github.com/your-org/main-repo.git base-workspace
cd base-workspace
```

### 3. Create a Feature Workspace

Create a new isolated workspace for your feature.

```bash
# Create a workspace named 'A'
workspace create A
```

This creates a sibling directory `../base-workspace-A` which is a Git Worktree of your base workspace.

### 4. Switch Preview

Instantly switch your Base Workspace to reflect the code in your feature workspace.

```bash
workspace preview --workspace A
# OR (if inside the workspace directory)
workspace preview
```

Your Base Workspace now contains the code from `A`, and the Daemon is watching for changes.

## ⚙️ Configuration

The `workspace.json` file configures the behavior of your workspaces. It is typically located in the root of your Base Workspace.

```json
{
  "base_path": "/absolute/path/to/base-workspace",
  "workspaces": {
    "A": {
      "path": "/absolute/path/to/base-workspace-A"
    }
  },
  "preview": ["cd frontend && npm run dev"],
  "preview_hook": {
    "before_clear": ["rm -rf dist"],
    "after_preview": ["echo 'Preview Ready'"]
  }
}
```

### Configuration Fields

| Field                        | Type      | Description                                                                            |
| :--------------------------- | :-------- | :------------------------------------------------------------------------------------- |
| `base_path`                  | String    | **Required**. Absolute path to the Base Workspace.                                     |
| `workspaces`                 | Map       | Managed automatically. Maps workspace names to their paths.                            |
| `preview`                    | List[Str] | Commands to run when starting the preview server (e.g., `cd frontend && npm run dev`). |
| `preview_hook`               | Object    | Hooks for preview lifecycle.                                                           |
| `preview_hook.before_clear`  | List[Str] | Commands to run before clearing the preview environment.                               |
| `preview_hook.after_preview` | List[Str] | Commands to run after preview sync is complete.                                        |

## 🔄 End-to-End Workflow Guide

This guide walks you through setting up a new multi-repo project from scratch and performing daily development.

### Phase 1: Project Initialization (One-time Setup)

If you are starting a brand new project with multiple repositories (e.g., `main`, `frontend`, `backend`).

1.  **Create Repositories**:
    Create your repositories on GitHub/GitLab.

    - `my-project-main` (The container repo)
    - `my-project-frontend`
    - `my-project-backend`

2.  **Setup Main Repository**:
    Clone the main repository and add your submodules.

    ```bash
    git clone https://github.com/org/my-project-main.git
    cd my-project-main

    # Add submodules
    git submodule add https://github.com/org/my-project-frontend.git frontend
    git submodule add https://github.com/org/my-project-backend.git backend

    # Commit setup
    git commit -m "Setup project structure"
    git push
    ```

### Phase 2: Developer Setup (Base Workspace)

Every developer on the team performs this step to set up their environment.

1.  **Clone Base Workspace**:
    Clone the main repository recursively. This directory will serve as your **Base Workspace** and **Preview Target**.

    ```bash
    # Clone recursively to get all submodules
    git clone --recursive https://github.com/org/my-project-main.git base-workspace
    cd base-workspace
    ```

2.  **Initialize Configuration**:
    Create a `workspace.json` file in the root of `base-workspace`.

    ```bash
    # Example workspace.json
    echo '{
      "base_path": "'$(pwd)'",
      "workspaces": {},
      "preview": ["cd frontend && npm run dev"],
      "preview_hook": {
        "before_clear": ["rm -rf dist"],
        "after_preview": ["echo Preview Ready"]
      }
    }' > workspace.json
    ```

3.  **Start Daemon**:
    Start the Workspace Daemon. It must be running for commands to work.

    ```bash
    workspace daemon
    ```

### Phase 3: Daily Development Cycle

Now you are ready to develop features.

1.  **Create Feature Workspace**:
    Instead of working directly in `base-workspace`, create an isolated workspace.

    ```bash
    workspace create A
    ```

    _This creates `../base-workspace-A` (a sibling directory)._

2.  **Start Preview**:
    Switch the Base Workspace to preview your feature.

    ```bash
    workspace preview --workspace A
    # OR simply: workspace preview
    ```

    _The Daemon will now sync changes from `A` to `base-workspace` in real-time._

3.  **Develop**:
    Open `../base-workspace-A` in your IDE.

    - Modify `frontend/src/Login.js`.
    - Modify `backend/api/auth.py`.
    - **Result**: Changes are instantly synced to `base-workspace`. Your dev server running in `base-workspace` hot-reloads automatically.

4.  **Sync Updates**:
    If teammates push code to `main`, keep your workspace updated.

    ```bash
    workspace sync --all
    ```

5.  **Finish & Cleanup**:
    Once your PR is merged, delete the feature workspace.

    ```bash
    workspace delete A
    ```

## 🛠️ Command Reference

| Command          | Description                               | Example                           |
| :--------------- | :---------------------------------------- | :-------------------------------- |
| `daemon`         | Start the background service.             | `workspace daemon`                |
| `status`         | Show daemon status and active workspaces. | `workspace status`                |
| `create <names>` | Create new workspaces.                    | `workspace create A`              |
| `preview`        | Switch preview to a specific workspace.   | `workspace preview --workspace A` |
| `sync`           | Sync code from remote.                    | `workspace sync --all`            |
| `delete <name>`  | Delete a workspace.                       | `workspace delete A`              |

## 🧠 How It Works (Principles)

### Client-Server Architecture

- **Daemon (Server)**: A FastAPI application that manages state, holds locks for concurrency, and handles heavy Git operations. It maintains a singleton `WorkspaceManager`.
- **CLI (Client)**: A lightweight Typer app that sends HTTP requests to the Daemon.

### Git Worktrees

Instead of cloning the repository multiple times (which is slow and wastes disk space), Workspace CLI uses **Git Worktrees**.

- **Base Workspace**: The main repository clone.
- **Feature Workspaces**: Linked worktrees that share the `.git` directory with the Base Workspace but have their own working trees.

### Smart Syncing

- **Global Sync**: `workspace sync` handles complex git operations (fetch, rebase, submodule update) across all workspaces.
- **Live Preview Mechanism**:
  1.  **Common Base Discovery**: When you switch preview, the Daemon calculates the common ancestor commit between your Feature Workspace and the Base Workspace (using `git merge-base`).
  2.  **Clean Reset**: The Base Workspace is reset to this common ancestor state. This ensures a clean slate without conflicting history.
  3.  **File Synchronization**: The Daemon then copies **all files** from the Feature Workspace to the Base Workspace (excluding `.git`). This effectively applies your current work-in-progress on top of the stable base, mimicking a "squashed" view of your changes.
  4.  **Real-time Watch**: A file watcher (using `watchdog`) then monitors the Feature Workspace and instantly replicates any subsequent file changes to the Base Workspace.
