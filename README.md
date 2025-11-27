# Workspace CLI

Workspace CLI 是一个用于管理多工作区（Workspace）、Git 仓库（Repo）以及实时预览（Live Preview）的命令行工具。它旨在为 AI 辅助开发提供高效、隔离且易于同步的开发环境。

## 📖 项目简介

本项目的核心目标是解决多任务并行开发时的环境隔离与同步问题。通过将不同的开发任务分配到独立的 Workspace 中，每个 Workspace 拥有独立的 Git Worktree，互不干扰。同时，提供一个统一的 Preview Workspace 用于实时预览和 Review，确保开发过程中的变更能被精确、快速地同步。

### 核心特性

- **Workspace 逻辑分组**：Workspace 仅作为文件夹存在，不被 Git 直接管理，便于灵活组织。
- **Repo 独立管理**：利用 `git worktree` 技术，每个 Workspace 内的 Repo 拥有独立的分支（Feature/Stand/Preview），支持并行开发。
- **Preview Workspace**：单一的预览环境，支持从任意 Workspace 精确同步代码（仅同步 Tracked 文件），保证预览环境的纯净。
- **实时预览 (Live Preview)**：自动监听文件变更，实时同步到 Preview Workspace。
- **Rules Repo 同步**：支持特殊规则仓库的跨 Workspace 自动同步（Commit/Push/Merge）。

## 🛠️ 安装

确保你的环境中已安装 Python 3.8+ 和 Git。

```bash
# 克隆项目
git clone <your-repo-url>
cd workspace

# 安装依赖
pip install -e .
```

## 🚀 快速开始

### 1. 创建 Workspace

使用 `create` 命令基于一个基础 Workspace 创建新的开发 Workspace。

**自动配置**：如果当前目录下不存在 `workspace.json` 配置文件，`create` 命令会根据提供的 `--base` 和 `--repo` 参数自动创建一个。

```bash
# 语法
workspace create --name <新名称> [--base <基础路径> --repo <仓库列表>]

# 示例 1：已有配置文件，直接创建
workspace create --name feature-a

# 示例 2：首次使用，自动生成配置文件并创建
workspace create --name feature-a --base ./work_root/main --repo frontend --repo backend
```

### 2. 完整场景示例

假设你的目录结构如下：

```text
/Users/luoking/Desktop/Project/Work
└── workspace
    ├── luoking-creatify-coding  (Rules Repo)
    ├── main-web-ui
    └── webserver
```

#### 场景 1：创建多个 Workspace

**命令**：

```bash
cd /Users/luoking/Desktop/Project/Work

# 创建第一个 workspace (lulu) 并初始化配置
workspace create lulu \
  --base ./workspace \
  --repo main-web-ui \
  --repo webserver \
  --repo luoking-creatify-coding

# 创建后续 workspace
workspace create kiki
workspace create momo
```

**结果**：

- 创建三个 workspace：`workspace-lulu`, `workspace-kiki`, `workspace-momo`。
- Workspace 内 repo 使用 `git worktree`，默认分支为 `workspace-{name}/stand`。
- 基础 workspace `./workspace` 下的 repo 自动切换到 `workspace-{name}/preview` 分支，准备作为 Preview 环境。
- 自动生成 `workspace.json` 配置文件。

#### 场景 2：配置 Rules Repo

**操作**：

打开生成的 `workspace.json`，将 `rules_repo` 字段修改为你的规则仓库名称：

```json
"rules_repo": "luoking-creatify-coding"
```

#### 场景 3：在 Workspace 根目录执行 Live Preview

**命令**：

```bash
cd ./workspace-lulu
workspace preview
```

**结果**：

- 自动 `add` 当前 workspace 所有 tracked 文件。
- 计算与 `main` 分支的差异。
- 清理 Preview Workspace (即 Base Workspace)。
- 在 Preview Workspace 创建/重置 `workspace-lulu/preview` 分支。
- 应用差异文件，实现精确同步。
- 启动 Live Preview，实时监听文件变化并同步。

#### 场景 4：在 Workspace 子目录执行 Preview

**命令**（例如在 `workspace-momo/main-web-ui/src`）：

```bash
cd ./workspace-momo/main-web-ui/src
workspace preview
```

**结果**：

- CLI 自动向上查找 workspace 根目录（`workspace-momo`）。
- 执行与场景 3 相同的同步逻辑。
- 启动 Live Preview。

#### 场景 5：切换 Live Preview 到另一个 Workspace

**命令**：

```bash
# 假设当前正在 preview lulu
cd ./workspace-kiki
workspace preview
```

**结果**：

- 之前的 Live Preview 进程（如果还在运行）会停止（需手动或通过脚本控制，CLI 目前支持覆盖）。
- 清理 Preview Workspace。
- 删除旧的 `workspace-lulu/preview` 分支。
- 创建新的 `workspace-kiki/preview` 分支。
- 同步 `workspace-kiki` 的内容并启动监听。

#### 场景 6：Rules Repo 同步

**命令**：

```bash
workspace syncrule
```

**结果**：

- Rules Repo 切换到 `main` 分支。
- `commit` + `push` 当前 workspace 的规则更改。
- 自动对其他 workspace 的 Rules Repo 执行 `pull origin main` (或 merge)。
- 返回当前 workspace 的 Feature 分支。

#### 场景 7：查看 Workspace 状态

**命令**：

```bash
workspace status
```

**结果**：

- 显示 Base Workspace 路径。
- 列出所有已创建的 Workspace 及其路径。

#### 场景 8：删除 Workspace

**命令**：

```bash
workspace delete --name kiki
```

**结果**：

- 删除 `workspace-kiki` 文件夹。
- 自动清理相关的 git worktree。
- 不影响 Base Workspace 或其他 Workspace。

## 📚 详细文档

### 核心概念

- **Workspace**: 工作区文件夹，命名格式通常为 `{base}-{name}`。
- **Preview Workspace**: 基础 Workspace（通常是 `{base}`），用于运行和预览代码。
- **Repo**: Git 仓库，在各 Workspace 间通过 `git worktree` 共享对象库但保持工作目录独立。
- **Stand 分支**: 待机分支，用于在新 Workspace 中保持干净的状态。
- **Preview 分支**: 临时分支，仅存在于 Preview Workspace，用于应用来自其他 Workspace 的变更。

### 系统设计与分支策略

本项目采用独特的分支模型来隔离开发环境与预览环境。

#### 1. 分支模型

| 分支类型         | 命名规则                   | 作用                                                                                                     | 生命周期                                                         |
| :--------------- | :------------------------- | :------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------- |
| **Feature 分支** | `workspace/{feature_name}` | **实际开发分支**。用户在 Workspace 中手动创建，用于日常开发。                                            | 长期存在，随功能开发结束合并/删除。                              |
| **Stand 分支**   | `workspace-{name}/stand`   | **待机/占位分支**。`create` 命令自动创建。当 Workspace 刚创建或未切到 Feature 分支时使用，防止分支冲突。 | Workspace 存在期间长期存在。                                     |
| **Preview 分支** | `workspace-{name}/preview` | **预览专用分支**。`preview` 命令自动创建。仅存在于 Base Workspace (Preview Workspace) 中。               | **临时**。每次执行 `preview` 或切换 Workspace 时会被删除并重建。 |

#### 2. 工作流设计

- **Create 阶段**：

  - 执行 `create` 时，CLI 会在目标 Workspace 中为每个 Repo 创建一个 `stand` 分支。
  - **设计意图**：新 Workspace 应该是一个干净的“待机”状态，等待用户检出（Checkout）具体的 Feature 分支进行开发。此时不应直接处于 Preview 状态。

- **Preview 阶段**：
  - 执行 `preview` 时，CLI 会将当前 Workspace（开发中）的代码同步到 Base Workspace（预览环境）。
  - 此时，Base Workspace 的 Repo 会被切换到 `preview` 分支。
  - **设计意图**：Base Workspace 充当“播放器”，负责运行和展示代码；而开发 Workspace 充当“编辑器”，负责修改代码。

### 配置文件说明

`workspace.json` 是项目的核心配置文件，通常位于 Work Root 目录下。

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
  "rules_repo": "rules-repo-name"
}
```

| 字段           | 类型   | 说明                                                                                          |
| :------------- | :----- | :-------------------------------------------------------------------------------------------- |
| `base_path`    | String | **基础 Workspace 的绝对路径**。新 Workspace 将以此为蓝本创建，Preview 也是在此目录下运行。    |
| `repos`        | List   | **管理的仓库列表**。定义了哪些仓库需要被 Workspace 管理。                                     |
| `repos[].name` | String | 仓库名称，用于 CLI 命令中引用（如 `create --repo name`）。                                    |
| `repos[].path` | String | 仓库相对于 Workspace 根目录的路径。                                                           |
| `repos[].url`  | String | (可选) 仓库的远程 Git 地址。**注：当前版本暂未使用此字段，预留用于未来支持自动 Clone 功能。** |
| `rules_repo`   | String | (可选) 指定哪个仓库是规则仓库，用于 `syncrule` 命令。                                         |

### 命令参考

| 命令       | 说明               | 示例                                     |
| :--------- | :----------------- | :--------------------------------------- |
| `create`   | 创建新的 Workspace | `workspace create --name dev --repo web` |
| `delete`   | 删除 Workspace     | `workspace delete --name dev`            |
| `status`   | 查看当前状态       | `workspace status`                       |
| `preview`  | 启动预览同步       | `workspace preview`                      |
| `syncrule` | 同步规则仓库       | `workspace syncrule`                     |

更多详细设计和原理请参考 [需求文档](requirement-doc/requirement.md)。
