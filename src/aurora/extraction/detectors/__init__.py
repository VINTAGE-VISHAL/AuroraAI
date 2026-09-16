"""Individual format signature detectors."""

from aurora.extraction.detectors.html import HTMLDetector
from aurora.extraction.detectors.pdf import PDFDetector
from aurora.extraction.detectors.text import TextDetector
from aurora.extraction.detectors.zip import ZipDetector

__all__ = [
    "PDFDetector",
    "ZipDetector",
    "HTMLDetector",
    "TextDetector",
]
