"""
Prime shared documents for the per-user assistant system.

This script prepares documents that will be automatically uploaded
to each new user's personal assistant when they are provisioned.

Usage:
    # 1. Place your docs in backend/shared_docs/
    # 2. Run this to verify and optionally test upload
    cd backend
    python scripts/prime_shared_docs.py             # Verify docs
    python scripts/prime_shared_docs.py --test      # Test upload to a test assistant
    python scripts/prime_shared_docs.py --list-all  # List all assistants and their docs
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.assistant_template import SYSTEM_PROMPT, SHARED_DOCUMENTS, SHARED_DOCS_DIR, ASSISTANT_CONFIG


def verify_shared_docs():
    """Check that all shared documents exist and are ready for upload."""
    print(f"Shared docs directory: {SHARED_DOCS_DIR}")
    print(f"Expected documents: {len(SHARED_DOCUMENTS)}\n")

    ready = 0
    missing = 0

    for doc_name in SHARED_DOCUMENTS:
        doc_path = SHARED_DOCS_DIR / doc_name
        if doc_path.exists():
            size_kb = doc_path.stat().st_size / 1024
            print(f"  [OK]      {doc_name} ({size_kb:.1f} KB)")
            ready += 1
        else:
            print(f"  [MISSING] {doc_name}")
            missing += 1

    # Check for extra files in shared_docs that aren't in the template
    actual_files = [
        f.name for f in SHARED_DOCS_DIR.iterdir()
        if f.is_file() and not f.name.startswith(".")
    ]
    extra = set(actual_files) - set(SHARED_DOCUMENTS)
    if extra:
        print(f"\n  Files in shared_docs/ NOT in template:")
        for f in extra:
            print(f"  [EXTRA]   {f}")
            print(f"            Add to SHARED_DOCUMENTS in assistant_template.py to include it")

    print(f"\nReady: {ready}, Missing: {missing}")
    print(f"\nSystem prompt ({len(SYSTEM_PROMPT)} chars):")
    print(f"  {SYSTEM_PROMPT[:200]}...")

    return missing == 0


async def test_upload():
    """Create a test assistant, upload docs, verify indexing, then delete."""
    from backboard import BackboardClient, DocumentStatus

    api_key = os.getenv("BACKBOARD_API_KEY")
    if not api_key:
        print("BACKBOARD_API_KEY not set")
        return

    client = BackboardClient(api_key=api_key)

    try:
        # Create test assistant
        print("\nCreating test assistant...")
        assistant = await client.create_assistant(
            name="[TEST] RAG Priming Verification",
            description="Temporary assistant for testing document uploads",
        )
        assistant_id = str(assistant.assistant_id)
        print(f"  Created: {assistant_id}")

        # Upload each document
        for doc_name in SHARED_DOCUMENTS:
            doc_path = SHARED_DOCS_DIR / doc_name
            if not doc_path.exists():
                print(f"  Skipping {doc_name} (not found)")
                continue

            print(f"\n  Uploading {doc_name}...")
            doc = await client.upload_document_to_assistant(
                assistant_id=assistant_id,
                file_path=str(doc_path)
            )
            print(f"    Document ID: {doc.document_id}")

            # Wait for indexing
            for _ in range(40):  # 2 min max
                status = await client.get_document_status(doc.document_id)
                if status.status == DocumentStatus.INDEXED:
                    print(f"    Indexed: {status.chunk_count} chunks, {status.total_tokens} tokens")
                    break
                elif status.status == DocumentStatus.FAILED:
                    print(f"    FAILED: {status.status_message}")
                    break
                await asyncio.sleep(3)
            else:
                print(f"    Timeout waiting for indexing")

        # Test a RAG query
        print("\nTesting RAG query...")
        thread = await client.create_thread(assistant_id)
        response = await client.add_message(
            thread_id=str(thread.thread_id),
            content="What are the hackathon rules and schedule?",
            llm_provider=os.getenv("CHAT_LLM_PROVIDER", "openai"),
            model_name=os.getenv("CHAT_MODEL_NAME", "gpt-4o-mini"),
        )
        print(f"  Response: {response.content[:200]}...")
        if response.retrieved_files:
            print(f"  Retrieved files: {response.retrieved_files}")
        else:
            print(f"  WARNING: No files retrieved - RAG may not be working")

        # Cleanup
        print(f"\nCleaning up test assistant {assistant_id}...")
        await client.delete_assistant(assistant_id)
        print("  Deleted.")

    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        await client.aclose()

    print("\nTest complete!")


async def list_all_assistants():
    """List all assistants and their documents."""
    from backboard import BackboardClient, DocumentStatus

    api_key = os.getenv("BACKBOARD_API_KEY")
    if not api_key:
        print("BACKBOARD_API_KEY not set")
        return

    client = BackboardClient(api_key=api_key)

    try:
        assistants = await client.list_assistants(limit=100)
        print(f"Total assistants: {len(assistants)}\n")

        for a in assistants:
            print(f"  {a.name}")
            print(f"    ID: {a.assistant_id}")
            print(f"    Created: {a.created_at}")

            try:
                docs = await client.list_assistant_documents(str(a.assistant_id))
                if docs:
                    print(f"    Documents ({len(docs)}):")
                    for d in docs:
                        status_icon = "OK" if d.status == DocumentStatus.INDEXED else str(d.status.value)
                        print(f"      [{status_icon}] {d.filename}")
                else:
                    print(f"    Documents: none")
            except Exception:
                print(f"    Documents: error listing")

            print()

    finally:
        await client.aclose()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Prime shared documents for RAG")
    parser.add_argument("--test", action="store_true", help="Test upload to a temporary assistant")
    parser.add_argument("--list-all", action="store_true", help="List all assistants and their docs")

    args = parser.parse_args()

    if args.test:
        if not verify_shared_docs():
            print("\nFix missing documents before testing.")
            sys.exit(1)
        asyncio.run(test_upload())
    elif args.list_all:
        asyncio.run(list_all_assistants())
    else:
        verify_shared_docs()
