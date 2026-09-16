import re
from enum import Enum
from typing import List, Tuple, Optional
from pydantic import BaseModel, ConfigDict

class BlockType(str, Enum):
    TITLE = "title"
    DEFINITION = "definition"
    EXPLANATION = "explanation"
    EXAMPLE = "example"
    COMPONENTS = "components"
    ADVANTAGES = "advantages"
    DISADVANTAGES = "disadvantages"
    APPLICATIONS = "applications"


class KnowledgeBlock(BaseModel):
    """A classified block of educational text with confidence metrics."""
    model_config = ConfigDict(frozen=True)

    type: BlockType
    confidence: float
    text: str
    offset: int
    source_segment_id: Optional[str] = None


class KnowledgeUnit(BaseModel):
    """A compiled structured unit representing an educational concept."""
    model_config = ConfigDict(frozen=True)

    title: str
    blocks: List[KnowledgeBlock]

    def get_blocks_of_type(self, block_type: BlockType) -> List[KnowledgeBlock]:
        """Returns all blocks matching a given type."""
        return [b for b in self.blocks if b.type == block_type]


class KnowledgeExtractor:
    """Extracts structured KnowledgeUnits from textbook segments using layered sentence classification."""

    def __init__(self) -> None:
        # Canonical keyword markers
        self.keywords = {
            BlockType.DEFINITION: [r"\brefers to\b", r"\bdefined as\b", r"\bdenotes\b", r"\bstands for\b"],
            BlockType.EXAMPLE: [r"\bfor example\b", r"\bsuch as\b", r"\bconsider\b", r"\bfor instance\b", r"\billustrate\b", r"\be\.g\.\b"],
            BlockType.COMPONENTS: [r"\bconsist of\b", r"\bcontains\b", r"\bcomponent\b", r"\bpart of\b", r"\belement\b"],
            BlockType.ADVANTAGES: [r"\badvantage\b", r"\bbenefit\b", r"\bpro\b", r"\befficient\b", r"\bimprove\b", r"\bperformance\b"],
            BlockType.DISADVANTAGES: [r"\bdisadvantage\b", r"\bdrawback\b", r"\bcon\b", r"\blimitation\b", r"\bexpensive\b", r"\boverhead\b"],
            BlockType.APPLICATIONS: [r"\bused for\b", r"\bapplication\b", r"\bscenario\b", r"\buse case\b", r"\bimplemented in\b"]
        }

    def extract(self, text: str, heading: str, segment_id: Optional[str] = None) -> KnowledgeUnit:
        """Assembles a compiled KnowledgeUnit from raw text segment and heading context."""
        from aurora.corpus.dataset_generators import DeterministicQuestionGenerator
        title = DeterministicQuestionGenerator.clean_concept(heading)
        
        sentences = self._split_sentences(text)
        blocks: List[KnowledgeBlock] = []
        
        # If heading segment is present, classify first sentence as TITLE
        start_idx = 0
        if sentences and heading and sentences[0][0].strip().endswith(heading.strip()):
            blocks.append(
                KnowledgeBlock(
                    type=BlockType.TITLE,
                    confidence=1.0,
                    text=sentences[0][0],
                    offset=sentences[0][1],
                    source_segment_id=segment_id
                )
            )
            start_idx = 1

        total = len(sentences)
        for idx in range(start_idx, total):
            sent, offset = sentences[idx]
            block_type, confidence = self._classify_sentence(sent, idx, total, title)
            blocks.append(
                KnowledgeBlock(
                    type=block_type,
                    confidence=confidence,
                    text=sent,
                    offset=offset,
                    source_segment_id=segment_id
                )
            )
            
        return KnowledgeUnit(title=title, blocks=blocks)

    def _split_sentences(self, text: str) -> List[Tuple[str, int]]:
        """Splits raw text into sentences while tracking exact character offsets."""
        # Simple sentence splitter on punctuation followed by spacing and capital letters
        pattern = re.compile(r'(?<=[.!?])\s+(?=[A-Z0-9#])')
        parts = pattern.split(text)
        
        sentences = []
        current_offset = 0
        for part in parts:
            if part.strip():
                # Locate start offset of this sentence in original text
                pos = text.find(part, current_offset)
                if pos != -1:
                    sentences.append((part, pos))
                    current_offset = pos + len(part)
                else:
                    sentences.append((part, current_offset))
                    current_offset += len(part)
        return sentences

    def _classify_sentence(self, sentence: str, idx: int, total: int, title: str) -> Tuple[BlockType, float]:
        """Classifies a sentence into a BlockType using a multi-signal scoring heuristic."""
        lowered = sentence.lower()
        scores = {t: 0.0 for t in BlockType}
        
        # 1. Heading similarity (0.35)
        # Check if title tokens appear in sentence
        title_tokens = set(re.findall(r'\w+', title.lower()))
        sent_tokens = set(re.findall(r'\w+', lowered))
        if title_tokens:
            matches = title_tokens.intersection(sent_tokens)
            scores[BlockType.DEFINITION] += (len(matches) / len(title_tokens)) * 0.35
            scores[BlockType.EXPLANATION] += (len(matches) / len(title_tokens)) * 0.20

        # 2. Position (0.20)
        # Definitions tend to be at the start (indices 0-2)
        if idx <= 2:
            scores[BlockType.DEFINITION] += 0.20
        # Examples and applications tend to be in the middle or end
        elif idx >= total - 3:
            scores[BlockType.APPLICATIONS] += 0.15
        else:
            scores[BlockType.EXPLANATION] += 0.20

        # 3. Keywords (0.25)
        for b_type, patterns in self.keywords.items():
            for pat in patterns:
                if re.search(pat, lowered):
                    scores[b_type] += 0.25
                    break  # Deduplicate keyword hits for the same type

        # 4. Typography/Formatting (0.10)
        # Check if sentence starts with common itemized markers
        if re.match(r'^\s*[-*•]\s+', sentence) or re.match(r'^\s*\d+\.\s+', sentence):
            scores[BlockType.COMPONENTS] += 0.10
            scores[BlockType.EXPLANATION] += 0.05

        # 5. Enumeration cues (0.10)
        # Check if contains numbering (1, 2, a, b) or separator tokens like semicolons
        if ";" in sentence or "," in sentence:
            scores[BlockType.COMPONENTS] += 0.05
            scores[BlockType.EXPLANATION] += 0.05

        # Select highest scoring type
        # Default to EXPLANATION if all scores are 0
        best_type = BlockType.EXPLANATION
        best_score = 0.0
        
        for b_type, score in scores.items():
            if score > best_score:
                best_score = score
                best_type = b_type
                
        # Confidence normalized to 0.0 - 1.0 range
        confidence = min(max(best_score, 0.50), 1.0)
        
        return best_type, confidence
