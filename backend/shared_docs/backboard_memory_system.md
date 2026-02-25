# Backboard SDK — Memory System

Backboard's memory system provides **persistent, long-term storage** that survives across conversations and sessions. This is a key differentiator from traditional RAG systems.

---

## Memory Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     MEMORY SYSTEM                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐    ┌──────────────────────────────┐  │
│  │  ADD MEMORY      │    │  MEMORY STORAGE              │  │
│  │  ─────────────   │───▶│  ┌────────────────────────┐  │  │
│  │  content: str    │    │  │ ID: mem_abc123         │  │  │
│  │  metadata: dict  │    │  │ Content: "User prefers │  │  │
│  └──────────────────┘    │  │          dark mode"    │  │  │
│                          │  │ Metadata: {type: pref} │  │  │
│  ┌──────────────────┐    │  │ Score: 0.95            │  │  │
│  │  AUTO RETRIEVAL  │◀───│  │ Created: 2026-02-04    │  │  │
│  │  ─────────────   │    │  └────────────────────────┘  │  │
│  │  Semantic search │    │                              │  │
│  │  during messages │    │  ┌────────────────────────┐  │  │
│  └──────────────────┘    │  │ ID: mem_def456         │  │  │
│                          │  │ Content: "..."         │  │  │
│                          │  └────────────────────────┘  │  │
│                          └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Memory Model

```python
class Memory:
    id: str                        # Unique identifier
    content: str                   # Memory content
    metadata: Optional[Dict]       # Custom metadata
    score: Optional[float]         # Relevance score (when retrieved)
    created_at: Optional[str]      # Creation timestamp
    updated_at: Optional[str]      # Last update timestamp
```

---

## Memory CRUD Operations

```python
# CREATE - Add a new memory
result = await client.add_memory(
    assistant_id=assistant_id,
    content="User's name is John and he prefers dark mode",
    metadata={"type": "user_preference", "category": "ui"}
)
print(f"Memory ID: {result['memory_id']}")

# READ - Get all memories
memories_response = await client.get_memories(assistant_id)
for memory in memories_response.memories:
    print(f"[{memory.id}] {memory.content}")
print(f"Total: {memories_response.total_count}")

# READ - Get a specific memory
memory = await client.get_memory(assistant_id, memory_id)

# UPDATE - Modify a memory
updated_memory = await client.update_memory(
    assistant_id=assistant_id,
    memory_id=memory_id,
    content="User's name is John, prefers dark mode, and lives in NYC",
    metadata={"type": "user_preference", "updated": True}
)

# DELETE - Remove a memory
result = await client.delete_memory(assistant_id, memory_id)
```

---

## Memory Statistics

```python
stats = await client.get_memory_stats(assistant_id)

print(f"Total Memories: {stats.total_memories}")
print(f"Last Updated: {stats.last_updated}")
print(f"Limits: {stats.limits}")
```

---

## How Memory Works in Conversations

When you send a message with `memory="auto"`:

1. **Retrieval Phase**: Backboard searches existing memories using semantic similarity
2. **Context Injection**: Relevant memories are injected into the AI's context
3. **Response Generation**: AI responds with memory-informed context
4. **Memory Writing**: New important information is automatically saved

```python
# Memories are automatically retrieved and used
response = await client.add_message(
    thread_id=thread_id,
    content="What do you know about me?",
    memory="auto"
)

# Check which memories were retrieved
if response.retrieved_memories:
    print("Retrieved memories:")
    for mem in response.retrieved_memories:
        print(f"  - {mem}")
```

---

## Complete Example: Personal Assistant with Memory

```python
import asyncio
from backboard import BackboardClient

async def personal_assistant():
    async with BackboardClient(api_key="YOUR_API_KEY") as client:
        # Create assistant with memory
        assistant = await client.create_assistant(
            name="Personal Assistant",
            description="An assistant that remembers your preferences"
        )

        # Pre-seed some memories
        await client.add_memory(
            assistant_id=assistant.assistant_id,
            content="User's name is Alex",
            metadata={"type": "identity"}
        )

        await client.add_memory(
            assistant_id=assistant.assistant_id,
            content="User prefers concise answers",
            metadata={"type": "preference"}
        )

        # Create thread
        thread = await client.create_thread(assistant.assistant_id)

        # Conversation with memory
        messages = [
            "Hi! What's my name?",
            "I'm working on a Python project",
            "My favorite framework is FastAPI",
            "What do you remember about my project?"
        ]

        for msg in messages:
            response = await client.add_message(
                thread_id=thread.thread_id,
                content=msg,
                memory="auto",  # Enable memory
                llm_provider="openai",
                model_name="gpt-4o"
            )

            print(f"User: {msg}")
            print(f"Assistant: {response.content}")

            if response.retrieved_memories:
                print(f"  [Used {len(response.retrieved_memories)} memories]")
            print()

        # Check memory stats
        stats = await client.get_memory_stats(assistant.assistant_id)
        print(f"\nTotal memories: {stats.total_memories}")

if __name__ == "__main__":
    asyncio.run(personal_assistant())
```
