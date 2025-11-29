# Workspace CLI

Workspace CLI is a command-line tool for managing multiple Workspaces, Git Repositories (Repo), and Live Preview. It is designed to provide an efficient, isolated, and easily synchronized development environment for AI-assisted development.

## 📖 Introduction

The core goal of this project is to solve the problem of environment isolation and synchronization during parallel multi-task development. By assigning different development tasks to independent Workspaces, each Workspace has its own independent Git Worktree, ensuring no interference. At the same time, it provides a unified Preview Workspace for real-time preview and review, ensuring that changes during development can be accurately and quickly synchronized.

### Core Features

- **Workspace Logical Grouping**: Workspaces exist only as folders and are not directly managed by Git, facilitating flexible organization.
- **Independent Repo Management**: Utilizing `git worktree` technology, Repos within each Workspace have independent branches (Feature/Stand/Preview), supporting parallel development.
- **Preview Workspace**: A single preview environment that supports accurate synchronization of code from any Workspace (syncing only Tracked files), ensuring a clean preview environment.
- **Live Preview**: Automatically monitors file changes and synchronizes them to the Preview Workspace in real-time.
- **Rules Repo Synchronization**: Supports automatic cross-workspace synchronization (Commit/Push/Merge) of special rules repositories.

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

### 1. Create Workspace

Use the `create` command to create a new development Workspace based on a base Workspace.

**Auto Configuration**: If a `workspace.json` configuration file does not exist in the current directory, the `create` command will automatically create one based on the provided `--base` and `--repo` parameters.

```bash
# Syntax
workspace create --name <new_name> [--base <base_path> --repo <repo_list>]

# Example 1: Config exists, create directly
workspace create --name feature-a

# Example 2: First use, auto-generate config and create
workspace create --name feature-a --base ./work_root/main --repo frontend --repo backend
```

### 2. Complete Scenario Example

Assuming your directory structure is as follows:

```text
/Users/luoking/Desktop/Project/Work
└── workspace
    ├── luoking-creatify-coding  (Rules Repo)
    ├── main-web-ui
    └── webserver
```

#### Scenario 1: Create Multiple Workspaces

**Command**:

```bash
cd /Users/luoking/Desktop/Project/Work

# Create the first workspace (lulu) and initialize config
workspace create lulu \
  --base ./workspace \
  --repo main-web-ui \
  --repo webserver \
  --repo luoking-creatify-coding

# Create subsequent workspaces
workspace create kiki
workspace create momo
```

**Result**:

- Three workspaces created: `workspace-lulu`, `workspace-kiki`, `workspace-momo`.
- Repos inside Workspaces use `git worktree`, default branch is `workspace-{name}/stand`.
- Repos under the base workspace `./workspace` automatically switch to `workspace-{name}/preview` branch, ready to serve as the Preview environment.
- `workspace.json` configuration file is automatically generated.

#### Scenario 2: Configure Rules Repo

**Action**:

Open the generated `workspace.json` and modify the `rules_repo` field to your rules repository name:

```json
"rules_repo": "luoking-creatify-coding"
```

#### Scenario 3: Execute Live Preview in Workspace Root

**Command**:

```bash
workspace-cli preview
```

**Result**:

- **Auto-detection**: Automatically identifies the current workspace (e.g., `workspace-momo`).
- **Precise Sync**:
  - Automatically adds tracked files.
  - Calculates diff with main branch.
  - Cleans preview workspace.
  - Switches/Resets preview branch `preview` (single branch to prevent redundancy).
  - Applies diff, syncing files.
- **Live Preview**: Starts live preview, monitoring file changes.
  - Outputs change info: `[CREATED]`, `[UPDATED]`, `[DELETED]` (with color highlighting).
- **Concurrency Control**: Prevents running multiple preview instances simultaneously.

### Scenario 4: Execute Preview in Workspace Subdirectory

**Command** (e.g., in `workspace-momo/frontend/src`):

```bash
workspace-cli preview
```

**Result**:

- Automatically looks up the workspace root directory → `workspace-momo`.
- Executes preview sync logic.

### Scenario 5: One-time Sync (Non-Live Mode)

**Command**:

```bash
workspace-cli preview --once
```

**Result**:

- Exits immediately after one sync, does not start file monitoring.
- Suitable for CI/CD or quick checks.

### Scenario 6: Debugging and Logging

**Command**:

```bash
workspace-cli preview --debug --log-file workspace.log
```

**Result**:

- Enables debug mode, printing detailed information.
- Outputs logs to `workspace.log`.

#### Scenario 7: Switch Live Preview to Another Workspace

**Command**:

```bash
# Assuming currently previewing lulu
cd ./workspace-kiki
workspace preview
```

**Result**:

- The previous Live Preview process (if running) will stop (requires manual control or script, CLI currently supports overwrite).
- Cleans Preview Workspace.
- Deletes the old `workspace-lulu/preview` branch.
- Creates a new `workspace-kiki/preview` branch.
- Syncs `workspace-kiki` content and starts monitoring.

#### Scenario 8: Rules Repo Sync

**Command**:

```bash
workspace syncrule
```

**Result**:

- Rules Repo switches to `main` branch.
- `commit` + `push` current workspace rules changes.
- Automatically executes `pull origin main` (or merge) for Rules Repos in other workspaces.
- Automatically executes `pull origin main` (or merge) for Rules Repos in other workspaces.
- **Expand Folder**: If `workspace_expand_folder` is configured, contents of that folder in Rules Repo will be expanded (copied) to the root of all workspaces, ensuring consistent configuration (e.g., for AI agents).
- Returns to the current workspace's Feature branch.

#### Scenario 9: View Workspace Status

**Command**:

```bash
workspace status
```

**Result**:

- Displays Base Workspace path.
- Lists all created Workspaces and their paths.

#### Scenario 10: Delete Workspace

**Command**:

```bash
workspace delete --name kiki
```

**Result**:

- Deletes `workspace-kiki` folder.
- Automatically cleans up related git worktrees.
- Does not affect Base Workspace or other Workspaces.

## 📚 Detailed Documentation

### Core Concepts

- **Workspace**: Workspace folder, typically named `{base}-{name}`.
- **Preview Workspace**: Base Workspace (usually `{base}`), used for running and previewing code.
- **Repo**: Git repository, sharing object storage via `git worktree` across Workspaces while keeping working directories independent.
- **Stand Branch**: Standby branch, used to maintain a clean state in new Workspaces.
- **Preview Branch**: Temporary branch, exists only in Preview Workspace, used to apply changes from other Workspaces.

### System Design and Branch Strategy

This project uses a unique branch model to isolate development environments from preview environments.

#### 1. Branch Model

| Branch Type        | Naming Rule                | Role                                                                                                                                                            | Lifecycle                                                                             |
| :----------------- | :------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------ |
| **Feature Branch** | `workspace/{feature_name}` | **Actual Development Branch**. Manually created by user in Workspace for daily development.                                                                     | Long-term, merged/deleted after feature completion.                                   |
| **Stand Branch**   | `workspace-{name}/stand`   | **Standby/Placeholder Branch**. Automatically created by `create` command. Used when Workspace is just created or not on a Feature branch to prevent conflicts. | Long-term during Workspace existence.                                                 |
| **Preview Branch** | `workspace-{name}/preview` | **Preview Dedicated Branch**. Automatically created by `preview` command. Exists only in Base Workspace (Preview Workspace).                                    | **Temporary**. Deleted and recreated every time `preview` runs or Workspace switches. |

#### 2. Workflow Design

- **Create Phase**:

  - When executing `create`, CLI creates a `stand` branch for each Repo in the target Workspace.
  - **Design Intent**: New Workspace should be in a clean "standby" state, waiting for user to Checkout specific Feature branch for development. It should not be directly in Preview state.

- **Preview Phase**:
  - When executing `preview`, CLI syncs code from current Workspace (under development) to Base Workspace (preview environment).
  - At this time, Repo in Base Workspace is switched to `preview` branch.
  - **Design Intent**: Base Workspace acts as a "Player", responsible for running and displaying code; while development Workspace acts as an "Editor", responsible for modifying code.

### Configuration File

`workspace.json` is the core configuration file of the project, usually located in the Work Root directory.

```json
{
  "base_path": "/absolute/path/to/base/workspace",
  "repos": [
    {
      "name": "repo-name",
      "path": "relative/path/to/repo",
      "url": "git@github.com:user/repo.git"
    }
  ],
  "rules_repo": "rules-repo-name",
  "workspace_expand_folder": "expand"
}
```

| Field                     | Type   | Description                                                                                                                 |
| :------------------------ | :----- | :-------------------------------------------------------------------------------------------------------------------------- |
| `base_path`               | String | **Absolute path of Base Workspace**. New Workspaces will be created based on this, and Preview also runs in this directory. |
| `repos`                   | List   | **List of managed repositories**. Defines which repositories need to be managed by Workspace.                               |
| `repos[].name`            | String | Repository name, used in CLI commands (e.g., `create --repo name`).                                                         |
| `repos[].path`            | String | Path of repository relative to Workspace root.                                                                              |
| `repos[].url`             | String | (Optional) Remote Git URL of repository. **Note: Currently unused, reserved for future auto-clone support.**                |
| `rules_repo`              | String | (Optional) Specifies which repository is the rules repository, used for `syncrule` command.                                 |
| `workspace_expand_folder` | String | (Optional) Path to a folder in Rules Repo. Its contents will be expanded to the root of all workspaces during `syncrule`.   |

### Command Reference

| Command    | Description           | Example                                  |
| :--------- | :-------------------- | :--------------------------------------- |
| `create`   | Create new Workspace  | `workspace create --name dev --repo web` |
| `delete`   | Delete Workspace      | `workspace delete --name dev`            |
| `status`   | View current status   | `workspace status`                       |
| `preview`  | Start preview sync    | `workspace preview`                      |
| `syncrule` | Sync rules repository | `workspace syncrule`                     |
