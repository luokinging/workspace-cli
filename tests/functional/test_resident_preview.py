import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from workspace_cli.server.manager import WorkspaceManager
from workspace_cli.server.runner import PreviewRunner

@pytest.mark.asyncio
async def test_resident_preview_log_streaming():
    # Setup
    base_path = MagicMock()
    runner = PreviewRunner(base_path)
    manager = MagicMock()
    manager.runner = runner
    
    # Simulate subscribe_to_logs
    async def subscribe():
        queue = await runner.add_observer()
        try:
            while True:
                line = await queue.get()
                if line is None:
                    break
                yield line
        finally:
            runner.remove_observer(queue)

    # Test Scenario
    # 1. Client A subscribes
    stream_a = subscribe()
    # We need to start the generator to trigger add_observer
    # But add_observer is awaited inside.
    # We can't just call anext because it will block on queue.get()
    # Wait, add_observer is called BEFORE the loop.
    # But we need to reach the first yield or await.
    # Actually, we can just use a helper to ensure subscription.
    
    # Correct approach:
    # The generator needs to run until it hits the first await queue.get()
    # But we can't easily control that without a signal.
    # Let's modify subscribe to yield a "ready" signal or just use a task.
    
    # Alternative: Just manually add observer in test setup for verification
    # But we want to test subscribe logic.
    
    # Let's just start the generator in a task? No, we want to iterate it.
    # We can use `anext` but we need to make sure something is in queue?
    # No, we want to verify it's added.
    
    # Let's modify the test to trust that anext will block, so we put something first?
    # But we can't put something if we don't have the queue.
    
    # Let's modify subscribe to yield the queue first? No, that changes API.
    
    # Let's just rely on the fact that we can't easily inspect internal state in this way
    # without running the coroutine.
    # But we can use `runner.add_observer` directly to simulate what happens.
    
    # Or, we can just run the generator and put a message immediately?
    # But we don't have the queue reference.
    
    # Let's change the test to not rely on accessing `runner.observers` immediately.
    # Instead, we can just start the stream, then log, then check if we get it.
    # But we need to ensure the observer is added before we log.
    
    # To ensure observer is added, we can modify the mock runner to signal us?
    # Or just use a small sleep? (Not ideal but works for async test)
    
    task = asyncio.create_task(stream_a.__anext__())
    await asyncio.sleep(0.01) # Yield to let subscribe run until await queue.get()
    
    queue_a = list(runner.observers)[0]
    
    # 2. Log message
    runner._log("test", "Hello A")
    line = await task
    assert "Hello A" in line
    
    # 3. Client B subscribes (simulating new preview switch)
    # In real app, switch_preview calls runner.stop()
    await runner.stop()
    
    # 4. Verify Client A stream ends
    try:
        await stream_a.__anext__()
        assert False, "Stream should have ended"
    except StopAsyncIteration:
        pass
        
    # 5. Verify observers cleared
    assert len(runner.observers) == 0
