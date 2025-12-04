# Development Workflow

This document outlines the standard workflow for developing, testing, and verifying changes in `workspace-cli`. All contributors (human and AI) must follow this process to ensure stability and quality.

## 1. Development Cycle

### Step 1: Feature/Fix Implementation

- **Coding**: Implement changes in the `workspace_cli` package.
- **Dependency Injection**: Always use `GitProvider` or other interfaces for external dependencies to ensure testability.

### Step 2: Unit Testing (Mandatory)

- **Scope**: Test individual classes and functions in isolation.
- **Mocking**: Use `MockGitProvider` and `unittest.mock` to mock file system and git operations. **No real git commands or network calls allowed.**
- **Command**:
  ```bash
  pytest tests/unit
  ```
- **Requirement**: All unit tests must pass before proceeding.

### Step 3: E2E Testing (Mandatory)

- **Scope**: Verify the entire system flow (Client -> Daemon -> Git/FS).
- **Environment**: The test runner handles setting up a temporary directory, a local bare git repo, and a temporary Daemon instance.
- **Command**:
  ```bash
  pytest tests/e2e
  ```
- **Requirement**: All E2E tests must pass. This ensures that the CLI commands correctly interact with the Daemon and that the Daemon performs the expected side effects (file creation, git branching, etc.).

### Step 4: Manual Verification (Optional but Recommended)

- For UI changes or complex interactive flows, run the daemon locally and test with a real workspace.

  ```bash
  # Terminal 1
  workspace daemon --foreground

  # Terminal 2
  workspace create test-feature
  workspace preview test-feature
  ```

---

## 2. Testing Guidelines

### Unit Tests

- **Test First Principle**: If a functionality change affects existing unit tests, **you must update the unit tests first** to reflect the new expected behavior, then modify the code to pass the tests.
- **Location**: `tests/unit/`.
- **Scope**: Focus on edge cases, error handling, and state transitions.
- **Mocking**: Use `MockGitProvider` to avoid real git operations.

### E2E Tests

- **Documentation Driven**: `dev-doc/e2e.md` is the **primary source of truth**.
- **Process**:
  1.  **Read**: Review `dev-doc/e2e.md` to understand the required scenarios.
  2.  **Check Updates**: If a feature has changed, check if `tests/unit` and `dev-doc/e2e.md` need updates.
  - **Rule**: If `dev-doc/e2e.md` is updated, the corresponding test script **must** be updated to match.
  3.  **Setup**: Manually (or via script) create the test root directory (e.g., `test-e2e-work-root`).
  4.  **Execute**: Run through all Use Cases described in the document.
  - **Command**: `pytest tests/e2e`
  5.  **Verify**: Check files and git state after each step.
  6.  **Cleanup**: If successful, delete the test root directory.
- **Mandatory Run**: After any feature change, you **must** run all tests (Unit + E2E) to ensure no regressions.

---

## 3. Checklist for Pull Requests / Commits

- [ ] Code changes implemented.
- [ ] `pytest tests/unit` passed.
- [ ] `pytest tests/e2e` passed.
- [ ] Documentation (docstrings, README, dev-docs) updated if necessary.
