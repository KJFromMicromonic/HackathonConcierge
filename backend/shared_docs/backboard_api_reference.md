# Backboard SDK — API Reference and Error Handling

This document covers the REST API reference for developers using the API directly (e.g. from another language or when the SDK is not used), the complete client method quick reference, and error handling best practices.

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

## Complete Example: Simple Chat Application

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

---

## REST API Reference

This section is for developers using the REST API directly (e.g. from another language or when the SDK is not used). The Python SDK wraps these endpoints.

### REST API Quick Reference

| Area | Method | Path |
|------|--------|------|
| **Assistants** | POST | `/assistants` |
| | GET | `/assistants`, `/assistants/{id}` |
| | PATCH | `/assistants/{id}` |
| | DELETE | `/assistants/{id}` |
| | POST | `/assistants/{id}/threads` |
| | GET | `/assistants/{id}/threads` |
| | GET | `/assistants/{id}/documents` |
| | POST | `/assistants/{id}/documents` (multipart) |
| **Threads** | GET | `/threads`, `/threads/{id}` |
| | DELETE | `/threads/{id}` |
| | POST | `/threads/{id}/messages` (form/multipart) |
| | POST | `/threads/{id}/tool_outputs` (see API docs) |
| | GET | `/threads/{id}/documents` |
| | POST | `/threads/{id}/documents` (multipart) |
| **Documents** | GET | `/documents/{id}/status` |
| | DELETE | `/documents/{id}` |
| **Memories** | GET | `/assistants/{id}/memories` |
| | POST | `/assistants/{id}/memories` |
| | GET | `/assistants/{id}/memories/{mem_id}` |
| | PATCH | `/assistants/{id}/memories/{mem_id}` |
| | DELETE | `/assistants/{id}/memories/{mem_id}` |
| | GET | `/assistants/{id}/memories/stats` |
| | GET | `/assistants/{id}/memories/operations/{op_id}` |
| **Models** | GET | `/models`, `/models/providers`, `/models/embedding`, etc. |

### Add Message (REST)

**Endpoint:** `POST /threads/{thread_id}/messages`
**Content-Type:** `application/x-www-form-urlencoded` (or `multipart/form-data` when attaching files)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `content` | string | — | User message text. |
| `stream` | boolean | `false` | If `true`, response is Server-Sent Events (SSE) stream. |
| `memory` | string | `"off"` | `"Auto"` \| `"Readonly"` \| `"off"`. |
| `llm_provider` | string | `"openai"` | e.g. `openai`, `anthropic`, `google`, `xai`. |
| `model_name` | string | `"gpt-4o"` | Model name for that provider. |
| `web_search` | string | `"off"` | `"Auto"` \| `"off"` (web search tool). |
| `send_to_llm` | string | `"true"` | `"false"` = store message only, no LLM reply. |
| `metadata` | string | — | Optional JSON string. |
| `files` | binary[] | — | Optional file attachments (multipart). |

**Non-streaming response (JSON):** `message`, `thread_id`, `content`, `message_id`, `role`, `status`, `tool_calls`, `run_id`, `memory_operation_id`, `retrieved_memories`, `retrieved_files`, `model_provider`, `model_name`, `input_tokens`, `output_tokens`, `total_tokens`, `created_at`, `attachments`, `timestamp`.

**Message status:** `IN_PROGRESS` | `REQUIRES_ACTION` | `COMPLETED` | `FAILED` | `CANCELLED`. When `REQUIRES_ACTION`, submit tool outputs then continue.

**Supported attachment types (examples):** `.pdf`, `.doc(x)`, `.ppt(x)`, `.xls(x)`, `.txt`, `.csv`, `.md`, `.json`, `.xml`, `.py`, `.js`, `.ts`, `.html`, `.png`, `.jpg`. See the [Add Message API reference](https://backboard-docs.docsalot.dev/api-reference/threads/add-message.md) for the full list.

### Streaming (REST / SSE)

When `stream=true`, the response is **Server-Sent Events** (`text/event-stream`). Each event is a line `data: <json>`; events are separated by double newline. Terminator: `data: [DONE]`.

| Event `type` | Meaning | Typical fields |
|--------------|---------|----------------|
| `content_streaming` | One chunk of assistant text | `content` (string) |
| `message_complete` | End of message; may include usage | Full message / `total_tokens` etc. |
| `run_started` | Processing began | `run_id` |
| `run_ended` | Processing complete | `status` |
| `error` | Error occurred | `error`, `message` |
| `run_failed` | Run failed | `error`, `message` |
| `tool_calls` | Tool calls (when status is `REQUIRES_ACTION`) | `tool_calls`, `run_id` |

Parse by reading line-by-line, accumulating a buffer until `\n\n`; for each line starting with `data: `, parse the JSON (or treat `[DONE]` as end of stream).

---

## Quick Reference — Client Methods

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
