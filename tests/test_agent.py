"""
Tests for the Confluence Agent components.
Run with: pytest tests/
"""

import pytest
from unittest.mock import MagicMock, patch
from src.indexer import DocumentIndexer, BM25Index, Chunk
from src.confluence_client import ConfluenceClient


# --- BM25 Index Tests ---

def make_chunk(doc_id, title, text, chunk_id=0):
    return Chunk(doc_id=doc_id, chunk_id=chunk_id, title=title, url="http://test",
                 breadcrumb="", labels=[], text=text)


def test_bm25_basic_search():
    index = BM25Index()
    chunks = [
        make_chunk("1", "Python Guide", "Python is a programming language great for scripting"),
        make_chunk("2", "Java Guide", "Java is an object oriented language for enterprise apps"),
        make_chunk("3", "DevOps Intro", "Docker and Kubernetes are used for container orchestration"),
    ]
    index.add_chunks(chunks)

    results = index.search("Python programming", top_k=2)
    assert len(results) > 0
    assert results[0][0].doc_id == "1"


def test_bm25_no_match():
    index = BM25Index()
    chunks = [make_chunk("1", "Title", "Some text about cats and dogs")]
    index.add_chunks(chunks)

    results = index.search("quantum physics supercollider", top_k=3)
    assert results == []


def test_bm25_empty_index():
    index = BM25Index()
    index.add_chunks([])
    results = index.search("anything")
    assert results == []


def test_tokenize():
    tokens = BM25Index._tokenize("Hello World! This is a TEST 123.")
    assert "hello" in tokens
    assert "world" in tokens
    assert "test" in tokens
    assert "123" in tokens
    # stop words removed
    assert "is" not in tokens
    assert "a" not in tokens


# --- HTML to text Tests ---

def test_html_to_text_basic():
    html = "<p>Hello <strong>world</strong>!</p>"
    result = ConfluenceClient._html_to_text(html)
    assert "Hello" in result
    assert "world" in result


def test_html_to_text_table():
    html = """
    <table>
      <tr><th>Name</th><th>Age</th></tr>
      <tr><td>Alice</td><td>30</td></tr>
    </table>
    """
    result = ConfluenceClient._html_to_text(html)
    assert "Name" in result
    assert "Alice" in result
    assert "|" in result


def test_html_to_text_empty():
    assert ConfluenceClient._html_to_text("") == ""
    assert ConfluenceClient._html_to_text(None) == ""


# --- Chunking Tests ---

def test_chunking_long_text(tmp_path):
    cfg = MagicMock()
    cfg.chunk_size = 10
    cfg.chunk_overlap = 2
    cfg.index_dir = str(tmp_path)

    indexer = DocumentIndexer(cfg)
    page = {
        "id": "1", "title": "Test", "url": "http://x",
        "breadcrumb": "", "labels": [],
        "text": " ".join([f"word{i}" for i in range(50)])
    }
    chunks = indexer._chunk_page(page)
    assert len(chunks) > 1
    # Overlap: last words of one chunk appear at start of next
    assert chunks[0].text.split()[-2] in chunks[1].text


def test_chunking_empty_page(tmp_path):
    cfg = MagicMock()
    cfg.chunk_size = 100
    cfg.chunk_overlap = 20
    cfg.index_dir = str(tmp_path)

    indexer = DocumentIndexer(cfg)
    page = {"id": "1", "title": "Empty", "url": "http://x",
            "breadcrumb": "", "labels": [], "text": ""}
    chunks = indexer._chunk_page(page)
    assert chunks == []


# --- Index persistence Tests ---

def test_index_round_trip(tmp_path):
    cfg = MagicMock()
    cfg.chunk_size = 100
    cfg.chunk_overlap = 20
    cfg.index_dir = str(tmp_path)
    cfg.top_k_results = 3

    indexer = DocumentIndexer(cfg)
    pages = [
        {"id": "1", "title": "Deployment Guide", "url": "http://x/1",
         "breadcrumb": "Docs", "labels": ["ops"],
         "text": "Deploy the application using Docker compose and nginx reverse proxy"},
        {"id": "2", "title": "API Reference", "url": "http://x/2",
         "breadcrumb": "Docs > API", "labels": ["dev"],
         "text": "The REST API supports JSON payloads with authentication via Bearer tokens"},
    ]

    indexer.index_pages("TEST", pages)
    assert indexer.index_exists("TEST")
    assert indexer.get_index_count("TEST") > 0

    results = indexer.search("TEST", "Docker deployment", top_k=2)
    assert len(results) > 0
    assert results[0][0].title == "Deployment Guide"
