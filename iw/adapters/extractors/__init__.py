"""Pluggable content extractors package."""

from iw.adapters.extractors.html_extractor import HtmlExtractor
from iw.adapters.extractors.image_extractor import ImageExtractor
from iw.adapters.extractors.pdf_extractor import PdfExtractor
from iw.adapters.extractors.registry import ExtractorRegistry
from iw.adapters.extractors.text_extractor import TextExtractor

__all__ = [
    "HtmlExtractor",
    "ImageExtractor",
    "PdfExtractor",
    "ExtractorRegistry",
    "TextExtractor",
]
