"""
Configuration management — reads from environment variables or .env file.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    def __init__(self):
        # Confluence settings
        self.confluence_url = self._require("CONFLUENCE_URL")
        self.confluence_username = self._require("CONFLUENCE_USERNAME")
        self.confluence_api_token = self._require("CONFLUENCE_API_TOKEN")

        # Anthropic settings
        self.anthropic_api_key = self._require("ANTHROPIC_API_KEY")
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

        # Indexing settings
        self.index_dir = os.getenv("INDEX_DIR", "data/index")
        self.chunk_size = int(os.getenv("CHUNK_SIZE", "1000"))
        self.chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "200"))
        self.top_k_results = int(os.getenv("TOP_K_RESULTS", "5"))

    def _require(self, key: str) -> str:
        val = os.getenv(key)
        if not val:
            raise EnvironmentError(
                f"Required environment variable '{key}' is not set. "
                f"Copy .env.example to .env and fill in your values."
            )
        return val
