# Backboard SDK Documentation

A comprehensive guide to the Backboard SDK - a Python SDK for building conversational AI applications with persistent memory and intelligent document processing.

**Version:** 1.4.11
**License:** MIT
**Python:** 3.8+
**Website:** [backboard.io](https://backboard.io)

---

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Client Initialization](#client-initialization)
4. [Assistants](#assistants)
5. [Threads](#threads)
6. [Messages & Conversations](#messages--conversations)
7. [Memory System](#memory-system)
8. [RAG & Document Processing](#rag--document-processing)
9. [Models & Providers](#models--providers)
10. [Tool Calling](#tool-calling)
11. [Streaming](#streaming)
12. [Error Handling](#error-handling)
13. [Complete Examples](#complete-examples)

---

## Overview

Backboard positions itself as "The World's Smartest AI Memory" - a One Stop Shop for the entire AI Stack. Unlike traditional RAG systems that focus solely on document lookup, Backboard layers stateful threads and persistent memory on top, maintaining continuity across tasks and conversations.

### Key Differentiators

| Feature | Traditional RAG | Backboard |
|---------|----------------|-----------|
| Document Retrieval | Yes | Yes |
| Persistent Memory | No | Yes |
| Stateful Threads | No | Yes |
| Cross-Model Portability | No | Yes |
| Memory CRUD Operations | No | Yes |

### Core Capabilities

- **1,800+ LLMs** supported across major providers
- **Persistent Memory** that survives across sessions
- **Intelligent Document Processing** with automatic indexing
- **Configurable Embeddings** from multiple providers
- **Tool/Function Calling** for agentic workflows
- **Streaming Support** for real-time responses

---

## Installation

```bash
pip install backboard-sdk
```

**Dependencies:**
- `httpx >= 0.27.0`
- `pydantic`

---

## Client Initialization

The `BackboardClient` is an **async-only** client that handles all API communication.

```python
from backboard import BackboardClient

# Basic initialization
client = BackboardClient(api_key="YOUR_API_KEY")

# With custom configuration
client = BackboardClient(
    api_key="YOUR_API_KEY",
    base_url="https://app.backboard.io/api",  # Default
    timeout=30  # Request timeout in seconds
)

# Using as context manager (recommended for proper cleanup)
async with BackboardClient(api_key="YOUR_API_KEY") as client:
    # Your code here
    pass

# Manual cleanup
await client.aclose()
```

### Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | str | Required | Your Backboard API key |
| `base_url` | str | `https://app.backboard.io/api` | API base URL |
| `timeout` | int | 30 | Request timeout in seconds |

---

## Assistants

Assistants are the core entities that define AI behavior, tools, and embedding configuration. Each assistant can have its own system prompt, tools, and document knowledge base.

### Create an Assistant

```python
from backboard import BackboardClient

async def create_assistant():
    client = BackboardClient(api_key="YOUR_API_KEY")

    assistant = await client.create_assistant(
        name="My Assistant",
        description="A helpful assistant for customer support",  # Optional
        tools=[...],  # Optional - list of tool definitions
        embedding_provider="openai",  # Optional
        embedding_model_name="text-embedding-3-small",  # Optional
        embedding_dims=1536  # Optional
    )

    print(f"Assistant ID: {assistant.assistant_id}")
    print(f"Name: {assistant.name}")
    print(f"Created: {assistant.created_at}")
```

### Assistant Model Properties

```python
class Assistant:
    assistant_id: uuid.UUID        # Unique identifier
    name: str                      # Assistant name
    description: Optional[str]     # Description
    system_prompt: Optional[str]   # System instructions
    tools: Optional[List[ToolDefinition]]  # Configured tools
    tok_k: Optional[int]           # Top-k retrieval setting
    embedding_provider: Optional[str]      # e.g., "openai", "cohere"
    embedding_model_name: Optional[str]    # Model for embeddings
    embedding_dims: Optional[int]          # Embedding dimensions
    created_at: datetime           # Creation timestamp
```

### Assistant Operations

```python
# List all assistants
assistants = await client.list_assistants(skip=0, limit=100)

# Get a specific assistant
assistant = await client.get_assistant(assistant_id)

# Update an assistant
updated = await client.update_assistant(
    assistant_id=assistant_id,
    name="New Name",
    description="Updated description",
    tools=[...]
)

# Delete an assistant
result = await client.delete_assistant(assistant_id)
```

---

## Threads

Threads represent conversation sessions with persistent history. Each thread belongs to an assistant and maintains the full conversation context.

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

Messages are the core of conversational interactions. Backboard handles message history, context retrieval, and AI responses.

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

---

## Memory System

Backboard's memory system provides **persistent, long-term storage** that survives across conversations and sessions. This is a key differentiator from traditional RAG systems.

### Memory Architecture

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

### Memory Model

```python
class Memory:
    id: str                        # Unique identifier
    content: str                   # Memory content
    metadata: Optional[Dict]       # Custom metadata
    score: Optional[float]         # Relevance score (when retrieved)
    created_at: Optional[str]      # Creation timestamp
    updated_at: Optional[str]      # Last update timestamp
```

### Memory CRUD Operations

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

### Memory Statistics

```python
stats = await client.get_memory_stats(assistant_id)

print(f"Total Memories: {stats.total_memories}")
print(f"Last Updated: {stats.last_updated}")
print(f"Limits: {stats.limits}")
```

### How Memory Works in Conversations

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

## RAG & Document Processing

Backboard provides intelligent document processing with automatic chunking, indexing, and retrieval for RAG (Retrieval-Augmented Generation).

### Supported Document Types

| Category | Extensions |
|----------|------------|
| PDF | `.pdf` |
| Office | `.docx`, `.xlsx`, `.pptx` |
| Text | `.txt`, `.md`, `.csv` |
| Code | `.py`, `.js`, `.ts`, `.java`, etc. |
| Data | `.json`, `.xml`, `.yaml` |

### Document Model

```python
class Document:
    document_id: uuid.UUID
    filename: str
    status: DocumentStatus         # pending/processing/indexed/failed
    created_at: datetime
    status_message: Optional[str]
    summary: Optional[str]         # Auto-generated summary
    updated_at: Optional[datetime]
    file_size_bytes: Optional[int]
    total_tokens: Optional[int]
    chunk_count: Optional[int]
    processing_started_at: Optional[datetime]
    processing_completed_at: Optional[datetime]
    document_type: Optional[str]
    metadata_: Optional[Dict]

class DocumentStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"
```

### Upload Documents

Documents can be uploaded at two levels:

**Assistant-Level Documents** (shared across all threads):

```python
# Upload to assistant (available to all threads)
document = await client.upload_document_to_assistant(
    assistant_id=assistant_id,
    file_path="./company_handbook.pdf"
)

print(f"Document ID: {document.document_id}")
print(f"Status: {document.status}")
```

**Thread-Level Documents** (specific to one conversation):

```python
# Upload to specific thread
document = await client.upload_document_to_thread(
    thread_id=thread_id,
    file_path="./meeting_notes.docx"
)
```

### Document Processing Pipeline

```
┌──────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐
│  UPLOAD  │───▶│  PROCESSING  │───▶│   CHUNKING   │───▶│ INDEXING │
│          │    │              │    │              │    │          │
│ .pdf     │    │ Parse text   │    │ Split into   │    │ Generate │
│ .docx    │    │ Extract      │    │ semantic     │    │ embed-   │
│ .xlsx    │    │ structure    │    │ chunks       │    │ dings    │
└──────────┘    └──────────────┘    └──────────────┘    └──────────┘
                                                              │
                                                              ▼
┌──────────────────────────────────────────────────────────────────┐
│                       VECTOR STORE                               │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐            │
│  │ Chunk 1 │  │ Chunk 2 │  │ Chunk 3 │  │ Chunk N │    ...     │
│  │ [emb]   │  │ [emb]   │  │ [emb]   │  │ [emb]   │            │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘            │
└──────────────────────────────────────────────────────────────────┘
```

### Monitor Document Status

```python
import asyncio

async def wait_for_indexing(client, document_id):
    while True:
        doc = await client.get_document_status(document_id)
        print(f"Status: {doc.status}")

        if doc.status == DocumentStatus.INDEXED:
            print(f"Indexed! Chunks: {doc.chunk_count}")
            return doc
        elif doc.status == DocumentStatus.FAILED:
            raise Exception(f"Processing failed: {doc.status_message}")

        await asyncio.sleep(2)
```

### Document Operations

```python
# List assistant documents
docs = await client.list_assistant_documents(assistant_id)

# List thread documents
docs = await client.list_thread_documents(thread_id)

# Get document status
doc = await client.get_document_status(document_id)

# Delete document
result = await client.delete_document(document_id)
```

### How RAG Works in Conversations

When you send a message, Backboard automatically:

1. Converts your query to embeddings
2. Searches the vector store for relevant chunks
3. Injects retrieved context into the prompt
4. Generates a response with citations

```python
response = await client.add_message(
    thread_id=thread_id,
    content="What does the handbook say about vacation policy?"
)

# Check which files were used
if response.retrieved_files:
    print("Sources used:")
    for file in response.retrieved_files:
        print(f"  - {file}")
```

---

## Models & Providers

Backboard supports **1,800+ LLMs** across all major providers, giving you flexibility to choose the best model for each use case.

### Supported Providers

| Provider | Example Models |
|----------|---------------|
| **OpenAI** | `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `o1`, `o1-mini` |
| **Anthropic** | `claude-3-5-sonnet`, `claude-3-opus`, `claude-3-haiku` |
| **Google** | `gemini-1.5-pro`, `gemini-1.5-flash`, `gemini-2.0` |
| **Cohere** | `command-r-plus`, `command-r` |
| **Mistral** | `mistral-large`, `mixtral-8x7b` |
| **Meta** | `llama-3.1-405b`, `llama-3.1-70b` |
| And more... | 1,800+ models |

### Specifying Models

```python
# Use OpenAI
response = await client.add_message(
    thread_id=thread_id,
    content="Explain quantum entanglement",
    llm_provider="openai",
    model_name="gpt-4o"
)

# Use Anthropic
response = await client.add_message(
    thread_id=thread_id,
    content="Write a poem about AI",
    llm_provider="anthropic",
    model_name="claude-3-5-sonnet-20241022"
)

# Use Google
response = await client.add_message(
    thread_id=thread_id,
    content="Summarize this document",
    llm_provider="google",
    model_name="gemini-1.5-pro"
)
```

### Embedding Providers

For document indexing and memory, you can configure embedding models:

```python
assistant = await client.create_assistant(
    name="Custom Embeddings Assistant",
    embedding_provider="openai",           # or "google", "cohere"
    embedding_model_name="text-embedding-3-large",
    embedding_dims=3072
)
```

| Provider | Models | Dimensions |
|----------|--------|------------|
| OpenAI | `text-embedding-3-small`, `text-embedding-3-large` | 1536, 3072 |
| Google | `text-embedding-004` | 768 |
| Cohere | `embed-english-v3.0`, `embed-multilingual-v3.0` | 1024 |

### Cross-Model Portability

A key advantage of Backboard is that your threads, memory, and documents work across ANY model:

```python
# Start conversation with GPT-4
await client.add_message(thread_id, "Hello!", llm_provider="openai", model_name="gpt-4o")

# Continue with Claude (same thread, same context!)
await client.add_message(thread_id, "Continue our discussion", llm_provider="anthropic", model_name="claude-3-5-sonnet-20241022")

# Switch to Gemini for a specific task
await client.add_message(thread_id, "Now summarize everything", llm_provider="google", model_name="gemini-1.5-pro")
```

---

## Tool Calling

Backboard supports function/tool calling for building agentic AI applications.

### Define Tools

```python
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get current weather for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name, e.g., 'San Francisco'"
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "description": "Temperature unit"
                }
            },
            "required": ["location"]
        }
    }
}]

# Create assistant with tools
assistant = await client.create_assistant(
    name="Weather Assistant",
    description="An assistant that can check the weather",
    tools=tools
)
```

### Handle Tool Calls

```python
import json

async def handle_conversation_with_tools(client, thread_id, user_message):
    response = await client.add_message(
        thread_id=thread_id,
        content=user_message,
        stream=False
    )

    # Check if assistant wants to call tools
    if response.status == "REQUIRES_ACTION" and response.tool_calls:
        tool_outputs = []

        for tool_call in response.tool_calls:
            func_name = tool_call.function.name
            args = tool_call.function.parsed_arguments  # Auto-parsed dict

            # Execute the function
            if func_name == "get_weather":
                result = get_weather(args["location"], args.get("unit", "celsius"))
            else:
                result = {"error": f"Unknown function: {func_name}"}

            tool_outputs.append({
                "tool_call_id": tool_call.id,
                "output": json.dumps(result)
            })

        # Submit tool outputs to continue
        final_response = await client.submit_tool_outputs(
            thread_id=thread_id,
            run_id=response.run_id,
            tool_outputs=tool_outputs,
            stream=False
        )

        return final_response.content

    return response.content

# Mock function implementation
def get_weather(location, unit="celsius"):
    return {
        "location": location,
        "temperature": 22 if unit == "celsius" else 72,
        "unit": unit,
        "condition": "Sunny"
    }
```

### Tool Call Models

```python
class ToolCall:
    id: str                        # Unique call identifier
    type: str                      # "function"
    function: ToolCallFunction

class ToolCallFunction:
    name: str                      # Function name
    arguments: str                 # Raw JSON string
    parsed_arguments: Dict         # Auto-parsed (computed property)
```

---

## Streaming

Backboard supports streaming for real-time response delivery.

### Basic Streaming

```python
async def stream_response(client, thread_id, content):
    stream = await client.add_message(
        thread_id=thread_id,
        content=content,
        stream=True
    )

    full_response = ""
    async for event in stream:
        event_type = event.get("type")

        if event_type == "content_delta":
            # Incremental content
            delta = event.get("delta", "")
            print(delta, end="", flush=True)
            full_response += delta

        elif event_type == "message_complete":
            # Final message data
            print("\n--- Complete ---")
            print(f"Tokens: {event.get('total_tokens')}")

        elif event_type == "error":
            print(f"Error: {event.get('error')}")

        elif event_type == "run_failed":
            print(f"Run failed: {event.get('message')}")

    return full_response
```

### Stream Event Types

| Event Type | Description | Fields |
|------------|-------------|--------|
| `content_delta` | Incremental content chunk | `delta` |
| `message_complete` | Response finished | Full message data |
| `run_started` | Processing began | `run_id` |
| `run_ended` | Processing complete | `status` |
| `error` | Error occurred | `error`, `message` |
| `run_failed` | Run failed | `error`, `message` |

### Streaming with Tool Calls

```python
async def stream_with_tools(client, thread_id, content):
    stream = await client.add_message(
        thread_id=thread_id,
        content=content,
        stream=True
    )

    tool_calls = []
    run_id = None

    async for event in stream:
        if event.get("type") == "content_delta":
            print(event.get("delta", ""), end="", flush=True)

        elif event.get("type") == "tool_calls":
            tool_calls = event.get("tool_calls", [])
            run_id = event.get("run_id")

        elif event.get("status") == "REQUIRES_ACTION":
            # Process tool calls and submit outputs
            break

    if tool_calls:
        # Handle tool calls (see Tool Calling section)
        pass
```

---

## Error Handling

Backboard provides specific exception types for different error scenarios.

### Exception Hierarchy

```python
BackboardError                    # Base exception
├── BackboardAPIError             # General API errors
│   ├── BackboardValidationError  # 400 - Bad request
│   ├── BackboardNotFoundError    # 404 - Resource not found
│   ├── BackboardRateLimitError   # 429 - Rate limit exceeded
│   └── BackboardServerError      # 5xx - Server errors
```

### Exception Properties

```python
try:
    response = await client.add_message(...)
except BackboardAPIError as e:
    print(f"Error: {e}")
    print(f"Status Code: {e.status_code}")
    print(f"Response: {e.response}")
```

### Best Practices

```python
from backboard import (
    BackboardClient,
    BackboardValidationError,
    BackboardNotFoundError,
    BackboardRateLimitError,
    BackboardServerError,
    BackboardAPIError
)
import asyncio

async def robust_message(client, thread_id, content, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await client.add_message(
                thread_id=thread_id,
                content=content
            )

        except BackboardValidationError as e:
            # Don't retry validation errors
            raise e

        except BackboardNotFoundError as e:
            # Resource doesn't exist
            raise e

        except BackboardRateLimitError as e:
            # Wait and retry
            wait_time = 2 ** attempt
            print(f"Rate limited, waiting {wait_time}s...")
            await asyncio.sleep(wait_time)

        except BackboardServerError as e:
            # Server error, retry with backoff
            wait_time = 2 ** attempt
            print(f"Server error, retrying in {wait_time}s...")
            await asyncio.sleep(wait_time)

        except BackboardAPIError as e:
            # Other API errors
            print(f"API error: {e}")
            raise e

    raise Exception("Max retries exceeded")
```

---

## Complete Examples

### Example 1: Simple Chat Application

```python
import asyncio
from backboard import BackboardClient

async def simple_chat():
    async with BackboardClient(api_key="YOUR_API_KEY") as client:
        # Create assistant
        assistant = await client.create_assistant(
            name="Chat Bot",
            description="A friendly chat assistant"
        )

        # Create thread
        thread = await client.create_thread(assistant.assistant_id)

        # Chat loop
        while True:
            user_input = input("You: ")
            if user_input.lower() in ['quit', 'exit']:
                break

            response = await client.add_message(
                thread_id=thread.thread_id,
                content=user_input,
                llm_provider="openai",
                model_name="gpt-4o"
            )

            print(f"Assistant: {response.content}\n")

if __name__ == "__main__":
    asyncio.run(simple_chat())
```

### Example 2: Document Q&A with RAG

```python
import asyncio
from backboard import BackboardClient, DocumentStatus

async def document_qa():
    async with BackboardClient(api_key="YOUR_API_KEY") as client:
        # Create assistant
        assistant = await client.create_assistant(
            name="Document Expert",
            description="An assistant that answers questions about documents"
        )

        # Upload documents
        doc = await client.upload_document_to_assistant(
            assistant_id=assistant.assistant_id,
            file_path="./company_handbook.pdf"
        )

        # Wait for indexing
        while True:
            status = await client.get_document_status(doc.document_id)
            if status.status == DocumentStatus.INDEXED:
                print(f"Document indexed: {status.chunk_count} chunks")
                break
            elif status.status == DocumentStatus.FAILED:
                raise Exception(f"Indexing failed: {status.status_message}")
            await asyncio.sleep(2)

        # Create thread and ask questions
        thread = await client.create_thread(assistant.assistant_id)

        questions = [
            "What is the vacation policy?",
            "How do I submit expense reports?",
            "What are the working hours?"
        ]

        for question in questions:
            response = await client.add_message(
                thread_id=thread.thread_id,
                content=question,
                llm_provider="openai",
                model_name="gpt-4o"
            )

            print(f"Q: {question}")
            print(f"A: {response.content}")
            if response.retrieved_files:
                print(f"Sources: {response.retrieved_files}")
            print()

if __name__ == "__main__":
    asyncio.run(document_qa())
```

### Example 3: Personal Assistant with Memory

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

### Example 4: Multi-Tool Agent

```python
import asyncio
import json
from backboard import BackboardClient

# Tool definitions
tools = [
    {
        "type": "function",
        "function": {
            "name": "search_database",
            "description": "Search the product database",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "category": {"type": "string", "enum": ["electronics", "clothing", "home"]}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_inventory",
            "description": "Check inventory for a product",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Product ID"}
                },
                "required": ["product_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "place_order",
            "description": "Place an order for a product",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string"},
                    "quantity": {"type": "integer"}
                },
                "required": ["product_id", "quantity"]
            }
        }
    }
]

# Mock function implementations
def search_database(query, category=None):
    return [
        {"id": "PROD001", "name": f"{query} - Premium", "price": 99.99},
        {"id": "PROD002", "name": f"{query} - Basic", "price": 49.99}
    ]

def get_inventory(product_id):
    return {"product_id": product_id, "in_stock": 42, "warehouse": "West"}

def place_order(product_id, quantity):
    return {"order_id": "ORD12345", "product_id": product_id, "quantity": quantity, "status": "confirmed"}

async def agent_loop(client, thread_id, user_message):
    response = await client.add_message(
        thread_id=thread_id,
        content=user_message,
        stream=False
    )

    # Handle tool calls in a loop
    while response.status == "REQUIRES_ACTION" and response.tool_calls:
        tool_outputs = []

        for tc in response.tool_calls:
            args = tc.function.parsed_arguments

            if tc.function.name == "search_database":
                result = search_database(args["query"], args.get("category"))
            elif tc.function.name == "get_inventory":
                result = get_inventory(args["product_id"])
            elif tc.function.name == "place_order":
                result = place_order(args["product_id"], args["quantity"])
            else:
                result = {"error": "Unknown function"}

            tool_outputs.append({
                "tool_call_id": tc.id,
                "output": json.dumps(result)
            })

        response = await client.submit_tool_outputs(
            thread_id=thread_id,
            run_id=response.run_id,
            tool_outputs=tool_outputs,
            stream=False
        )

    return response.content

async def main():
    async with BackboardClient(api_key="YOUR_API_KEY") as client:
        assistant = await client.create_assistant(
            name="Shopping Agent",
            description="An agent that helps with shopping",
            tools=tools
        )

        thread = await client.create_thread(assistant.assistant_id)

        result = await agent_loop(
            client,
            thread.thread_id,
            "Search for wireless headphones, check inventory on the first result, and order 2 units"
        )

        print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Quick Reference

### Client Methods

| Method | Description |
|--------|-------------|
| `create_assistant()` | Create a new assistant |
| `list_assistants()` | List all assistants |
| `get_assistant()` | Get assistant by ID |
| `update_assistant()` | Update assistant |
| `delete_assistant()` | Delete assistant |
| `create_thread()` | Create conversation thread |
| `list_threads()` | List all threads |
| `list_threads_for_assistant()` | List threads for specific assistant |
| `get_thread()` | Get thread with messages |
| `delete_thread()` | Delete thread |
| `add_message()` | Send message and get response |
| `submit_tool_outputs()` | Submit tool call results |
| `upload_document_to_assistant()` | Upload doc to assistant |
| `upload_document_to_thread()` | Upload doc to thread |
| `list_assistant_documents()` | List assistant docs |
| `list_thread_documents()` | List thread docs |
| `get_document_status()` | Check document status |
| `delete_document()` | Delete document |
| `get_memories()` | List all memories |
| `add_memory()` | Create new memory |
| `get_memory()` | Get memory by ID |
| `update_memory()` | Update memory |
| `delete_memory()` | Delete memory |
| `get_memory_stats()` | Get memory statistics |

---

## Sources

- [Backboard.io](https://backboard.io) - Official Website
- [PyPI - backboard-sdk](https://pypi.org/project/backboard-sdk/) - Package Repository
- SDK Source Code (v1.4.11) - Analyzed from installed package
