"""Strategies for matching potential concept candidates in document segments."""

import re
from typing import List

from aurora.knowledge.extraction.interfaces import ICandidateDiscoveryStrategy
from aurora.models import StructuredDocument
from aurora.models.enums import SegmentType


class HeadingPatternMatcher(ICandidateDiscoveryStrategy):
    """Strategy extracting concepts from Markdown heading titles."""

    def discover(self, doc: StructuredDocument) -> List[str]:
        candidates: List[str] = []
        # Matches typical chapter prefixes like "1.2 ", "Chapter 3: "
        skip_words = {
            "introduction", "summary", "exercise", "exercises",
            "table of contents", "preface", "index"
        }

        for seg in doc.segments:
            if seg.type == SegmentType.HEADING:
                cleaned = re.sub(r"^#{1,6}\s+", "", seg.text).strip()
                # Remove section numbers
                cleaned = re.sub(r"^(?:\d+\.)*\d+\s*", "", cleaned).strip()
                cleaned = re.sub(
                    r"^(?:Chapter|Section)\s+\d+[:\s]*",
                    "",
                    cleaned,
                    flags=re.IGNORECASE
                ).strip()

                lower_cleaned = cleaned.lower()
                prefixes = ("figure", "table", "chart", "page", "exercise")
                if any(lower_cleaned.startswith(p) for p in prefixes):
                    continue

                if cleaned.lower() not in skip_words and len(cleaned) > 2:
                    candidates.append(cleaned)
        return candidates


class BoldPatternMatcher(ICandidateDiscoveryStrategy):
    """Strategy extracting candidates wrapped in markdown bold formatting."""

    def discover(self, doc: StructuredDocument) -> List[str]:
        candidates: List[str] = []
        bold_pattern = re.compile(r"\*\*(.+?)\*\*")
        # Reject common figures/tables prefixes
        skip_patterns = [
            re.compile(r"^(?:Figure|Table|Page|Exercise|Eq)\.?\s*\d+", re.IGNORECASE)
        ]

        for seg in doc.segments:
            for match in bold_pattern.finditer(seg.text):
                val = match.group(1).strip()
                if any(p.match(val) for p in skip_patterns):
                    continue
                # Skip simple strings/digits or long paragraphs accidentally marked bold
                if len(val) > 2 and len(val.split()) < 6:
                    candidates.append(val)
        return candidates


class DefinitionPatternMatcher(ICandidateDiscoveryStrategy):
    """Strategy extracting candidates prefixed by definition labels."""

    def discover(self, doc: StructuredDocument) -> List[str]:
        candidates: List[str] = []
        def_pattern = re.compile(
            r"\b(?:Definition|Def\.?)\s*:\s*([A-Za-z0-9\s\-]+)(?=\.|\n|$)",
            re.IGNORECASE
        )

        for seg in doc.segments:
            for match in def_pattern.finditer(seg.text):
                val = match.group(1).strip()
                if len(val) > 2 and len(val.split()) < 6:
                    candidates.append(val)
        return candidates
