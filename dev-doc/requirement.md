# Workspace CLI 需求文档 (Refactored)

## 1. 系统目标

建立一个基于 **Git Native (Workspace as Repo)** 的多工作区开发环境管理系统。

### 核心目标

- **Workspace 即仓库**：Workspace 本身是一个 Git 仓库，内部通过 Submodule 管理子 Repo。
- **Git Native 管理**：充分利用 Git 的 Worktree 和 Submodule 机制，减少自定义逻辑。
- **Preview Workspace**：用于本地运行和 Review，作为 Base Workspace 存在。
  - **精确同步**：通过文件拷贝 (`shutil`) 将工作 Workspace 的变更（含未提交变更）同步到 Preview Workspace。
  - **Common Root**：基于 Git 历史寻找共同祖先，确保 Preview 环境的纯净和准确。
- **Sync 命令**：统一的同步机制，保持所有 Workspace 的基准 (Main) 与远程同步。

## 2. 核心概念与命名规则

### 分支规则

| 名称             | 说明                                                     | 分支规则                 |
| :--------------- | :------------------------------------------------------- | :----------------------- |
| **Main 分支**    | Workspace Repo 的主分支，包含 `.gitmodules` 和子模块指针 | `main`                   |
| **Stand 分支**   | 工作 Workspace 的专属分支，用于日常开发和待机            | `workspace-{name}/stand` |
| **Preview 分支** | 子模块内的临时分支，用于 Preview                         | `preview` (每次重建)     |

### 概念说明

- **Base Workspace**: 也就是 Preview Workspace，是 Git Repo 的根目录。
- **Work Workspace**: 基于 Base Workspace 创建的 Git Worktree，与 Base 共享 `.git` 目录，但有独立的工作区。
- **Submodule**: 具体的业务代码仓库，作为 Workspace Repo 的子模块存在。

## 3. Workspace / Repo 结构

```text
PROJECT_ROOT/
  ├── main-workspace/                  # Base Workspace (Preview Workspace)
  │    ├── .git/
  │    ├── .gitmodules
  │    ├── backend/ (Submodule @ commitA)
  │    └── frontend/ (Submodule @ commitB)
  │
  ├── main-workspace-featureA/         # Work Workspace (Git Worktree)
  │    ├── .git (file -> main-workspace/.git/worktrees/...)
  │    ├── backend/ (Submodule @ commitA or modified)
  │    └── frontend/ (Submodule @ commitB or modified)
```

## 4. 功能需求

### 4.1. 创建 Workspace (`create`)

**命令**: `workspace-cli create <name> --base <base_path>`

**逻辑**:

1.  **验证**: 检查 `base_path` 是否为有效的 Git 仓库。
2.  **创建 Worktree**: 在 `base_path` 执行 `git worktree add`，创建新的目录 `base-name-{name}`。
    - 新分支命名: `workspace-{name}/stand`。
3.  **初始化子模块**: 在新 Workspace 中执行 `git submodule update --init --recursive`。

### 4.2. Preview 同步 (`preview`)

**命令**: `workspace-cli preview [--workspace <name>]`

**逻辑**:

1.  **准备 Target (Preview Workspace)**:
    - 更新所有子模块到远程 `main` 最新状态 (`git fetch` & `git merge origin/main`)。
2.  **计算 Common Root**:
    - 对比 Source (工作 Workspace) 和 Target (Preview Workspace) 的子模块 Commit。
    - 使用 `git merge-base` 找到共同祖先。
3.  **准备 Preview 分支**:
    - 在 Target 子模块中，基于 **Common Root** 创建/重置 `preview` 分支。
4.  **文件同步**:
    - 使用文件拷贝 (Copy) 将 Source 的文件覆盖到 Target。
    - **目的**: 同步所有变更（包括未提交的），且不产生额外的 Commit。
5.  **Live Watch**:
    - 监听 Source 文件变化，实时重复同步步骤。

### 4.3. 全局同步 (`sync`)

**命令**: `workspace-cli sync`

**逻辑**:

1.  **更新 Base**: 在 Base Workspace 拉取远程 `main` (`git pull origin main`)。
2.  **更新所有 Workspaces**:
    - 遍历所有本地 Workspace (Worktrees)。
    - **Merge**: 将 `main` 合并到当前 Workspace 的 `stand` 分支。
    - **Update Submodules**: 执行 `git submodule update --init --recursive`，确保子模块指针更新。

### 4.4. 删除 Workspace (`delete`)

**命令**: `workspace-cli delete <name>`

**逻辑**:

1.  **删除 Worktree**: 使用 `git worktree remove`。
2.  **清理目录**: 确保物理目录被删除。

## 5. 迁移指南 (Breaking Changes)

由于架构从 "文件夹管理" 变为 "Git 仓库管理"，旧的 Workspace 结构不再兼容。
用户需要：

1.  创建一个新的 Git 仓库作为 Base Workspace。
2.  使用 `git submodule add` 添加原有的业务 Repo。
3.  使用新的 CLI 工具重新创建工作 Workspace。
