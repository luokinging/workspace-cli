# Workspace CLI

Workspace CLI is a command-line tool for managing multiple Workspaces using a **Git-native** architecture. It treats the Workspace itself as a Git repository and manages child repositories as **Git Submodules**, providing an efficient, isolated, and easily synchronized development environment for AI-assisted development.

## 📖 Introduction

The core goal of this project is to solve the problem of environment isolation and synchronization during parallel multi-task development. By assigning different development tasks to independent Workspaces (Git Worktrees), each Workspace has its own independent environment. At the same time, it provides a unified Preview Workspace for real-time preview and review, ensuring that changes during development can be accurately and quickly synchronized.

### Core Features

- **Workspace as Repo**: The top-level Workspace is a Git repository. Child repositories are managed via `.gitmodules`.
- **Git Worktree Isolation**: Each Workspace is a Git Worktree of the Base Workspace, ensuring efficient storage usage and fast creation.
- **Unified Sync**: The `sync` command updates the Base Workspace from remote and propagates changes (including submodule pointers) to all sibling Workspaces.
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
workspace create <new_name> [--base <base_path>]

# Example: Create a feature workspace
# Run this from within the Base Workspace or specify --base
workspace create feature-a
```

**Result**:

- A new directory `../base-workspace-feature-a` is created.
- It is a Git Worktree of `base-workspace`.
- Submodules are initialized and updated.
- A `workspace.json` config is automatically generated if not present.

### 3. Sync Workspaces

Use the `sync` command to update all workspaces with the latest changes from the remote repository.

```bash
# Run from any workspace
workspace sync
```

**Result**:

- **Base Workspace**: Pulls `origin/main`.
- **Sibling Workspaces**: Merges `origin/main` into their current branch and updates submodules.
- **Expansion**: If `workspace_expand_folder` is configured, contents from that folder in the Base Workspace are expanded to all workspaces.

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

| Command   | Description                                                  | Example                      |
| :-------- | :----------------------------------------------------------- | :--------------------------- |
| `create`  | Create a new Workspace (Git Worktree).                       | `workspace create feature-a` |
| `sync`    | Sync all workspaces from remote and expand shared resources. | `workspace sync`             |
| `preview` | Start live preview sync to Base Workspace.                   | `workspace preview`          |
| `delete`  | Delete a Workspace and its worktree.                         | `workspace delete feature-a` |
| `status`  | View current status and list of workspaces.                  | `workspace status`           |

## ⚙️ Configuration

`workspace.json` is the configuration file, usually located in the Base Workspace.

```json
{
  "base_path": "/absolute/path/to/base/workspace",
  "repos": [],
  "workspace_expand_folder": "expand"
}
```

| Field                     | Type   | Description                                                                                                            |
| :------------------------ | :----- | :--------------------------------------------------------------------------------------------------------------------- |
| `base_path`               | String | **Absolute path of Base Workspace**. New Workspaces will be created based on this.                                     |
| `repos`                   | List   | (Optional) List of managed repositories. Mostly auto-discovered from submodules now.                                   |
| `workspace_expand_folder` | String | (Optional) Path to a folder in Base Workspace. Its contents will be expanded (copied) to all workspaces during `sync`. |

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

    - Updates Base Workspace from Remote.
    - Propagates updates to all Feature Workspaces (Merge + Submodule Update).
    - Expands shared resources (e.g., rules, configs) from `workspace_expand_folder`.

2.  **Preview Sync (`preview`)**:
    - Identifies Common Root between Feature and Base submodules.
    - Resets Base submodules to Common Root (on `preview` branch).
    - Copies modified files from Feature to Base.
