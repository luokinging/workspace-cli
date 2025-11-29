# 重构需求文档 (Refactor Requirements)

## 1. 核心概念重构 (Core Concept)

- **旧架构**: Workspace 是一个逻辑文件夹，包含多个独立的 Git Repo。
- **新架构**: Workspace 本身是一个 **Git 仓库**。
  - 内部通过 **Submodule** 管理具体的子 Repo。
  - 用户指定 Base Workspace 时，必须验证其为 Git 仓库且包含 Submodule 配置。

## 2. 组织方式重构 (Organization & Creation)

- **创建 (Create)**:
  - 不再需要指定 Repo 列表。
  - 基于 Base Workspace 的 Git 仓库创建新的 **Worktree**。
  - 在新的 Worktree 中执行 `git submodule update --init --recursive` 初始化子模块。
  - 新 Workspace 默认检出/创建专属分支 (e.g., `workspace-{name}/stand`)。

## 3. 预览重构 (Preview)

- **目标**: 将当前 Workspace (Source) 的更改同步到 Preview Workspace (Target)。
- **流程**:
  1.  **准备 Target**:
      - 在 Preview Workspace 中，将所有子模块更新到远程 `main` 分支的最新状态 (`git fetch` & `git merge origin/main`)。
  2.  **寻找共同祖先 (Common Root)**:
      - 对比 Source 和 Target 的子模块 Commit，使用 `git merge-base` 找到共同祖先。
  3.  **准备 Preview 分支**:
      - 在 Target 子模块中，基于 **共同祖先** 创建或重置 `preview` 分支。
  4.  **同步更改 (Sync)**:
      - 使用 **文件同步** (`shutil.copy` / `rsync`) 将 Source 的文件复制到 Target。
      - _理由_: 能够同步未提交的更改，且不破坏 Source 的 Commit 历史。
  5.  **清理**:
      - 每次 Preview 开始前，清理旧的 `preview` 分支。

## 4. 同步重构 (Sync Command)

- **变更**: 废弃 `syncrule` 命令，引入通用的 `sync` 命令。
- **目标**: 保持所有 Workspace 的基准 (Main) 与远程同步，并更新各 Workspace 的专属分支。
- **流程**:
  1.  **更新 Base**: 在 Base Workspace (或当前上下文) 拉取远程 `main` 分支 (`git pull origin main`)。
  2.  **更新所有 Workspaces**:
      - 遍历所有本地 Workspace。
      - 在每个 Workspace 中，将 `main` 分支合并到当前分支 (e.g., `workspace-{name}/stand`)。
      - 执行 `git submodule update --init --recursive` 确保子模块指针和文件是最新的。
