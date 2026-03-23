import asyncio
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.backend.core.task import (
    TodoManager, TaskCreate, TaskUpdate, 
    TaskFilter, TaskStatus, TaskPriority
)


async def test_todo_manager():
    print("=== Testing TodoManager ===\n")
    
    manager = TodoManager(storage_path="/tmp/test_tasks.json")
    await manager.initialize()
    
    # Test 1: Create tasks
    print("1. Creating tasks...")
    task1 = await manager.create_task(TaskCreate(
        content="Implement skill loading system",
        priority=TaskPriority.HIGH,
        tags=["backend", "feature"]
    ))
    print(f"   Created task 1: {task1.id}")
    
    task2 = await manager.create_task(TaskCreate(
        content="Write unit tests",
        priority=TaskPriority.MEDIUM,
        tags=["testing"]
    ))
    print(f"   Created task 2: {task2.id}")
    
    task3 = await manager.create_task(TaskCreate(
        content="Refactor code",
        priority=TaskPriority.LOW,
        tags=["refactor"]
    ))
    print(f"   Created task 3: {task3.id}")
    
    # Test 2: List tasks
    print("\n2. Listing all tasks...")
    tasks = await manager.list_tasks()
    print(f"   Total tasks: {len(tasks)}")
    for t in tasks:
        print(f"   - [{t.priority}] {t.content}")
    
    # Test 3: Update task
    print("\n3. Updating task...")
    updated = await manager.update_task(task1.id, TaskUpdate(
        status=TaskStatus.IN_PROGRESS,
        tags=["backend", "feature", "in-progress"]
    ))
    print(f"   Updated: {updated.status}, tags: {updated.tags}")
    
    # Test 4: Add subtask
    print("\n4. Adding subtask...")
    subtask = await manager.add_subtask(task1.id, TaskCreate(
        content="Design API interface",
        priority=TaskPriority.MEDIUM
    ))
    print(f"   Added subtask: {subtask.id}")
    
    subtasks = await manager.get_subtasks(task1.id)
    print(f"   Subtasks count: {len(subtasks)}")
    
    # Test 5: Add dependency
    print("\n5. Adding dependency...")
    await manager.add_dependency(task3.id, task1.id)
    print(f"   Task3 now depends on task1")
    
    # Test 6: Get statistics
    print("\n6. Getting statistics...")
    stats = await manager.get_statistics()
    print(f"   Total: {stats['total']}")
    print(f"   By status: {stats['by_status']}")
    print(f"   By priority: {stats['by_priority']}")
    
    # Test 7: Task tree
    print("\n7. Getting task tree...")
    tree = await manager.get_task_tree()
    print(f"   Root tasks: {len(tree['tasks'])}")
    
    # Test 8: Complete task
    print("\n8. Completing task...")
    completed = await manager.complete_task(task1.id)
    print(f"   Completed: {completed.status}, at: {completed.completed_at}")
    
    # Test 9: Queue status
    print("\n9. Getting queue status...")
    queue_status = await manager.get_queue_status()
    print(f"   Queue: {queue_status}")
    
    # Test 10: Delete task
    print("\n10. Deleting task...")
    deleted = await manager.delete_task(task2.id)
    print(f"   Deleted: {deleted}")
    
    remaining = await manager.list_tasks()
    print(f"   Remaining tasks: {len(remaining)}")
    
    # Cleanup
    await manager.shutdown()
    print("\n=== Tests Passed ===")


if __name__ == "__main__":
    asyncio.run(test_todo_manager())