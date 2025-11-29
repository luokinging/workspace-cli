# E2E Test Documentation

此文档详细描述了 Workspace CLI 的端到端 (E2E) 测试用例。AI Agent 应能够读取此文档并自动在 `test-e2e-work-root` 目录中执行测试。

## 测试环境准备

1.  **工作目录**: `test-e2e-work-root` (所有测试操作均在此目录下进行，或以此为根)。
2.  **前置条件**:
    - 安装 `workspace-cli` (`pip install -e .`)。
    - 确保 `git` 可用。
    - 清理之前的测试数据 (如果存在)。
    - e2e 测试中，你可以创建额外的测试脚本，但是测试完成要删除

## 测试用例

### Case 1: 初始化与 Workspace 创建

**目标**: 验证能够基于现有的 git repo 创建新的 workspace，并生成正确的目录结构和 git worktree。

**步骤**:

1.  **创建 Base Repo**:
    - 创建目录 `main-repo`。
    - 初始化 git (`git init`)。
    - 添加文件 `README.md` 并提交 (`git commit`)。
    - 创建子目录 `backend`，初始化 git，添加文件并提交 (模拟多 repo 结构)。
2.  **创建 Workspace**:
    - 执行命令: `workspace-cli create feature-a --base $(pwd)/main-repo --repo backend`
    - (注意: `--base` 需要绝对路径，或相对于 CWD 的路径)。

**验证**:

- 存在目录 `main-repo-feature-a`。
- 存在目录 `main-repo-feature-a/backend`。
- `main-repo-feature-a/backend` 是一个 git worktree。
- `main-repo-feature-a/backend` 的当前分支为 `workspace-feature-a/stand`。
- 存在 `workspace.json` 配置文件 (通常在执行命令的目录或 work root)。

### Case 2: 自动检测与 Preview 初始化

**目标**: 验证 CLI 能够自动检测当前 workspace 名称，并初始化 preview 环境。

**步骤**:

1.  进入 workspace 目录: `cd main-repo-feature-a`。
2.  执行一次性 preview: `workspace-cli preview --once`。

**验证**:

- CLI 输出 "Auto-detected workspace: feature-a"。
- Base Repo (`main-repo`) 切换到了 `preview` 分支。
- `main-repo` 的内容与 `feature-a` workspace 的内容一致。

### Case 3: Live Preview 文件同步

**目标**: 验证 Live Preview 模式下，文件的新增、修改、删除能够实时同步到 Base Repo (Preview Workspace)。

**步骤**:

1.  启动 Live Preview (后台运行或新终端): `workspace-cli preview`。
2.  **新增文件**: 在 `main-repo-feature-a` 中创建 `new_file.txt`。
    - 验证: CLI 输出 `[CREATED] new_file.txt` (绿色)。
    - 验证: `main-repo/new_file.txt` 存在。
3.  **修改文件**: 修改 `main-repo-feature-a/README.md`。
    - 验证: CLI 输出 `[UPDATED] README.md` (黄色)。
    - 验证: `main-repo/README.md` 内容更新。
4.  **删除文件**: 删除 `main-repo-feature-a/new_file.txt`。
    - 验证: CLI 输出 `[DELETED] new_file.txt` (红色)。
    - 验证: `main-repo/new_file.txt` 不存在。

### Case 4: 并发控制与自动接管

**目标**: 验证当启动新的 Preview 时，会自动终止已存在的 Preview 进程，并接管 Preview 环境。

**步骤**:

1.  确保一个 preview 进程正在运行 (Case 3)。
2.  尝试启动第二个 preview: `workspace-cli preview` (可以在另一个 workspace 或同一个 workspace)。
    - 验证: CLI 提示 "Stopping existing preview process..."。
    - 验证: 新的 preview 进程成功启动并开始监听。
    - 验证: 旧的 preview 进程被终止 (可以通过 PID 检查)。
3.  停止当前的 preview 进程。
    - 验证: `.workspace_preview.pid` 文件被删除。

### Case 5: 切换 Workspace

**目标**: 验证从一个 workspace 切换 preview 到另一个 workspace 时，环境被正确重置。

**步骤**:

1.  创建第二个 workspace: `workspace-cli create feature-b ...`。
2.  在 `feature-b` 中修改一些文件，使其与 `feature-a` 不同。
3.  执行: `workspace-cli preview --workspace feature-b --once` (或进入目录执行)。
4.  **验证**:
    - `main-repo` (Preview Workspace) 现在包含 `feature-b` 的内容。
    - `main-repo` 仍然在 `preview` 分支。
    - 之前 `feature-a` 的内容被清理。

### Case 6: 日志与调试

**目标**: 验证调试模式和日志文件输出。

**步骤**:

1.  执行: `workspace-cli --debug --log-file debug.log preview --once`。
2.  **验证**:
    - 生成了 `debug.log` 文件。
    - 文件中包含 DEBUG 级别的日志信息。

### Case 7: Rules Sync with Expansion

**目标**: 验证 `syncrule` 命令能够同步 rules repo，并根据 `workspace_expand_folder` 配置将指定文件夹的内容展开到所有 workspace。

**步骤**:

1.  **配置 Rules Repo**:
    - 创建一个独立的 `rules-repo` git 仓库。
    - 在 `workspace.json` 中配置 `rules_repo` 和 `workspace_expand_folder` (例如设置为 "expand")。
2.  **准备 Expansion 内容**:
    - 在 `rules-repo` 中创建 `expand` 目录。
    - 在 `expand` 目录中添加文件 `agent_config.json`。
    - 提交并推送到远程 (模拟)。
3.  **执行 Sync**:
    - 在任意 workspace 中执行: `workspace-cli syncrule`。
4.  **验证**:
    - `agent_config.json` 出现在所有 workspace 的根目录下。
    - 如果 workspace 中原先存在同名文件，应被覆盖。
    - 如果 `expand` 目录中有子目录，也应被递归复制。
