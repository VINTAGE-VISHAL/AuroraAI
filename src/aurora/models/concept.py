"""Concept schema representing syllabus details, terms, and conceptual topics."""

from typing import List

from pydantic import BaseModel


class Concept(BaseModel):
    """A core educational concept or learning outcome extracted from resources."""
    name: str
    description: str
    difficulty: str  # e.g., 'beginner', 'intermediate', 'advanced'
    prerequisites: List[str]
    reference_chunk_ids: List[str]
