# E2E Test Documentation (Refactored)

此文档详细描述了基于 **Git Native (Workspace as Repo)** 架构的端到端 (E2E) 测试用例。

## 测试环境准备

1.  **工作目录**: `test-e2e-work-root`。
2.  **前置条件**:
    - 安装 `workspace-cli`。
    - Git 环境可用。

## 测试用例

### Case 1: 环境初始化 (Setup)

**目标**: 模拟真实的远程仓库环境，包含主仓库和子模块。

**步骤**:

1.  **创建 Remote Submodules**:
    - 创建 `remote-backend` 仓库，提交初始文件。
    - 创建 `remote-frontend` 仓库，提交初始文件。
2.  **创建 Remote Main Repo**:
    - 创建 `remote-main` 仓库。
    - 使用 `git submodule add` 添加 `remote-backend` 和 `remote-frontend`。
    - 提交并推送。
3.  **模拟 Base Workspace**:
    - `git clone --recursive remote-main base-workspace`。
    - 这是我们的 "Base Workspace" (也是 Preview Workspace)。

### Case 2: 创建 Workspace (Create)

**目标**: 验证基于 Base Workspace 创建新的 Worktree Workspace。

**步骤**:

1.  **执行命令**: `workspace-cli create feature-a --base $(pwd)/base-workspace`
2.  **验证**:
    - 存在目录 `base-workspace-feature-a`。
    - 该目录是 `base-workspace` 的 Git Worktree。
    - 当前分支为 `workspace-feature-a/stand`。
    - 子模块 `backend` 和 `frontend` 已被初始化且内容存在。

### Case 3: 全局同步 (Sync)

**目标**: 验证 `sync` 命令能够同步远程变更到所有 Workspace。

**步骤**:

1.  **模拟远程变更**:
    - 在 `remote-main` 中更新子模块指针 (例如 `backend` 有新 Commit)。
    - Push 到 `remote-main` 的 `main` 分支。
2.  **执行 Sync**:
    - 在 `base-workspace-feature-a` 中执行: `workspace-cli sync`。
3.  **验证**:
    - **Feature Workspace**: `stand` 分支已 Merge `main` 的变更，`backend` 子模块指向新 Commit。

### Case 4: Preview 初始化与同步

**目标**: 验证 Preview 的 Common Root 逻辑和文件同步。

**步骤**:

1.  **准备差异**:
    - 在 `base-workspace-feature-a` (Source) 中修改 `backend/README.md`。
    - **不提交** (Uncommitted Change)。
2.  **执行 Preview**:
    - `workspace-cli preview`。
3.  **验证**:

    - **Base Workspace (Target)**:

      - `backend` 子模块切换到了 `preview` 分支。
      - `backend/README.md` 内容已更新。
      - `git status` 显示 `backend` 是 clean 的 (因为文件是 Copy 过去的，且 Base 是基于 Common Root，如果 Source 未提交，Base 应该也是 Uncommitted? 不，Base 是 Copy 覆盖。如果 Base Reset 到 Common Root，Copy 后应该是 Modified 状态)。
      - _修正_: Preview 逻辑是 Reset 到 Common Root，然后 Copy 文件。所以 Base 中应该是 "Modified" 状态，且内容与 Source 一致。

      - _修正_: Preview 逻辑是 Reset 到 Common Root，然后 Copy 文件。所以 Base 中应该是 "Modified" 状态，且内容与 Source 一致。

### Case 5: Clean Preview (Clean)

**目标**: 验证 `clean-preview` 命令能够清理 Preview 环境。

**步骤**:

1.  **执行 Clean**:
    - `workspace-cli clean-preview`。
2.  **验证**:
    - **Base Workspace**:
      - `backend` 子模块切换回 `main` 分支。
      - `preview` 分支被删除。
      - `git status` 显示 clean (无 untracked files)。

### Case 6: 切换 Workspace (Switch)

**目标**: 验证 Preview 环境的清理和切换。

**步骤**:

1.  创建另一个 Workspace `feature-b`。
2.  在 `feature-b` 做不同的修改。
3.  执行 `workspace-cli preview --workspace feature-b`。
4.  **验证**:

    - Base Workspace 的内容变成了 `feature-b` 的内容。
    - 之前的 `feature-a` 内容被清除。

    - 之前的 `feature-a` 内容被清除。

### Case 7: 删除 Workspace (Delete)

**目标**: 验证清理。

**步骤**:

1.  `workspace-cli delete feature-a`。
2.  **验证**:
    - 目录 `base-workspace-feature-a` 不存在。

### Case 8: Preview Hooks

**目标**: 验证 `preview_hook` 配置的钩子命令是否正确执行。

**步骤**:

1.  **配置 Hook**:
    - 在 `workspace.json` 中添加 `preview_hook`:
      ```json
      {
        "preview_hook": {
          "before_clear": "touch hook_before.txt",
          "ready_preview": "touch hook_ready.txt"
        }
      }
      ```
2.  **执行 Preview**:
    - `workspace-cli preview`。
3.  **验证**:
    - **Base Workspace**:
      - 存在文件 `hook_before.txt`。
      - 存在文件 `hook_ready.txt`。
