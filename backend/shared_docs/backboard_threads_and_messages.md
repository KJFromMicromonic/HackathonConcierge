# Backboard SDK — Threads and Messages

Threads represent conversation sessions with persistent history. Each thread belongs to an assistant and maintains the full conversation context. Messages are the core of conversational interactions — Backboard handles message history, context retrieval, and AI responses.

---

## Threads

### Create a Thread

```python
# Create a thread under an assistant
thread = await client.create_thread(assistant_id)

print(f"Thread ID: {thread.thread_id}")
print(f"Created: {thread.created_at}")
print(f"Messages: {len(thread.messages)}")
```

### Thread Model Properties

```python
class Thread:
    thread_id: uuid.UUID           # Unique identifier
    created_at: datetime           # Creation timestamp
    messages: List[Message]        # Conversation history
    metadata_: Optional[Dict]      # Custom metadata
```

### Thread Operations

```python
# List all threads
threads = await client.list_threads(skip=0, limit=100)

# List threads for a specific assistant
threads = await client.list_threads_for_assistant(
    assistant_id=assistant_id,
    skip=0,
    limit=100
)

# Get a specific thread (includes messages)
thread = await client.get_thread(thread_id)

# Delete a thread
result = await client.delete_thread(thread_id)
```

### Thread Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        ASSISTANT                            │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │   Thread 1      │  │   Thread 2      │  ...             │
│  │  ┌───────────┐  │  │  ┌───────────┐  │                  │
│  │  │ Message 1 │  │  │  │ Message 1 │  │                  │
│  │  │ Message 2 │  │  │  │ Message 2 │  │                  │
│  │  │ Message 3 │  │  │  │ ...       │  │                  │
│  │  │ ...       │  │  │  └───────────┘  │                  │
│  │  └───────────┘  │  └─────────────────┘                  │
│  └─────────────────┘                                        │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                    DOCUMENTS (RAG)                    │  │
│  │    doc1.pdf    doc2.docx    data.json    code.py     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                  PERSISTENT MEMORY                    │  │
│  │    memory_1    memory_2    memory_3    ...           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Messages & Conversations

### Send a Message

```python
# Basic message (non-streaming)
response = await client.add_message(
    thread_id=thread.thread_id,
    content="Hello! Tell me about quantum computing.",
    llm_provider="openai",    # Optional - provider choice
    model_name="gpt-4o",      # Optional - model choice
    stream=False,             # Default
    memory="auto"             # Memory mode: "auto", "readonly", or None
)

print(f"Response: {response.content}")
print(f"Model: {response.model_provider}/{response.model_name}")
print(f"Tokens: {response.total_tokens}")
```

### Message Response Properties

```python
class MessageResponse:
    message: str                   # Status message
    thread_id: uuid.UUID           # Thread identifier
    content: Optional[str]         # AI response content
    message_id: Optional[uuid.UUID]
    role: Optional[MessageRole]    # user/assistant/system
    status: Optional[str]          # e.g., "completed", "REQUIRES_ACTION"
    tool_calls: Optional[List[ToolCall]]  # Pending tool calls
    run_id: Optional[str]          # Run identifier for tool handling

    # Memory & RAG
    memory_operation_id: Optional[str]
    retrieved_memories: Optional[List[Dict]]  # Memories used
    retrieved_files: Optional[List[str]]      # Documents retrieved

    # Token usage
    model_provider: Optional[str]
    model_name: Optional[str]
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    total_tokens: Optional[int]

    # Timestamps
    created_at: Optional[datetime]
    timestamp: datetime

    # Attachments
    attachments: Optional[List[AttachmentInfo]]
```

### Message with File Attachments

```python
# Send message with files for immediate context
response = await client.add_message(
    thread_id=thread.thread_id,
    content="Summarize this document",
    files=["./report.pdf", "./data.xlsx"],
    stream=False
)
```

### Memory Modes

The `memory` parameter controls how the assistant interacts with persistent memory:

| Mode | Description |
|------|-------------|
| `"auto"` | Search existing memories AND write new ones |
| `"readonly"` | Search existing memories only (no writes) |
| `None` | Disable memory for this message |

```python
# Auto mode - full memory capabilities
response = await client.add_message(
    thread_id=thread_id,
    content="My favorite color is blue. Remember that.",
    memory="auto"
)

# Readonly mode - use memories but don't create new ones
response = await client.add_message(
    thread_id=thread_id,
    content="What's my favorite color?",
    memory="readonly"
)
```
