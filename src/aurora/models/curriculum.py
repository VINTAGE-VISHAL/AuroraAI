"""Curriculum schema defining educational syllabus models."""

from typing import List

from pydantic import BaseModel

from aurora.models.concept import Concept


class Curriculum(BaseModel):
    """Representing the structured network of learning Concepts."""
    domain: str
    concepts: List[Concept]
    version: str
