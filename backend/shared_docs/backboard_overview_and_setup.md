# Backboard SDK — Overview and Setup

A comprehensive guide to getting started with the Backboard SDK for building conversational AI applications with persistent memory and intelligent document processing.

**Version:** 1.4.11
**License:** MIT
**Python:** 3.8+
**Website:** [backboard.io](https://backboard.io)

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

## REST API Base & Authentication

You can call Backboard with any HTTP client; the SDK uses the same API under the hood.

- **Base URL:** `https://app.backboard.io/api`
- **Authentication:** Header `X-API-Key: <your_api_key>`
- **API key:** Create in [Dashboard](https://app.backboard.io/) → Settings → API Keys

```http
GET https://app.backboard.io/api/assistants
X-API-Key: your_api_key
```

All REST endpoints in this document are relative to the base URL and require the `X-API-Key` header.

---

## Sources

- [Backboard.io](https://backboard.io) - Official Website
- [PyPI - backboard-sdk](https://pypi.org/project/backboard-sdk/) - Package Repository
- SDK Source Code (v1.4.11) - Analyzed from installed package
