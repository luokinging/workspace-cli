import os
import shutil
import subprocess
import json
import unittest
from pathlib import Path

class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("/tmp/workspace_cli_test")
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        self.test_dir.mkdir()
        
        # Setup base workspace
        self.base_ws = self.test_dir / "base-ws"
        self.base_ws.mkdir()
        subprocess.run(["git", "init"], cwd=self.base_ws, check=True)
        subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=self.base_ws, check=True)
        
        # Setup a repo (outside base-ws)
        self.repo_path = self.test_dir / "repo1"
        self.repo_path.mkdir()
        subprocess.run(["git", "init"], cwd=self.repo_path, check=True)
        subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=self.repo_path, check=True)
        
        # Add as submodule to base-ws
        subprocess.run(["git", "submodule", "add", str(self.repo_path), "repo1"], cwd=self.base_ws, check=True)
        subprocess.run(["git", "commit", "-m", "add submodule"], cwd=self.base_ws, check=True)
        
        # Create config
        self.config = {
            "base_path": str(self.base_ws),
            "repos": [
                {"name": "repo1", "path": "repo1"}
            ]
        }
        with open(self.base_ws / "workspace.json", "w") as f:
            json.dump(self.config, f)

    def tearDown(self):
        if self.test_dir.exists():
            # Cleanup might fail if worktrees are locked or something
            # shutil.rmtree(self.test_dir, ignore_errors=True)
            pass

    def run_cli(self, args):
        import sys
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path.cwd())
        cmd = [sys.executable, "-m", "workspace_cli.main"] + args
        # We need to run from base_ws so it finds the config
        result = subprocess.run(
            cmd, 
            cwd=self.base_ws, 
            env=env,
            capture_output=True, 
            text=True
        )
        return result

    def test_create_and_delete_workspace(self):
        # 1. Create
        print("Testing create...")
        result = self.run_cli(["create", "test1"])
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        if result.returncode != 0:
            print(result.stderr)
        self.assertEqual(result.returncode, 0)
        
        # Verify dir exists
        ws_path = self.test_dir / "base-ws-test1"
        self.assertTrue(ws_path.exists())
        
        # Verify worktree
        wt_path = ws_path / "repo1"
        self.assertTrue(wt_path.exists())
        self.assertTrue((wt_path / ".git").exists())
        
        # 2. Status
        print("Testing status...")
        result = self.run_cli(["status"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("test1", result.stdout)
        
        # 3. Delete
        print("Testing delete...")
        result = self.run_cli(["delete", "test1"])
        self.assertEqual(result.returncode, 0)
        
        # Verify dir gone
        self.assertFalse(ws_path.exists())

if __name__ == "__main__":
    unittest.main()
