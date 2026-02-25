# Backboard SDK — Assistants

Assistants are the core entities in Backboard that define AI behavior, tools, and embedding configuration. Each assistant can have its own system prompt, tools, and document knowledge base.

---

## Create an Assistant

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

---

## Assistant Model Properties

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

---

## Assistant Operations

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
