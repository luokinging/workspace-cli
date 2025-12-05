# Comprehensive E2E Test Plan

This document outlines the end-to-end testing strategy for `workspace-cli`, focusing on real-world scenarios, concurrency handling, and system integrity.

## Test Environment Setup

The test runner will create a temporary directory structure simulating a real user environment:

```
/tmp/workspace-e2e-test-run/
├── base-repo/              (The main git repository)
│   ├── .git/
│   ├── workspace.json
│   ├── main.py             (Simulated app code)
│   └── .project-rules/     (Simulated rules)
├── feature-a/              (Git worktree for feature A)
├── feature-b/              (Git worktree for feature B)
└── logs/                   (Log directory for daily rotation)
```

## Scenarios

### 1. Initialization and Configuration

- **Action**: Initialize `workspace-cli` in `base-repo`.
- **Config**:
  - `base_path`: Absolute path to `base-repo`.
  - `log_path`: Absolute path to `logs/`.
  - `workspaces`: Empty initially.
- **Verification**:
  - `workspace.json` is created.
  - Daemon starts and logs to `logs/workspace-cli.log` (or rotated file).

### 2. Workspace Creation

- **Action**: `workspace create feature-a feature-b`
- **Verification**:
  - Directories `feature-a` and `feature-b` exist.
  - Both are valid git worktrees.
  - `workspace.json` is updated with both workspaces.
  - `workspace status` shows both as inactive.

### 3. Preview Concurrency (Switching)

- **Goal**: Verify that starting a preview in one workspace correctly terminates the previous one.
- **Step 3.1**: Start Preview A
  - **Action**: Run `workspace preview --workspace feature-a` (in background).
  - **Verification**:
    - Daemon status shows `active_preview: feature-a`.
    - `feature-a` is synced to `base-repo`.
    - `base-repo` is on branch `preview`.
    - "Before Clear" hooks executed.
    - "After Preview" hooks executed.
- **Step 3.2**: Start Preview B
  - **Action**: Run `workspace preview --workspace feature-b` (in background).
  - **Verification**:
    - Preview A process terminates (or stops streaming).
    - Daemon status shows `active_preview: feature-b`.
    - `base-repo` is re-synced with `feature-b` content.
    - "Before Clear" hooks executed again.
    - "After Preview" hooks executed again.

### 4. File Synchronization & Observation

- **Goal**: Verify that changes in the feature workspace are reflected in the preview (base) workspace.
- **Action**:
  - Modify `feature-b/main.py`.
- **Verification**:
  - Watcher detects change.
  - `base-repo/main.py` is updated automatically.
  - Logs show sync activity.

### 5. Log Rotation

- **Goal**: Verify logs are stored and rotated.
- **Action**: Check `logs/` directory.
- **Verification**:
  - `workspace-cli.log` exists.
  - Content includes debug logs (if enabled).

### 6. Cleanup

- **Action**: `workspace delete feature-a feature-b`
- **Verification**:
  - Worktrees removed.
  - Config entries removed.
