import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.backend.core.skill import SkillManager, SkillLoader, SkillModel


async def create_test_skill():
    skill_dir = Path("/tmp/test_skills")
    skill_dir.mkdir(exist_ok=True)
    
    git_skill_dir = skill_dir / "test_skill"
    git_skill_dir.mkdir(exist_ok=True)
    
    skill_json = {
        "name": "test_skill",
        "description": "A test skill for verification",
        "version": "1.0.0",
        "main": "handler.py",
        "commands": {
            "hello": {
                "description": "Say hello",
                "usage": "test_skill hello"
            },
            "echo": {
                "description": "Echo back the input",
                "usage": "test_skill echo <message>"
            }
        },
        "exclude_patterns": ["*.pyc", "__pycache__"]
    }
    
    import json
    with open(git_skill_dir / "test_skill_skill.json", "w") as f:
        json.dump(skill_json, f)
    
    handler_py = '''
import asyncio

async def register(skill):
    async def hello(params):
        return "Hello from test skill!"
    
    async def echo(params):
        msg = params.get("message", "no message")
        return f"Echo: {msg}"
    
    skill.register_handler("hello", hello)
    skill.register_handler("echo", echo)
'''
    
    with open(git_skill_dir / "handler.py", "w") as f:
        f.write(handler_py)
    
    return str(skill_dir)


async def test_skill_loading():
    print("=== Testing Skill Loading ===\n")
    
    skill_dir = await create_test_skill()
    print(f"Created test skill at: {skill_dir}")
    
    manager = SkillManager(skill_dir=skill_dir)
    await manager.initialize()
    
    # Test 1: List skills
    print("\n1. Listing skills...")
    skills = manager.list_skills()
    print(f"   Loaded skills: {len(skills)}")
    for s in skills:
        print(f"   - {s.name}: {s.description}")
    
    # Test 2: Get skill status
    print("\n2. Getting skill status...")
    status = manager.get_skill_status()
    print(f"   Status: {status}")
    
    # Test 3: Get commands
    print("\n3. Getting available commands...")
    commands = manager.get_commands()
    print(f"   Commands: {commands}")
    
    # Test 4: Execute skill command
    print("\n4. Executing 'hello' command...")
    result = await manager.execute_skill("test_skill", "hello")
    print(f"   Result: {result}")
    
    # Test 5: Execute with params
    print("\n5. Executing 'echo' command with params...")
    result = await manager.execute_skill("test_skill", "echo", {"message": "Hello World"})
    print(f"   Result: {result}")
    
    # Test 6: Get available commands by query
    print("\n6. Searching for 'he' commands...")
    found = await manager.get_available_commands("he")
    print(f"   Found: {found}")
    
    # Test 7: Has command check
    print("\n7. Checking if command exists...")
    has = manager.has_command("test_skill", "hello")
    print(f"   Has 'hello': {has}")
    has = manager.has_command("test_skill", "nonexistent")
    print(f"   Has 'nonexistent': {has}")
    
    # Test 8: Unload skill
    print("\n8. Unloading skill...")
    await manager.unload_skill("test_skill")
    status = manager.get_skill_status()
    print(f"   After unload: {status}")
    
    # Test 9: Reload skill
    print("\n9. Reloading skill...")
    await manager.reload_skill("test_skill")
    status = manager.get_skill_status()
    print(f"   After reload: {status}")
    
    await manager.shutdown()
    print("\n=== Tests Passed ===")


if __name__ == "__main__":
    asyncio.run(test_skill_loading())