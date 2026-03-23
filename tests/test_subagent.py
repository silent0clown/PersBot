import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.backend.core.agent import (
    BaseAgent, SubAgent, AgentRegistry,
    AgentConfig, AgentTask, AgentStatus
)


async def test_subagent():
    print("=== Testing SubAgent ===\n")
    
    # Test 1: Create agent registry and templates
    print("1. Creating agent registry and templates...")
    registry = AgentRegistry()
    
    registry.register_template("worker", AgentConfig(
        name="Worker Agent",
        description="A basic worker agent",
        max_steps=50,
        timeout=120
    ))
    
    registry.register_template("analyzer", AgentConfig(
        name="Analyzer Agent",
        description="Analyzes data",
        max_steps=20,
        capabilities=[{"name": "analyze", "description": "Analyze data"}]
    ))
    
    print("   Templates registered")
    
    # Test 2: Create agents from templates
    print("\n2. Creating agents from templates...")
    agent1 = registry.create_from_template("worker")
    agent2 = registry.create_from_template("analyzer")
    
    if agent1:
        registry.register(agent1)
    if agent2:
        registry.register(agent2)
        
    print(f"   Agent 1: {agent1.get_info()['name']}")
    print(f"   Agent 2: {agent2.get_info()['name']}")
    
    # Test 3: List all agents
    print("\n3. Listing all agents...")
    agents = registry.list_agents()
    print(f"   Total agents: {len(agents)}")
    for a in agents:
        print(f"   - {a['name']}: {a['status']}")
    
    # Test 4: Agent spawns child
    print("\n4. Agent spawning child...")
    child_config = AgentConfig(
        name="Child Agent",
        description="A child of worker"
    )
    child = await agent1.spawn_child(child_config)
    print(f"   Child created: {child.get_info()}")
    
    # Test 5: Task assignment and execution
    print("\n5. Testing task execution...")
    task = AgentTask(
        description="Process some data",
        input_data={"data": "test"}
    )
    
    result = await agent1.execute_task(task)
    print(f"   Task result: {result}")
    print(f"   Task status: {task.status}")
    
    # Test 6: Task history
    print("\n6. Checking task history...")
    info = agent1.get_info()
    print(f"   Task history count: {info['task_count']}")
    
    # Test 7: Unregister agent
    print("\n7. Unregistering agent...")
    registry.unregister(agent2.id)
    agents = registry.list_agents()
    print(f"   Remaining agents: {len(agents)}")
    
    # Test 8: Agent with custom implementation
    print("\n8. Custom agent implementation...")
    
    class CustomAgent(BaseAgent):
        async def _run_task(self, task):
            result = f"Custom processing: {task.description}"
            await asyncio.sleep(0.1)
            return {"status": "success", "result": result}
    
    custom = CustomAgent(AgentConfig(
        name="Custom Agent",
        description="Custom implementation"
    ))
    registry.register(custom)
    
    custom_task = AgentTask(description="Run custom logic")
    result = await custom.execute_task(custom_task)
    print(f"   Custom result: {result}")
    
    print("\n=== Tests Passed ===")


if __name__ == "__main__":
    asyncio.run(test_subagent())