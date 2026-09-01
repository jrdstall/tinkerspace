"""Contract tests for Extractor implementations."""

import pytest
from iw.contracts.extractor import (
    ExtractorProtocol,
    ExtractorRegistryProtocol,
    ExtractionResult,
)
from iw.adapters.extractors.html_extractor import HtmlExtractor
from iw.adapters.extractors.image_extractor import ImageExtractor
from iw.adapters.extractors.pdf_extractor import PdfExtractor
from iw.adapters.extractors.registry import ExtractorRegistry
from iw.adapters.extractors.text_extractor import TextExtractor


def test_extractors_satisfy_protocols():
    """Ensure all extractor adapters satisfy ExtractorProtocol and registry satisfies ExtractorRegistryProtocol."""
    text_ex = TextExtractor()
    assert isinstance(text_ex, ExtractorProtocol)

    html_ex = HtmlExtractor()
    assert isinstance(html_ex, ExtractorProtocol)

    pdf_ex = PdfExtractor()
    assert isinstance(pdf_ex, ExtractorProtocol)

    img_ex = ImageExtractor()
    assert isinstance(img_ex, ExtractorProtocol)

    registry = ExtractorRegistry()
    assert isinstance(registry, ExtractorRegistryProtocol)
