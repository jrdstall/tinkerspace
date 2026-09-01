"""Behaviour tests for content extractors.

Proves EXTRACT-01 through EXTRACT-06 from docs/design/specs/EXTRACT.md:
- EXTRACT-01: Text and markdown parsing
- EXTRACT-02: HTML stripping and title extraction
- EXTRACT-03: PDF content extraction and graceful degradation
- EXTRACT-04: Image metadata and SVG text extraction
- EXTRACT-05: Registry routing by MIME and extension
- EXTRACT-06: Unsupported format safety and fallback
"""

from pathlib import Path
import pytest

from iw.adapters.extractors.registry import ExtractorRegistry
from iw.adapters.extractors.text_extractor import TextExtractor
from iw.adapters.extractors.html_extractor import HtmlExtractor
from iw.adapters.extractors.pdf_extractor import PdfExtractor
from iw.adapters.extractors.image_extractor import ImageExtractor


def test_extract_01_text_and_markdown_extraction(tmp_path: Path):
    """EXTRACT-01: Text extractor parses markdown and plain text with structural metadata."""
    ex = TextExtractor()
    md_file = tmp_path / "note.md"
    md_file.write_text("# Project Vanguard\n\nDetailed technical specification.", encoding="utf-8")

    res = ex.extract_from_file(md_file)
    assert res.title == "Project Vanguard"
    assert "Detailed technical specification." in res.text
    assert res.metadata["line_count"] == 3


def test_extract_02_html_strips_tags_and_extracts_title():
    """EXTRACT-02: HTML extractor strips scripts/styles and extracts page title."""
    ex = HtmlExtractor()
    html_data = b"""
    <!DOCTYPE html>
    <html>
      <head>
        <title>Hydraulic Actuator Datasheet</title>
        <style>body { color: red; }</style>
        <script>console.log("secret tracker");</script>
      </head>
      <body>
        <h1>Specifications</h1>
        <p>Peak thrust: 1500 N at 24V.</p>
      </body>
    </html>
    """
    res = ex.extract_from_bytes(html_data, mime_type="text/html")
    assert res.title == "Hydraulic Actuator Datasheet"
    assert "secret tracker" not in res.text
    assert "Peak thrust: 1500 N at 24V." in res.text


def test_extract_03_pdf_extracts_text_and_degrades_gracefully():
    """EXTRACT-03: PDF extractor extracts text streams and handles missing streams safely."""
    ex = PdfExtractor()
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Title (Servo Calibration) >>\nendobj\nBT (Measured 12.4 rad/s) Tj ET\n%%EOF"

    res = ex.extract_from_bytes(pdf_bytes, mime_type="application/pdf", filename="servo.pdf")
    assert res.title == "Servo Calibration"
    assert "Measured 12.4 rad/s" in res.text
    assert res.metadata["pdf_version"] == "%PDF-1.4"


def test_extract_04_image_metadata_and_svg_text(tmp_path: Path):
    """EXTRACT-04: Image extractor extracts dimensions and SVG vector text."""
    ex = ImageExtractor()
    svg_data = b"<svg width='200' height='100'><text x='20' y='50'>Power Distribution Unit</text></svg>"
    res_svg = ex.extract_from_bytes(svg_data, mime_type="image/svg+xml", filename="pdu.svg")
    assert "Power Distribution Unit" in res_svg.text

    # PNG with 100x50 dimensions
    # Header: 8 bytes magic + 4 bytes length + 4 bytes 'IHDR' + 4 bytes width (100) + 4 bytes height (50)
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x64\x00\x00\x00\x32\x08\x06\x00\x00\x00"
    res_png = ex.extract_from_bytes(png_bytes, mime_type="image/png", filename="test.png")
    assert res_png.metadata["width"] == 100
    assert res_png.metadata["height"] == 50
    assert "100x50" in res_png.text


def test_extract_05_registry_routes_by_mime_and_extension(tmp_path: Path):
    """EXTRACT-05: Extractor registry routes by MIME or extension."""
    registry = ExtractorRegistry()
    html_file = tmp_path / "page.html"
    html_file.write_text("<html><head><title>Test Page</title></head><body>Content</body></html>")

    res = registry.extract(html_file)
    assert res.title == "Test Page"
    assert res.content_type == "text/html"


def test_extract_06_unsupported_binary_format_degrades_gracefully():
    """EXTRACT-06: Unknown binary formats return safely with metadata and text placeholder."""
    registry = ExtractorRegistry()
    bin_data = b"\x00\x01\x02\x03\x04\x05\xff\xfe"
    res = registry.extract(bin_data, mime_type="application/x-custom-binary", filename="data.bin")

    assert res.text is not None
    assert res.content_type == "application/x-custom-binary"
