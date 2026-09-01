"""HTML content extractor using standard library parser."""

from html.parser import HTMLParser
from pathlib import Path
import re
from iw.contracts.extractor import ExtractionResult, ExtractorProtocol


class _HTMLTextExtractor(HTMLParser):
    """Parser that collects readable text and strips scripts/styles."""

    def __init__(self) -> None:
        super().__init__()
        self.text_chunks: list[str] = []
        self.title: str | None = None
        self._in_title = False
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_lower = tag.lower()
        if tag_lower in ("script", "style", "noscript", "svg"):
            self._skip_depth += 1
        elif tag_lower == "title":
            self._in_title = True
        elif tag_lower in ("p", "div", "h1", "h2", "h3", "h4", "li", "br", "tr"):
            self.text_chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower in ("script", "style", "noscript", "svg") and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag_lower == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            if self._in_title:
                self.title = (self.title or "") + data.strip()
            text = data.strip()
            if text:
                self.text_chunks.append(text + " ")


class HtmlExtractor:
    """Extracts title and clean text from HTML content."""

    SUPPORTED_MIMES = {"text/html", "application/xhtml+xml"}
    SUPPORTED_EXTS = {".html", ".htm", ".xhtml"}

    def supports_mime_type(self, mime_type: str) -> bool:
        return mime_type.lower() in self.SUPPORTED_MIMES

    def supports_extension(self, extension: str) -> bool:
        return extension.lower() in self.SUPPORTED_EXTS

    def extract_from_bytes(
        self,
        data: bytes,
        mime_type: str,
        filename: str | None = None,
    ) -> ExtractionResult:
        try:
            raw_html = data.decode("utf-8")
        except UnicodeDecodeError:
            raw_html = data.decode("latin-1", errors="replace")

        parser = _HTMLTextExtractor()
        parser.feed(raw_html)
        raw_text = "".join(parser.text_chunks)
        clean_text = re.sub(r"\n\s*\n+", "\n\n", raw_text).strip()

        return ExtractionResult(
            text=clean_text,
            title=parser.title or (Path(filename).stem if filename else None),
            metadata={"char_count": len(clean_text), "has_title": parser.title is not None},
            content_type="text/html",
        )

    def extract_from_file(self, file_path: Path) -> ExtractionResult:
        if not file_path.exists():
            raise FileNotFoundError(f"HTML file not found: {file_path}")
        return self.extract_from_bytes(
            file_path.read_bytes(),
            mime_type="text/html",
            filename=file_path.name,
        )
