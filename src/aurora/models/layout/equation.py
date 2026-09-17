"""Models representing parsed mathematical formulas."""

from pydantic import ConfigDict

from aurora.models.layout.base import LayoutObject


class MathExpression(LayoutObject):
    """Natively formatted math formula expression."""
    model_config = ConfigDict(frozen=True)

    original_text: str
    latex_text: str
    is_display_mode: bool = False
