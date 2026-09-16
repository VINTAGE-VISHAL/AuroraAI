from typing import List, Dict
from aurora.corpus.knowledge_extractor import KnowledgeUnit, BlockType

class BlueprintEngine:
    """Loads declarative blueprint definitions specifying which KnowledgeBlocks to compile."""

    def __init__(self) -> None:
        # Declarative slot requirements for each educational goal style
        self.blueprints: Dict[str, List[BlockType]] = {
            "definition": [BlockType.DEFINITION],
            "detailed": [BlockType.DEFINITION, BlockType.EXPLANATION, BlockType.COMPONENTS, BlockType.ADVANTAGES, BlockType.DISADVANTAGES, BlockType.APPLICATIONS],
            "beginner": [BlockType.DEFINITION, BlockType.EXAMPLE],
            "exam": [BlockType.DEFINITION, BlockType.EXPLANATION, BlockType.COMPONENTS, BlockType.ADVANTAGES, BlockType.DISADVANTAGES, BlockType.APPLICATIONS],
            "interview": [BlockType.DEFINITION, BlockType.EXPLANATION, BlockType.EXAMPLE],
            "revision": [BlockType.DEFINITION, BlockType.COMPONENTS, BlockType.ADVANTAGES],
            "comparison": [BlockType.DEFINITION, BlockType.EXPLANATION],
            "example": [BlockType.DEFINITION, BlockType.EXAMPLE],
            "why": [BlockType.DEFINITION, BlockType.EXPLANATION, BlockType.ADVANTAGES],
            "advantages": [BlockType.ADVANTAGES],
            "flashcard": [BlockType.DEFINITION]
        }

    def get_slots(self, name: str) -> List[BlockType]:
        """Retrieves list of slot requirements for a blueprint name."""
        return self.blueprints.get(name.lower(), [BlockType.DEFINITION, BlockType.EXPLANATION])


class KnowledgeComposer:
    """Composes structured grounded educational explanations matching blueprint definitions."""

    def __init__(self, engine: BlueprintEngine = None) -> None:
        self.engine = engine or BlueprintEngine()
        
        # Heading titles for each section
        self.section_headers = {
            BlockType.DEFINITION: "Core Definition",
            BlockType.EXPLANATION: "Explanation & Working Details",
            BlockType.EXAMPLE: "Practical Example",
            BlockType.COMPONENTS: "Key Components & Structures",
            BlockType.ADVANTAGES: "Advantages & Benefits",
            BlockType.DISADVANTAGES: "Limitations & Drawbacks",
            BlockType.APPLICATIONS: "Real-World Applications"
        }

    def compose(self, unit: KnowledgeUnit, blueprint_name: str) -> str:
        """Assembles KnowledgeUnit blocks matching the requested blueprint schema."""
        slots = self.engine.get_slots(blueprint_name)
        parts: List[str] = []
        
        for slot in slots:
            blocks = unit.get_blocks_of_type(slot)
            if not blocks:
                continue
                
            # Concatenate sentences of the same type
            block_text = " ".join(b.text.strip() for b in blocks)
            header = self.section_headers.get(slot, slot.value.capitalize())
            
            parts.append(f"### {header}\n{block_text}")
            
        # Join into a single structured response
        return "\n\n".join(parts)
