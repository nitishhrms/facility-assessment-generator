"""Healthcare RAG chat system for the Medelite project.

A guarded, tiered Retrieval-Augmented-Generation pipeline:
  security gate -> domain gate -> intent router (SQL | RAG | web search)
  -> extractive context compression -> Claude-generated grounded answer.

See CHAT_SYSTEM_PLAN.md. Phase 1 (this package's first slice) covers ingestion
of a PubMedQA corpus into a sqlite-vec vector store + similarity search.
"""

__version__ = "0.1.0"
