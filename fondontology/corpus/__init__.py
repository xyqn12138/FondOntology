"""Versioned document evidence storage, independent of ontology fact storage."""

from .store import CorpusError, CorpusRepository

__all__ = ["CorpusError", "CorpusRepository"]
