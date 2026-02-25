# Backboard SDK — RAG & Document Processing

Backboard provides intelligent document processing with automatic chunking, indexing, and retrieval for RAG (Retrieval-Augmented Generation).

---

## Supported Document Types

| Category | Extensions |
|----------|------------|
| PDF | `.pdf` |
| Office | `.docx`, `.xlsx`, `.pptx` |
| Text | `.txt`, `.md`, `.csv` |
| Code | `.py`, `.js`, `.ts`, `.java`, etc. |
| Data | `.json`, `.xml`, `.yaml` |

---

## Document Model

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

---

## Upload Documents

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

---

## Document Processing Pipeline

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

---

## Monitor Document Status

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

---

## Document Operations

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

---

## How RAG Works in Conversations

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

## Complete Example: Document Q&A with RAG

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
