import asyncio
import subprocess
import shlex
from typing import List, Optional, Set
from pathlib import Path
from rich.console import Console
from rich.style import Style

class PreviewRunner:
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.console = Console()
        self.process: Optional[subprocess.Popen] = None
        self.colors = ["cyan", "magenta", "green", "yellow", "blue"]
        self.color_idx = 0
        self.observers: Set[asyncio.Queue] = set()

    def _get_color(self) -> str:
        color = self.colors[self.color_idx % len(self.colors)]
        self.color_idx += 1
        return color

    def _log(self, name: str, message: str, color: str = "cyan"):
        # Console output
        label = name.capitalize()
        self.console.print(f"[{color}][{label}][/{color}] {message}")
        # Broadcast to observers
        for queue in list(self.observers):
            try:
                queue.put_nowait(f"[{color}][{label}][/{color}] {message}")
            except asyncio.QueueFull:
                pass # Drop if full? Or should we use infinite queue?

    async def add_observer(self) -> asyncio.Queue:
        queue = asyncio.Queue()
        self.observers.add(queue)
        return queue

    def remove_observer(self, queue: asyncio.Queue):
        if queue in self.observers:
            self.observers.remove(queue)

    async def run_hooks(self, hooks: List[str], stage: str):
        if not hooks:
            return
        
        color = self._get_color()
        self._log(stage, "Starting hooks...", color)
        
        for cmd in hooks:
            self._log(stage, f"Running: {cmd}", color)
            try:
                # Run synchronously for hooks as they are usually setup steps
                # We can use asyncio.create_subprocess_shell for async
                process = await asyncio.create_subprocess_shell(
                    cmd,
                    cwd=self.base_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if stdout:
                    for line in stdout.decode().splitlines():
                        self._log(stage, line, color)
                if stderr:
                    for line in stderr.decode().splitlines():
                        self._log(stage, line, "red")
                        
                if process.returncode != 0:
                    self._log(stage, f"Failed with code {process.returncode}", "red")
                    raise RuntimeError(f"Hook failed: {cmd}")
                    
            except Exception as e:
                self._log(stage, f"Error: {e}", "red")
                raise

    async def start_preview(self, commands: List[str]):
        if not commands:
            return

        # For now, we only support one long-running preview command
        # If multiple, we might need a supervisor like supervisord or parallel execution
        # Let's assume the first one is the main one for now, or run them in parallel?
        # The user requirement implies "preview" is a list of commands.
        # "execute preview commands and after_preview hooks in parallel" was mentioned in previous context.
        
        # Let's run all preview commands in background
        self.processes = []
        
        import os
        for cmd in commands:
            color = self._get_color()
            self._log("preview", f"Starting: {cmd}", color)
            
            # We use subprocess.Popen for long running processes to keep control
            # But we want to stream output.
            # asyncio.create_subprocess_shell is better for async streaming.
            
            # Use preexec_fn=os.setsid to create a new process group
            # This allows us to kill the entire tree (shell + children)
            process = await asyncio.create_subprocess_shell(
                cmd,
                cwd=self.base_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=os.setsid
            )
            self.processes.append((process, color, cmd))
            
            # Start a task to read output
            asyncio.create_task(self._stream_output(process, "preview", color))

    async def _stream_output(self, process, name: str, color: str):
        # Stream stdout
        async def read_stream(stream, is_stderr=False):
            while True:
                line = await stream.readline()
                if not line:
                    break
                text = line.decode().strip()
                if text:
                    log_color = "red" if is_stderr else color
                    self._log(name, text, log_color)
        
        await asyncio.gather(
            read_stream(process.stdout),
            read_stream(process.stderr, is_stderr=True)
        )

    async def stop(self):
        # Signal observers to stop? 
        # We can put a special None value or just clear them.
        # But the requirement is "current resident command line will automatically exit".
        # So we should send a signal.
        for queue in list(self.observers):
            queue.put_nowait(None) # None indicates stream end
        self.observers.clear()

        import os
        import signal
        if hasattr(self, 'processes'):
            for process, _, cmd in self.processes:
                try:
                    self._log("preview", f"Stopping: {cmd}", "yellow")
                    # Kill the process group
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    try:
                        await asyncio.wait_for(process.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        self._log("preview", f"Force killing: {cmd}", "red")
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                        await process.wait()
                except ProcessLookupError:
                    pass # Already dead
                except Exception as e:
                    self._log("preview", f"Error stopping {cmd}: {e}", "red")
            self.processes = []
