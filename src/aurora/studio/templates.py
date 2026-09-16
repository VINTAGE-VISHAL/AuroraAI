"""Templates defining standard prompt formats for educational instruction tuning examples."""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class PromptTemplate(BaseModel):
    """Immutable representation of a parameterized format layout."""
    model_config = ConfigDict(frozen=True)

    template_id: str
    format_tag: str
    user_prompt_template: str
    system_prompt_template: Optional[str] = None


class PromptTemplateRegistry:
    """Registry maintaining standard pedagogical prompt templates."""

    def __init__(self) -> None:
        self._templates = {
            "tutor": PromptTemplate(
                template_id="tutor_v1",
                format_tag="tutor",
                system_prompt_template="You are a helpful educational tutor specializing in DBMS.",
                user_prompt_template=(
                    "Explain the concept of {concept_name} to a student. "
                    "Use this context definition: {definition}. "
                    "Prerequisites: {prerequisites}."
                ),
            ),
            "mcq": PromptTemplate(
                template_id="mcq_v1",
                format_tag="mcq",
                system_prompt_template="You are an exam examiner compiling educational questions.",
                user_prompt_template=(
                    "Generate a Multiple-Choice Question (MCQ) for {concept_name}. "
                    "Core Definition: {definition}."
                ),
            ),
            "flashcard": PromptTemplate(
                template_id="flashcard_v1",
                format_tag="flashcard",
                user_prompt_template="Front: What is {concept_name}? Back: {definition}.",
            ),
            "viva": PromptTemplate(
                template_id="viva_v1",
                format_tag="viva",
                user_prompt_template=(
                    "Oral exam question: Explain how {concept_name} relates to its "
                    "prerequisites ({prerequisites})."
                ),
            ),
            "coding": PromptTemplate(
                template_id="coding_v1",
                format_tag="coding",
                user_prompt_template=(
                    "Write a coding exercise for {concept_name}. "
                    "Core concept context: {definition}."
                ),
            ),
        }

    def get_template(self, format_tag: str) -> PromptTemplate:
        """Retrieves template by key or raises error if not registered."""
        if format_tag not in self._templates:
            raise KeyError(f"Template format '{format_tag}' is not registered.")
        return self._templates[format_tag]
