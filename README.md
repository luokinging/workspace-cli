# Workspace CLI

Workspace CLI is a command-line tool for managing multiple Workspaces using a **Git-native** architecture. It treats the Workspace itself as a Git repository and manages child repositories as **Git Submodules**, providing an efficient, isolated, and easily synchronized development environment for AI-assisted development.

## 📖 Introduction

The core goal of this project is to solve the problem of environment isolation and synchronization during parallel multi-task development. By assigning different development tasks to independent Workspaces (Git Worktrees), each Workspace has its own independent environment. At the same time, it provides a unified Preview Workspace for real-time preview and review, ensuring that changes during development can be accurately and quickly synchronized.

### Core Features

- **Workspace as Repo**: The top-level Workspace is a Git repository. Child repositories are managed via `.gitmodules`.
- **Git Worktree Isolation**: Each Workspace is a Git Worktree of the Base Workspace, ensuring efficient storage usage and fast creation.
- **Unified Sync**: The `sync` command updates the current Workspace from remote. Use `--all` to update all Workspaces.
- **Preview Workspace**: A single preview environment that supports accurate synchronization of code from any Workspace (syncing only Tracked files), ensuring a clean preview environment.
- **Live Preview**: Automatically monitors file changes and synchronizes them to the Preview Workspace in real-time.

## 🛠️ Installation

Ensure that Python 3.8+ and Git are installed in your environment.

```bash
pip install dev-ws
```

### Local Development Installation

If you want to install from source for development:

```bash
git clone https://github.com/your-repo/workspace-cli.git
cd workspace-cli
pip install -e .
```

## 🚀 Quick Start

### 1. Setup Base Workspace

First, clone your main repository (which contains submodules) recursively. This will serve as your **Base Workspace**.

```bash
git clone --recursive https://github.com/your-org/main-repo.git base-workspace
cd base-workspace
```

### 2. Create Workspace

Use the `create` command to create a new development Workspace (Worktree) based on the Base Workspace.

```bash
# Syntax
workspace create <new_name>... [--base <base_path>]

# Example: Create a feature workspace
# Run this from within the Base Workspace or specify --base
workspace create feature-a

# Example: Create multiple workspaces
workspace create feature-a feature-b feature-c
```

**Result**:

- A new directory `../base-workspace-feature-a` is created.
- It is a Git Worktree of `base-workspace`.
- Submodules are initialized and updated.
- A `workspace.json` config is automatically generated if not present.

### 3. Sync Workspaces

Use the `sync` command to update workspaces with the latest changes from the remote repository.

```bash
# Sync current workspace (default)
workspace sync

# Sync all workspaces (Base + Siblings)
workspace sync --all
```

**Result**:

- **Current Workspace**: Pulls `origin/main` (rebase).
- **With `--all`**:
  - **Base Workspace**: Pulls `origin/main`.
  - **Sibling Workspaces**: Merges `origin/main` into their current branch and updates submodules.

### 4. Live Preview

Use the `preview` command to sync changes from your current development workspace to the Base Workspace (Preview Environment) in real-time.

```bash
# Run from your feature workspace
workspace preview
```

**Result**:

- **Base Workspace**: Switches submodules to a `preview` branch (reset to common root with feature workspace).
- **Sync**: Copies tracked files from Feature Workspace to Base Workspace.
- **Watch**: Monitors file changes and syncs them instantly.

## 📚 Command Reference

| Command   | Description                                      | Example                      |
| :-------- | :----------------------------------------------- | :--------------------------- |
| `create`  | Create a new Workspace (Git Worktree).           | `workspace create feature-a` |
| `sync`    | Sync workspace from remote. Use `--all` for all. | `workspace sync`             |
| `preview` | Start live preview sync to Base Workspace.       | `workspace preview`          |
| `delete`  | Delete a Workspace and its worktree.             | `workspace delete feature-a` |
| `status`  | View current status and list of workspaces.      | `workspace status`           |

## ⚙️ Configuration

`workspace.json` is the configuration file, usually located in the Base Workspace.

```json
{
  "base_path": "/absolute/path/to/base/workspace",
  "workspaces": {
    "feature-a": {
      "path": "../base-workspace-feature-a"
    }
  }
}
```

| Field        | Type   | Description                                                                        |
| :----------- | :----- | :--------------------------------------------------------------------------------- |
| `base_path`  | String | **Absolute path of Base Workspace**. New Workspaces will be created based on this. |
| `workspaces` | Map    | Map of created workspaces (Name -> Path). Managed automatically by CLI.            |

## 🏗️ Architecture

### Branch Strategy

- **Base Workspace**: Usually on `main` branch. Acts as the source of truth and Preview Target.
- **Feature Workspace**: Created as a Worktree.
  - **Workspace Repo**: On `workspace-{name}/stand` branch.
  - **Submodules**: On `main` or specific commits.
- **Preview**:
  - **Target Submodules**: Switched to `preview` branch (reset to common ancestor).

### Sync Logic

1.  **Global Sync (`sync`)**:

    - **Default**: Updates current Workspace (Pull --rebase).
    - **With `--all`**:
      - Updates Base Workspace from Remote.
      - Propagates updates to all Feature Workspaces (Merge + Submodule Update).

2.  **Preview Sync (`preview`)**:
    - Identifies Common Root between Feature and Base submodules.
    - Resets Base submodules to Common Root (on `preview` branch).
    - Copies modified files from Feature to Base.
    - **Note**: If you switch branches in the Feature Workspace during preview, files _will_ be synced, but the Git history (HEAD) in the Preview Workspace will remain at the initial Common Root. For best results, restart `preview` after switching branches.

```

```
