#!/usr/bin/env python3
"""
Confluence AI Search Agent
Connects to Confluence, indexes a space, and provides an AI-powered search agent.
"""

import argparse
import sys
from src.confluence_client import ConfluenceClient
from src.indexer import DocumentIndexer
from src.agent import ConfluenceAgent
from src.config import Config


def main():
    parser = argparse.ArgumentParser(description="Confluence AI Search Agent")
    parser.add_argument("--space", required=True, help="Confluence space key (e.g., 'MYSPACE')")
    parser.add_argument("--index", action="store_true", help="Re-index the space before searching")
    parser.add_argument("--query", help="Run a single query and exit")
    args = parser.parse_args()

    config = Config()

    print(f"\n🔗 Connecting to Confluence at {config.confluence_url}...")
    client = ConfluenceClient(config)

    # Verify space exists
    space = client.get_space(args.space)
    if not space:
        print(f"❌ Space '{args.space}' not found. Check the space key and your credentials.")
        sys.exit(1)
    print(f"✅ Connected to space: {space['name']} ({args.space})")

    indexer = DocumentIndexer(config)

    # Index if requested or if no index exists
    if args.index or not indexer.index_exists(args.space):
        print(f"\n📄 Fetching all documents from space '{args.space}'...")
        pages = client.get_all_pages(args.space)
        print(f"   Found {len(pages)} pages. Indexing...")
        indexer.index_pages(args.space, pages)
        print(f"✅ Indexed {len(pages)} pages successfully.\n")
    else:
        count = indexer.get_index_count(args.space)
        print(f"✅ Using existing index ({count} documents). Use --index to refresh.\n")

    agent = ConfluenceAgent(config, indexer)

    if args.query:
        # Single query mode
        result = agent.search(args.space, args.query)
        print(result)
    else:
        # Interactive chat mode
        print("=" * 60)
        print("🤖 Confluence Search Agent Ready!")
        print(f"   Space: {space['name']} ({args.space})")
        print("   Type your question or 'exit' to quit.")
        print("=" * 60)

        while True:
            try:
                user_input = input("\n💬 You: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ("exit", "quit", "q"):
                    print("👋 Goodbye!")
                    break

                print("\n🤖 Agent: ", end="", flush=True)
                result = agent.search(args.space, user_input)
                print(result)
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break


if __name__ == "__main__":
    main()
