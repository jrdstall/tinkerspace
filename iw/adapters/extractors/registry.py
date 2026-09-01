"""Extractor registry for routing content extraction requests."""

import mimetypes
from pathlib import Path
from iw.contracts.extractor import (
    ExtractionResult,
    ExtractorProtocol,
    ExtractorRegistryProtocol,
)
from iw.adapters.extractors.html_extractor import HtmlExtractor
from iw.adapters.extractors.image_extractor import ImageExtractor
from iw.adapters.extractors.pdf_extractor import PdfExtractor
from iw.adapters.extractors.text_extractor import TextExtractor


class ExtractorRegistry:
    """Registry routing extraction requests to appropriate extractor adapters."""

    def __init__(self, load_defaults: bool = True) -> None:
        self._extractors: list[ExtractorProtocol] = []
        if load_defaults:
            self.register_extractor(TextExtractor())
            self.register_extractor(HtmlExtractor())
            self.register_extractor(PdfExtractor())
            self.register_extractor(ImageExtractor())

    def register_extractor(self, extractor: ExtractorProtocol) -> None:
        self._extractors.append(extractor)

    def get_extractor_for_mime(self, mime_type: str) -> ExtractorProtocol | None:
        for ext in reversed(self._extractors):
            if ext.supports_mime_type(mime_type):
                return ext
        return None

    def get_extractor_for_extension(self, extension: str) -> ExtractorProtocol | None:
        for ext in reversed(self._extractors):
            if ext.supports_extension(extension):
                return ext
        return None

    def extract(
        self,
        source: Path | bytes,
        mime_type: str | None = None,
        filename: str | None = None,
    ) -> ExtractionResult:
        if isinstance(source, Path):
            if not source.exists():
                raise FileNotFoundError(f"Source file not found: {source}")
            ext = source.suffix.lower()
            detected_mime = mime_type
            if detected_mime is None:
                guessed, _ = mimetypes.guess_type(source.name)
                detected_mime = guessed or "application/octet-stream"

            extractor = self.get_extractor_for_extension(ext) or self.get_extractor_for_mime(detected_mime)
            if extractor:
                return extractor.extract_from_file(source)

            # Fallback to text extractor on file bytes
            fallback = TextExtractor()
            return fallback.extract_from_file(source)

        # source is bytes
        detected_mime = mime_type or "application/octet-stream"
        ext = Path(filename).suffix.lower() if filename else ""

        extractor = (
            (self.get_extractor_for_extension(ext) if ext else None)
            or self.get_extractor_for_mime(detected_mime)
        )
        if extractor:
            return extractor.extract_from_bytes(source, mime_type=detected_mime, filename=filename)

        fallback = TextExtractor()
        return fallback.extract_from_bytes(source, mime_type=detected_mime, filename=filename)
