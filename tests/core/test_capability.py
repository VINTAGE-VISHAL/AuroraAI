"""Unit tests for the framework Capability Registry."""

import pytest

from aurora.core.capability import CapabilityDescriptor, CapabilityRegistry


@pytest.fixture(autouse=True)
def clean_registry() -> None:
    """Ensure capability registry is cleared before and after each test."""
    CapabilityRegistry.clear()
    yield
    CapabilityRegistry.clear()


def test_capability_registration_and_lookup() -> None:
    """Verify capabilities can be registered and retrieved properly."""
    descriptor = CapabilityDescriptor(
        name="PDFExtractor",
        category="extraction",
        version="1.0.0",
        description="Extracts text from PDF files.",
        status="stable",
    )

    CapabilityRegistry.register(descriptor)

    assert CapabilityRegistry.has_capability("extraction", "PDFExtractor") is True
    assert CapabilityRegistry.has_capability("extraction", "HTMLExtractor") is False

    retrieved = CapabilityRegistry.get_capability("extraction", "PDFExtractor")
    assert retrieved == descriptor


def test_get_all_capabilities_filtering() -> None:
    """Verify registry supports listing all capabilities and filtering by category."""
    cap1 = CapabilityDescriptor(
        name="PDFExtractor",
        category="extraction",
        version="1.0.0",
        description="PDF extractor",
    )
    cap2 = CapabilityDescriptor(
        name="UnicodeNormalizer",
        category="normalization",
        version="1.0.0",
        description="Unicode normalizer",
    )

    CapabilityRegistry.register(cap1)
    CapabilityRegistry.register(cap2)

    all_caps = CapabilityRegistry.get_all_capabilities()
    assert len(all_caps) == 2

    extraction_caps = CapabilityRegistry.get_all_capabilities("extraction")
    assert len(extraction_caps) == 1
    assert extraction_caps[0] == cap1
