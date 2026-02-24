# backend/scripts/upload_docs.py
"""
Script to upload SDK documentation and hackathon content to Backboard RAG.
Run this once after setting up your Backboard assistant.

Usage:
    cd backend
    python scripts/upload_docs.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from backboard import BackboardClient, DocumentStatus

load_dotenv()


async def upload_documents():
    """Upload all documentation to Backboard for RAG."""

    api_key = os.getenv("BACKBOARD_API_KEY")
    assistant_id = os.getenv("BACKBOARD_ASSISTANT_ID")

    if not api_key:
        print("❌ BACKBOARD_API_KEY not set in .env")
        return

    if not assistant_id:
        print("❌ BACKBOARD_ASSISTANT_ID not set in .env")
        print("   Create an assistant first, then add the ID to .env")
        return

    client = BackboardClient(api_key=api_key)

    # Document paths relative to project root
    project_root = Path(__file__).parent.parent.parent
    docs_dir = project_root / "docs"

    doc_files = [
        # SDK Documentation (created by Claude)
        docs_dir / "BACKBOARD_SDK_DOCUMENTATION.md",
        docs_dir / "SPEECHMATICS_DOCUMENTATION.md",

        # Hackathon content
        docs_dir / "rag_content" / "schedule.md",
        docs_dir / "rag_content" / "sponsors.md",
        docs_dir / "rag_content" / "faq.md",
    ]

    print(f"📚 Uploading documents to assistant: {assistant_id}\n")

    successful = 0
    failed = 0

    for doc_path in doc_files:
        if not doc_path.exists():
            print(f"⚠️  Skipping {doc_path.name} - file not found at {doc_path}")
            continue

        print(f"📤 Uploading {doc_path.name}...")

        try:
            # Upload document
            doc = await client.upload_document_to_assistant(
                assistant_id=assistant_id,
                file_path=str(doc_path)
            )
            print(f"   Document ID: {doc.document_id}")

            # Wait for indexing with timeout
            max_wait = 120  # 2 minutes
            waited = 0

            while waited < max_wait:
                status = await client.get_document_status(doc.document_id)

                if status.status == DocumentStatus.INDEXED:
                    print(f"   ✅ Indexed! Chunks: {status.chunk_count}, Tokens: {status.total_tokens}")
                    successful += 1
                    break
                elif status.status == DocumentStatus.FAILED:
                    print(f"   ❌ Failed: {status.status_message}")
                    failed += 1
                    break
                else:
                    print(f"   ⏳ Status: {status.status.value}...")
                    await asyncio.sleep(3)
                    waited += 3
            else:
                print(f"   ⚠️  Timeout waiting for indexing")
                failed += 1

        except Exception as e:
            print(f"   ❌ Error: {e}")
            failed += 1

        print()  # Blank line between documents

    # Summary
    print("=" * 50)
    print(f"📊 Upload Summary:")
    print(f"   ✅ Successful: {successful}")
    print(f"   ❌ Failed: {failed}")
    print()

    # List all documents
    print("📚 All documents in assistant:")
    try:
        docs = await client.list_assistant_documents(assistant_id)
        for doc in docs:
            status_emoji = "✅" if doc.status == DocumentStatus.INDEXED else "⏳"
            print(f"   {status_emoji} {doc.filename}: {doc.status.value}")
            if doc.summary:
                print(f"      Summary: {doc.summary[:100]}...")
    except Exception as e:
        print(f"   Error listing documents: {e}")

    await client.aclose()
    print("\n✨ Done!")


async def create_assistant_if_needed():
    """Helper to create an assistant if one doesn't exist."""

    api_key = os.getenv("BACKBOARD_API_KEY")
    if not api_key:
        print("❌ BACKBOARD_API_KEY not set")
        return

    client = BackboardClient(api_key=api_key)

    system_prompt = """You are AURA, the AI assistant for the Activate Your Voice hackathon. You are knowledgeable about:

1. **Backboard SDK** - Memory management, threads, RAG, document processing, and LLM integration
2. **Speechmatics** - Speech-to-text (ASR), text-to-speech (TTS), and voice AI

Your role is to:
- Help developers understand and use these SDKs
- Provide code examples when asked
- Answer questions about integration patterns
- Assist with troubleshooting

Guidelines:
- Be concise but helpful
- Provide code examples in Python when relevant
- Reference the documentation when appropriate
- If you're unsure, say so rather than guessing

You have access to the full SDK documentation for both Backboard and Speechmatics."""

    print("🤖 Creating new assistant...")

    try:
        assistant = await client.create_assistant(
            name="AURA - Voice AI Concierge",
            description="Hackathon assistant with knowledge of Backboard and Speechmatics SDKs"
        )

        print(f"✅ Assistant created!")
        print(f"   ID: {assistant.assistant_id}")
        print(f"   Name: {assistant.name}")
        print(f"\n⚠️  Add this to your .env file:")
        print(f"   BACKBOARD_ASSISTANT_ID={assistant.assistant_id}")

    except Exception as e:
        print(f"❌ Error creating assistant: {e}")

    await client.aclose()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Manage Backboard RAG documents")
    parser.add_argument(
        "--create-assistant",
        action="store_true",
        help="Create a new assistant instead of uploading docs"
    )

    args = parser.parse_args()

    if args.create_assistant:
        asyncio.run(create_assistant_if_needed())
    else:
        asyncio.run(upload_documents())
