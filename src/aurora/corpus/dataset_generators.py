import re
from typing import List, Tuple

class DeterministicQuestionGenerator:
    """Generates diverse, natural student question variations across difficulty levels."""

    @staticmethod
    def clean_concept(heading: str) -> str:
        """Extracts the clean concept name from chapter or numbered headings."""
        if not heading:
            return "this topic"
        # Strip markdown hashes
        heading = re.sub(r'^[#\s]+', '', heading)
        # Strip Chapter/Unit prefix
        heading = re.sub(r'^(?:C\s*H\s*A\s*P\s*T\s*E\s*R\s+\d+|Chapter\s+\d+|UNIT\s+[IVXLCDM]+)[:.\s-]*', '', heading, flags=re.IGNORECASE)
        # Strip section numbers (e.g., 21.3.1)
        heading = re.sub(r'^(?:\d+\.\d+(?:\.\d+)*)[:.\s-]*', '', heading)
        clean = heading.strip()
        return clean if clean else "this topic"

    def generate_questions(self, heading: str) -> List[Tuple[str, str]]:
        """Generates a list of (difficulty_level, question) tuples for a heading."""
        concept = self.clean_concept(heading)
        
        # Define the 10 intent-driven educational question variations
        variations = [
            ("Definition", f"What is {concept}?"),
            ("Detailed", f"Explain {concept} in detail."),
            ("Beginner", f"Explain {concept} like I'm learning DBMS for the first time."),
            ("Exam", f"Write a 16-mark answer on {concept}."),
            ("Interview", f"Explain {concept} from an interview perspective."),
            ("Revision", f"Give short revision notes on {concept}."),
            ("Comparison", f"Differentiate {concept} and other database concepts."),
            ("Example", f"Give a real-world example of {concept}."),
            ("Why", f"Why do we use {concept}?"),
            ("Advantages", f"What are the advantages of {concept}?")
        ]
        return variations


class DeterministicAnswerReformatter:
    """Conversationalizes raw textbook passages using clean grounded terminology."""

    @staticmethod
    def conversationalize(text: str, heading: str) -> str:
        """Formats the response to read like a helpful educational explanation."""
        concept = DeterministicQuestionGenerator.clean_concept(heading)
        text_clean = text.strip()
        
        # Choose a conversational prefix based on the length/nature of the text
        if text_clean.lower().startswith(concept.lower()):
            prefix = "In database systems, "
        else:
            prefix = f"Regarding {concept.lower()}, the textbook explains that: "
            
        return f"{prefix}{text_clean}"
