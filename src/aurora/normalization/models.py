from typing import Any, Dict, Optional
from uuid import UUID

from aurora.core.pipeline import PipelineContext


class NormalizationContext(PipelineContext):
    """Configuration context guiding normalizer step executions and metrics."""

    def __init__(
        self,
        preserve_code_blocks: bool = True,
        preserve_tables: bool = True,
        normalize_unicode: bool = True,
        collapse_whitespace: bool = True,
        remove_control_characters: bool = True,
        preserve_markdown: bool = True,
        configuration: Optional[Dict[str, Any]] = None,
        run_id: Optional[UUID] = None,
        execution_id: Optional[UUID] = None,
    ) -> None:
        super().__init__(configuration, run_id, execution_id)
        self.preserve_code_blocks = preserve_code_blocks
        self.preserve_tables = preserve_tables
        self.normalize_unicode = normalize_unicode
        self.collapse_whitespace = collapse_whitespace
        self.remove_control_characters = remove_control_characters
        self.preserve_markdown = preserve_markdown

