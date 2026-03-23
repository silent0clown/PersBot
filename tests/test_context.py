import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.backend.core.context import (
    ContextManager, ContextCompactor, 
    Message, MessageRole, CompressionStrategy
)


async def test_context_compact():
    print("=== Testing Context Compact ===\n")
    
    # Test 1: Basic context management
    print("1. Basic context management...")
    manager = ContextManager(max_tokens=200)
    
    manager.add_user_message("Hello, I need help with coding")
    manager.add_assistant_message("Sure, I'd be happy to help! What do you need?")
    manager.add_user_message("Can you write a function to add two numbers?")
    manager.add_assistant_message("Of course! Here's a simple function:")
    
    context = manager.get_context()
    print(f"   Context length: {len(context)} messages")
    print(f"   Stats: {manager.get_stats()}")
    
    # Test 2: Compression strategies
    print("\n2. Testing compression strategies...")
    
    def mock_summarize(messages):
        return f"Summary of {len(messages)} messages"
    
    compactor = ContextCompactor(
        max_tokens=100, 
        strategy=CompressionStrategy.HYBRID,
        summarize_fn=mock_summarize
    )
    
    for i in range(20):
        compactor.add_message(Message(
            role=MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT,
            content=f"Message {i}: " + "x" * 50,
            importance=1.0 if i % 3 == 0 else 0.5
        ))
    
    print(f"   After 20 messages: {compactor.get_stats()}")
    
    # Test 3: Importance filtering
    print("\n3. Testing importance filtering...")
    compactor2 = ContextCompactor(max_tokens=50, strategy=CompressionStrategy.IMPORTANCE_FILTER)
    
    for i in range(15):
        compactor2.add_message(Message(
            role=MessageRole.USER,
            content=f"Message {i}",
            importance=1.0 if i % 2 == 0 else 0.3
        ))
    
    stats = compactor2.get_stats()
    print(f"   After 15 messages: {stats}")
    print(f"   Messages retained: {stats['message_count']}")
    
    # Test 4: Truncate strategy
    print("\n4. Testing truncate strategy...")
    compactor3 = ContextCompactor(max_tokens=80, strategy=CompressionStrategy.TRUNCATE)
    
    for i in range(10):
        compactor3.add_message(Message(
            role=MessageRole.USER,
            content=f"Long message {i}: " + "content " * 20
        ))
    
    stats = compactor3.get_stats()
    print(f"   After 10 long messages: {stats}")
    
    # Test 5: Tool messages
    print("\n5. Testing tool messages...")
    manager2 = ContextManager(max_tokens=300)
    manager2.add_user_message("Search for Python tutorials")
    manager2.add_tool_message("search", "call_123", "Found 50 Python tutorial results")
    manager2.add_assistant_message("I found some great tutorials for you:")
    
    context = manager2.get_context()
    print(f"   Context: {len(context)} messages")
    print(f"   Has tool message: {any(m['role'] == 'tool' for m in context)}")
    
    # Test 6: Clear and reset
    print("\n6. Testing clear and reset...")
    manager.clear()
    print(f"   After clear: {manager.get_stats()}")
    
    # Test 7: Stats
    print("\n7. Context statistics...")
    manager3 = ContextManager(max_tokens=150, strategy=CompressionStrategy.SLIDING_WINDOW)
    
    for i in range(12):
        manager3.add_user_message(f"Message {i}")
    
    stats = manager3.get_stats()
    print(f"   Stats: {stats}")
    
    print("\n=== Tests Passed ===")


if __name__ == "__main__":
    asyncio.run(test_context_compact())