"""
Confluence Search Agent.
Uses BM25 retrieval + Claude as the reasoning layer (RAG pattern).
"""

import anthropic

from .config import Config
from .indexer import DocumentIndexer, Chunk


SYSTEM_PROMPT = """You are a helpful assistant for a company's internal knowledge base powered by Confluence.

Your job is to answer user questions based **only** on the provided Confluence document excerpts.

Guidelines:
- Answer clearly and concisely based on the excerpts provided.
- If the excerpts do not contain enough information to answer the question, say so honestly.
- When relevant, mention which page(s) the information came from.
- Do not make up information not present in the excerpts.
- If a question is ambiguous, address the most likely interpretation and note any assumptions.
- Format your answer in readable markdown when helpful (bullet points, bold terms, code blocks).
"""


class ConfluenceAgent:
    def __init__(self, config: Config, indexer: DocumentIndexer):
        self.config = config
        self.indexer = indexer
        self.client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        self.conversation_history: list[dict] = []

    def search(self, space_key: str, query: str) -> str:
        """
        Retrieve relevant document chunks and let Claude compose the answer.
        Maintains multi-turn conversation history for follow-up questions.
        """
        # Retrieve relevant chunks
        results = self.indexer.search(space_key, query, top_k=self.config.top_k_results)

        if not results:
            return (
                "I couldn't find any relevant documents for your query. "
                "Try different keywords or re-index the space with --index."
            )

        # Build context block from retrieved chunks
        context_parts = []
        for i, (chunk, score) in enumerate(results, 1):
            source_line = f"**Source {i}:** [{chunk.title}]({chunk.url})"
            if chunk.breadcrumb:
                source_line += f"  \n📂 {chunk.breadcrumb}"
            if chunk.labels:
                source_line += f"  \n🏷️ Labels: {', '.join(chunk.labels)}"
            context_parts.append(f"{source_line}\n\n{chunk.text}")

        context = "\n\n---\n\n".join(context_parts)

        user_message = (
            f"**User question:** {query}\n\n"
            f"**Relevant Confluence excerpts:**\n\n{context}"
        )

        # Add to conversation history for multi-turn support
        self.conversation_history.append({"role": "user", "content": user_message})

        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=self.conversation_history,
        )

        answer = response.content[0].text

        # Store assistant reply in history
        self.conversation_history.append({"role": "assistant", "content": answer})

        # Append source URLs at the end for transparency
        sources_footer = self._format_sources(results)
        return f"{answer}\n\n{sources_footer}"

    def reset_conversation(self):
        """Clear conversation history to start a fresh session."""
        self.conversation_history = []

    @staticmethod
    def _format_sources(results: list[tuple[Chunk, float]]) -> str:
        seen_urls = set()
        lines = ["---", "**📚 Sources:**"]
        for chunk, score in results:
            if chunk.url not in seen_urls:
                seen_urls.add(chunk.url)
                lines.append(f"- [{chunk.title}]({chunk.url})")
        return "\n".join(lines)
