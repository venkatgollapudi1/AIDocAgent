"""
Confluence REST API client.
Handles authentication and pagination for fetching spaces and pages.
"""

import re
import time
import requests
from requests.auth import HTTPBasicAuth
from typing import Optional
from bs4 import BeautifulSoup

from .config import Config


class ConfluenceClient:
    def __init__(self, config: Config):
        self.base_url = config.confluence_url.rstrip("/")
        self.auth = HTTPBasicAuth(config.confluence_username, config.confluence_api_token)
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers.update({"Accept": "application/json"})

    def _get(self, path: str, params: dict = None) -> dict:
        """Make a GET request to the Confluence REST API."""
        url = f"{self.base_url}/rest/api{path}"
        resp = self.session.get(url, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_space(self, space_key: str) -> Optional[dict]:
        """Fetch space metadata; returns None if not found."""
        try:
            data = self._get(f"/space/{space_key}")
            return data
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise

    def get_all_pages(self, space_key: str) -> list[dict]:
        """
        Fetch every page in the space with its body content.
        Handles pagination automatically.
        """
        pages = []
        start = 0
        limit = 50

        while True:
            data = self._get(
                "/content",
                params={
                    "spaceKey": space_key,
                    "type": "page",
                    "status": "current",
                    "expand": "body.storage,ancestors,version,metadata.labels",
                    "start": start,
                    "limit": limit,
                },
            )

            results = data.get("results", [])
            for page in results:
                pages.append(self._parse_page(page))

            # Check if there are more pages
            size = data.get("size", 0)
            if start + size >= data.get("totalSize", 0):
                break

            start += limit
            time.sleep(0.1)  # Be polite to the API

        return pages

    def _parse_page(self, raw: dict) -> dict:
        """Extract useful fields and convert HTML body to plain text."""
        body_html = raw.get("body", {}).get("storage", {}).get("value", "")
        plain_text = self._html_to_text(body_html)

        ancestors = raw.get("ancestors", [])
        breadcrumb = " > ".join(a.get("title", "") for a in ancestors)

        labels = [
            lbl.get("name", "")
            for lbl in raw.get("metadata", {}).get("labels", {}).get("results", [])
        ]

        return {
            "id": raw["id"],
            "title": raw["title"],
            "url": f"{self.base_url}/wiki{raw.get('_links', {}).get('webui', '')}",
            "text": plain_text,
            "breadcrumb": breadcrumb,
            "labels": labels,
            "version": raw.get("version", {}).get("number", 1),
        }

    @staticmethod
    def _html_to_text(html: str) -> str:
        """Convert Confluence storage-format HTML to readable plain text."""
        if not html:
            return ""
        soup = BeautifulSoup(html, "html.parser")

        # Remove script/style tags
        for tag in soup(["script", "style", "ac:structured-macro"]):
            tag.decompose()

        # Preserve table structure with pipe separators
        for table in soup.find_all("table"):
            rows = []
            for tr in table.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                rows.append(" | ".join(cells))
            table.replace_with("\n".join(rows))

        text = soup.get_text(separator="\n")
        # Collapse excessive whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
