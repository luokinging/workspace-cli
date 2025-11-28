# Workspace CLI 需求文档

## 1. 系统目标

建立一个 **多 workspace + 单一 preview workspace + AI 并行开发** 支撑的开发环境管理系统。

### 核心目标

- **Workspace 逻辑分组**：Workspace 仅为文件夹，不被 git 管理。
- **Repo 独立管理**：每个 workspace 内的 repo 使用 git，支持 feature 分支、stand 分支、preview 分支。
- **Preview Workspace**：用于本地运行和 review，单一 workspace 映射，保证内容精确、轻量同步。
  - **精确同步**：仅同步 tracked 文件（自动 add），ignore 文件不被同步。
- **Rules Repo**：特殊 repo 可配置，支持 commit/push/merge 到其他 workspace。
- **Python CLI**：管理 workspace 创建、删除、preview、rulesync 等操作。

## 2. 核心概念与命名规则

### 分支规则

| 名称             | 说明                                          | 分支规则                            |
| :--------------- | :-------------------------------------------- | :---------------------------------- |
| **Feature 分支** | 工作中开发分支                                | `workspace/{feature_name}`          |
| **Stand 分支**   | 待机分支，防止 branch 冲突                    | `workspace-{workspacename}/stand`   |
| **Preview 分支** | preview workspace 内对应 workspace 的临时分支 | `workspace-{workspacename}/preview` |

### 概念说明

- **Preview Workspace**：单一 workspace，用于 live preview，同步当前 workspace 内容。每个 repo 对应一个 preview 分支。
- **Rules Repo**：特殊 repo，可配置，用于 commit/push/merge，自动同步到其他 workspace。配置文件指定，通过 CLI 命令 `syncrule` 操作。

### 规则约束

1.  **Preview Workspace 重建**：每个 repo 的 preview branch 每次切换都删除并重建，不累积历史。
2.  **Stand 分支待机**：Stand 分支用于待机状态，防止与 preview branch 或 feature 分支冲突。
3.  **单一 Live Preview**：任意时刻最多只有一个 workspace 对应 live preview。
4.  **自动查找根目录**：执行 preview 命令可以在 workspace 的任意子目录执行，CLI 自动向上查找 workspace 根目录。

## 3. Workspace / Repo 结构

```text
WORK_ROOT/
 ├── myworkspacename/                  # 基础 workspace，作为 preview workspace
 │    ├── repo1/
 │    ├── repo2/
 │    └── repo3/
 ├── myworkspacename-momo/             # 工作 workspace
 │    ├── repo1/  (workspace-momo/stand 等待开发分支)
 │    ├── repo2/
 │    └── repo3/
 ├── myworkspacename-kiki/
 │    └── ...
 └── myworkspacename-lulu/
      └── ...
```

- **Workspace**：本身是文件夹，不被 git 管理。
- **Repo**：使用 `git worktree`，feature 分支/stand 分支/preview 分支独立。
- **Preview Workspace**：每个 repo 对应 workspace 的 preview 分支。

## 4. Preview 同步逻辑

### 执行流程

当执行 `workspace-cli preview` 时：

1.  **准备当前 Workspace**：

    - 自动 `add` 当前 workspace 所有 tracked 文件（忽略 ignore 文件）。
    - 获取当前 workspace repo 与 main 分支的 `diff`。

2.  **更新 Preview Workspace**：

    - `git restore . && git clean -fd` 清理旧文件。
    - `checkout main`。
    - 删除旧 preview branch（如果存在）。
    - 创建新的 preview branch：`workspace-{workspacename}/preview`。
    - 应用 diff 文件到 preview workspace。

3.  **启动 Live Preview**：
    - 启动文件监听。
    - 任何 tracked 文件变动自动 `add` + `diff` + 同步。

### 切换 Workspace

切换到其他 workspace 执行 preview 时：

1.  停止当前 live preview。
2.  清理 preview workspace。
3.  删除旧 preview branch。
4.  创建新 preview branch 并同步当前 workspace 内容。

### 特点

- **精确同步**：文件“不能多不能少”。
- **无历史累积**：Preview branch 每次重建。
- **Live Preview**：自动监听文件变化。

## 5. Rulesync 功能

- **适用对象**：特殊 repo，可在 CLI 配置文件中指定。
- **命令**：`workspace-cli syncrule`

### 执行流程

1.  切换 rules repo 到 `main` 分支。
2.  `commit` + `push` 当前 workspace 的规则更改。
3.  对其他 workspace 的 rules repo `merge main`。
4.  返回当前 workspace 的 feature 分支。

**目的**：保持多 workspace 规则 repo 同步一致。

## 6. Workspace 创建 / 删除

### 创建 Workspace

**命令**：

```bash
workspace-cli create --base <基础workspace路径> --name <name1> <name2> ... --repo <repo1> <repo2> ...
```

**功能**：

- 基础 workspace 作为 preview workspace。
- 为每个 name 创建工作 workspace：目录名为在 baseworkspace 基础上加 `-{name}`。
- 使用 `git worktree` 将基础 workspace 的 repo 生成到新 workspace。
- 每个 workspace repo 默认创建 `stand` 分支作为待机分支。

### 删除 Workspace

**命令**：

```bash
workspace-cli delete --name <workspace>
```

**功能**：

- 删除指定 workspace 文件夹及其 worktree。
- 不影响 main workspace 或其他 workspace。

## 7. 使用示例

### 场景 1：创建多个 workspace

**命令**：

```bash
workspace-cli create --base ./work_root/myworkspacename --name momo kiki lulu --repo frontend backend rules
```

**结果**：

- 创建三个 workspace：`myworkspacename-momo`, `myworkspacename-kiki`, `myworkspacename-lulu`。
- Workspace 内 repo 使用 `git worktree`，分支为 `workspace-{name}/stand`。
- 基础 workspace `myworkspacename` 成为 preview workspace。

### 场景 2：在 workspace 根目录执行 live preview

**命令**：

```bash
workspace-cli preview
```

**结果**：

- 自动 add tracked 文件。
- 计算与 main 分支 diff。
- 清理 preview workspace。
- 创建 preview branch `workspace-momo/preview`。
- 应用 diff，同步文件。
- 启动 live preview，监听 `workspace-momo` repo 文件变化。

### 场景 3：在 workspace 子目录执行 preview

**命令**（例如在 `workspace-momo/frontend/src`）：

```bash
workspace-cli preview
```

**结果**：

- 自动向上查找 workspace 根目录 → `workspace-momo`。
- 执行 preview 同步逻辑（add + diff + clean + preview branch）。
- 启动 live preview。

### 场景 4：切换 live preview 到另一个 workspace

**命令**：

```bash
workspace-cli preview
```

**结果**：

- 停止当前 live preview（如 `workspace-momo`）。
- 清理 preview workspace。
- 删除旧 preview branch。
- 创建新的 preview branch `workspace-lulu/preview`。
- 应用 `workspace-lulu` diff。
- 启动 live preview。

### 场景 5：Rules repo 同步

**命令**：

```bash
workspace-cli syncrule
```

**结果**：

- rules repo 切换 `main` 分支。
- commit + push 当前 workspace 的规则更改。
- 自动 merge main 到其他 workspace rules repo。
- 返回当前 workspace feature 分支。

### 场景 6：删除 workspace

**命令**：

```bash
workspace-cli delete --name kiki
```

**结果**：

- 删除 `workspace-kiki` 文件夹及其 worktree。
- 不影响 main workspace 或其他 workspace。
- preview branch 若存在被删除。

### 场景 7：查看 workspace 状态

**命令**：

```bash
workspace-cli status
```

**结果**：

- 显示当前 workspace。
- 显示各 repo 当前分支状态。
- 显示 preview workspace preview branch。
- 显示 live preview 是否运行。

### 场景 8：手动指定 workspace 执行 preview

**命令**：

```bash
workspace-cli preview --workspace lulu
```

**结果**：

- 将 `workspace-lulu` 内容同步到 preview workspace。
- 自动 add + diff + clean + preview branch。
- 启动 live preview。

### 场景 9：启动独立文件监听

**命令**：

```bash
workspace-cli watch
```

**结果**：

- 启动文件监听模式。
- tracked 文件修改自动 add + diff + 同步到 preview workspace。
- 删除文件同步删除，保持 preview workspace 内容精确。
