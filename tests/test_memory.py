import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src" / "backend"))
sys.path.insert(0, str(Path(__file__).parent))

from src.backend.core.memory import MemoryManager


async def test_memory():
    print("=== Testing PersBot Memory System ===\n")
    
    manager = MemoryManager(workspace="/tmp/persbot_test_workspace")
    await manager.initialize()
    
    print("1. Write daily memory...")
    await manager.write_daily("User prefers to use dark mode")
    await manager.write_daily("Always use Chinese when user speaks Chinese")
    
    print("2. Write longterm memory...")
    await manager.write_longterm("## User Preferences\n- Dark mode\n- Chinese language")
    
    print("3. Search memory...")
    results = await manager.search("dark mode")
    print(f"   Found {len(results)} results:")
    for r in results:
        print(f"   - {r['path']}: {r['snippet'][:80]}...")
    
    print("4. Get context for prompt...")
    context = await manager.get_context_for_prompt()
    print(f"   Loaded {len(context)} memory blocks")
    for c in context:
        print(f"   - {c.get('type', 'unknown')}: {c.get('content', '')[:50]}...")
    
    print("5. List memory files...")
    files = await manager.list_files()
    print(f"   Found {len(files)} files:")
    for f in files:
        print(f"   - {f['name']}")
    
    await manager.shutdown()
    print("\n=== Memory System Test Complete ===")


if __name__ == "__main__":
    asyncio.run(test_memory())
