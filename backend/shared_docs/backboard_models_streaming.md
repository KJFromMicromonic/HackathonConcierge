# Backboard SDK — Models, Streaming, and Tool Calling

Backboard supports **1,800+ LLMs** across all major providers, streaming for real-time response delivery, and function/tool calling for building agentic AI applications.

---

## Models & Providers

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
        # Handle tool calls (see Tool Calling section above)
        pass
```

---

## Complete Example: Multi-Tool Agent

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
