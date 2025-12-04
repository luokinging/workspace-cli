import os
import socket
import threading
import subprocess
import signal
import time
import typer
from pathlib import Path
from typing import List, Optional
from workspace_cli.models import WorkspaceConfig
from workspace_cli.core import sync as sync_core

class PreviewRunner:
    def __init__(self, config: WorkspaceConfig):
        self.config = config
        self.running_processes: List[subprocess.Popen] = []
        self.server_socket: Optional[socket.socket] = None
        self.port_file = config.base_path / ".run_preview.port"
        self.lock = threading.Lock()
        self.current_workspace: Optional[str] = None
        self.stop_event = threading.Event()
        self.active_client_conn: Optional[socket.socket] = None

    def start(self):
        """Start the runner: setup socket and wait for commands."""
        self._setup_socket()
        
        typer.secho("Preview Runner Started", fg=typer.colors.GREEN)
        typer.echo(f"Listening on port {self.server_socket.getsockname()[1]}")
        
        # Start socket listener thread
        listener_thread = threading.Thread(target=self._listen_socket, daemon=True)
        listener_thread.start()
        
        try:
            while not self.stop_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stop runner and cleanup."""
        self.stop_event.set()
        self._stop_processes()
        if self.active_client_conn:
            try:
                self.active_client_conn.close()
            except Exception:
                pass
        if self.server_socket:
            self.server_socket.close()
        if self.port_file.exists():
            self.port_file.unlink()
        typer.secho("Preview Runner Stopped", fg=typer.colors.YELLOW)

    def _setup_socket(self):
        """Setup IPC socket."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(('127.0.0.1', 0)) # Random port
        self.server_socket.listen(1)
        
        port = self.server_socket.getsockname()[1]
        self.port_file.write_text(str(port))

    def _listen_socket(self):
        """Listen for incoming connections."""
        self.server_socket.settimeout(1.0) # Allow checking stop_event periodically
        
        while not self.stop_event.is_set():
            try:
                conn, addr = self.server_socket.accept()
                
                # New connection received
                typer.secho(f"\n[Runner] New connection from {addr}", fg=typer.colors.BLUE)
                
                # 1. Kick off existing client if any
                if self.active_client_conn:
                    typer.secho("[Runner] Terminating existing client session...", fg=typer.colors.YELLOW)
                    try:
                        self.active_client_conn.close()
                    except Exception:
                        pass
                    self.active_client_conn = None
                
                # 2. Accept new client
                self.active_client_conn = conn
                
                # 3. Handle handshake
                try:
                    data = conn.recv(1024).decode().strip()
                    if data.startswith("PREVIEW "):
                        workspace = data.split(" ", 1)[1]
                        typer.secho(f"[Runner] Starting session for workspace: {workspace}", fg=typer.colors.MAGENTA)
                        
                        # Trigger restart in a separate thread
                        threading.Thread(target=self._restart_lifecycle, args=(workspace,)).start()
                        
                        conn.sendall(b"ACCEPTED")
                    else:
                        conn.close()
                        self.active_client_conn = None
                except Exception as e:
                    typer.secho(f"[Runner] Handshake failed: {e}", fg=typer.colors.RED)
                    conn.close()
                    self.active_client_conn = None
                    
            except socket.timeout:
                continue
            except OSError:
                break
            except Exception as e:
                print(f"Socket error: {e}")

    def _stop_processes(self):
        """Stop all running child processes."""
        with self.lock:
            if not self.running_processes:
                return
                
            typer.secho("[Runner] Stopping running processes...", fg=typer.colors.YELLOW)
            for p in self.running_processes:
                if p.poll() is None:
                    p.terminate()
            
            # Wait for termination
            for p in self.running_processes:
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    p.kill()
            
            self.running_processes.clear()

    def _run_command(self, cmd: str, label: str, color: str):
        """Run a single command and stream output."""
        try:
            # Use shell=True for flexibility with user commands
            process = subprocess.Popen(
                cmd, 
                shell=True, 
                cwd=self.config.base_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                preexec_fn=os.setsid # Create new process group
            )
            
            with self.lock:
                self.running_processes.append(process)
            
            for line in process.stdout:
                typer.secho(f"[{label}] {line.strip()}", fg=color)
                
            process.wait()
            
            with self.lock:
                if process in self.running_processes:
                    self.running_processes.remove(process)
                    
        except Exception as e:
            typer.secho(f"[{label}] Error: {e}", fg=typer.colors.RED)

    def _execute_parallel(self, commands: List[str], label: str, color: str):
        """Execute commands in parallel."""
        if not commands:
            return

        threads = []
        for cmd in commands:
            t = threading.Thread(target=self._run_command, args=(cmd, label, color))
            t.start()
            threads.append(t)
        
        # We don't join here if we want them to run indefinitely (like servers)
        # But for hooks like 'before_clear', we might want to wait?
        # Requirement says: "Parallel execute before clear -> clear ... -> Parallel execute preview -> Parallel execute after preview"
        # 'preview' commands are likely long-running. 'hooks' might be short or long.
        # Usually 'before_clear' implies we wait for them to finish before clearing?
        # But the requirement says "Parallel execute before clear -> clear ...".
        # If 'before_clear' are long running, we can't wait.
        # Assumption: 'before_clear' are short-lived tasks. We should wait for them?
        # "workspace run-preview active duration should be internal programs duration"
        # Let's assume we wait for 'before_clear' hooks to finish before proceeding to clear.
        
        if label == "BeforeClear":
             for t in threads:
                 t.join()

    def _restart_lifecycle(self, workspace_name: str):
        """Execute the full preview lifecycle."""
        # 1. Stop existing
        self._stop_processes()
        
        self.current_workspace = workspace_name
        
        # 2. Before Clear Hooks
        if self.config.preview_hook.before_clear:
            typer.secho("\n[Runner] Running before_clear hooks...", fg=typer.colors.BLUE)
            self._execute_parallel(self.config.preview_hook.before_clear, "BeforeClear", typer.colors.CYAN)
            
        # 3. Clear & Sync
        typer.secho("\n[Runner] Cleaning and Syncing...", fg=typer.colors.BLUE)
        try:
            # We use the sync_core logic
            # Note: sync_core.rebuild_preview might try to kill processes if we used the old pid file mechanism.
            # But we are the runner now. We should probably avoid conflicting with 'clean_preview' CLI command if it uses PID.
            # The 'clean_preview' command uses .workspace_preview.pid.
            # We should probably NOT use that PID file for *this* runner, or we should manage it.
            # Actually, `rebuild_preview` does NOT kill processes. `clean_preview` does.
            # `rebuild_preview` calls `_force_clean_repo`.
            
            sync_core.rebuild_preview(workspace_name, self.config)
        except Exception as e:
            typer.secho(f"[Runner] Sync failed: {e}", fg=typer.colors.RED)
            return

        # 4. Preview & After Preview (Parallel)
        typer.secho("\n[Runner] Starting Preview & After Hooks...", fg=typer.colors.BLUE)
        
        commands = []
        labels = []
        
        for cmd in self.config.preview:
            commands.append((cmd, "Preview", typer.colors.GREEN))
            
        for cmd in self.config.preview_hook.after_preview:
            commands.append((cmd, "AfterPreview", typer.colors.MAGENTA))
            
        for cmd, label, color in commands:
            t = threading.Thread(target=self._run_command, args=(cmd, label, color))
            t.start()
            # We don't join these, they run until stopped or finished.
