# Confluence AI Search Agent

An AI-powered search agent that indexes your Confluence space and lets you ask
natural-language questions about its content. Built with **BM25 retrieval** +
**Claude** (RAG pattern) — no vector database required.

---

## Architecture

```
Confluence REST API
      │
      ▼
ConfluenceClient        ← fetches pages, strips HTML → plain text
      │
      ▼
DocumentIndexer         ← chunks text, builds BM25 index, persists to disk
      │
      ▼
ConfluenceAgent         ← retrieves top-K chunks, calls Claude, returns answer
```

---

## Setup

### 1. Clone & install dependencies

```bash
cd confluence_agent
pip install -r requirements.txt
```

### 2. Configure credentials

```bash
cp .env.example .env
# Edit .env with your Confluence URL, credentials, and Anthropic API key
```

**Getting your Confluence API token:**
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click **Create API token**
3. Copy the token into `.env` as `CONFLUENCE_API_TOKEN`

---

## Usage

### Index a space and start interactive chat

```bash
python main.py --space MYSPACE --index
```

### Chat without re-indexing (uses cached index)

```bash
python main.py --space MYSPACE
```

### Single query (non-interactive)

```bash
python main.py --space MYSPACE --query "How do I deploy the application?"
```

---

## Example Session

```
🔗 Connecting to Confluence at https://myorg.atlassian.net...
✅ Connected to space: Engineering Wiki (ENG)
📄 Fetching all documents from space 'ENG'...
   Found 142 pages. Indexing...
✅ Indexed 142 pages successfully.

============================================================
🤖 Confluence Search Agent Ready!
   Space: Engineering Wiki (ENG)
   Type your question or 'exit' to quit.
============================================================

💬 You: How do I roll back a production deployment?

🤖 Agent: Based on the Confluence docs, here are the steps to roll back...

---
📚 Sources:
- [Deployment Runbook](https://myorg.atlassian.net/wiki/...)
- [Incident Response Guide](https://myorg.atlassian.net/wiki/...)
```

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `CONFLUENCE_URL` | *(required)* | Base URL, e.g. `https://org.atlassian.net` |
| `CONFLUENCE_USERNAME` | *(required)* | Your Atlassian email |
| `CONFLUENCE_API_TOKEN` | *(required)* | Atlassian API token |
| `ANTHROPIC_API_KEY` | *(required)* | Anthropic API key |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Claude model to use |
| `INDEX_DIR` | `data/index` | Where indexes are saved |
| `CHUNK_SIZE` | `1000` | Words per chunk |
| `CHUNK_OVERLAP` | `200` | Overlap words between chunks |
| `TOP_K_RESULTS` | `5` | Chunks retrieved per query |

---

## Project Structure

```
confluence_agent/
├── main.py                  # CLI entry point
├── requirements.txt
├── .env.example
├── src/
│   ├── config.py            # Environment / settings
│   ├── confluence_client.py # Confluence REST API wrapper
│   ├── indexer.py           # BM25 indexer + chunker
│   └── agent.py             # RAG agent (retrieval + Claude)
├── tests/
│   └── test_agent.py        # Unit tests
└── data/
    └── index/               # Persisted BM25 indexes (auto-created)
```
