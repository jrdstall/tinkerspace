"""Text and markdown content extractor."""

from pathlib import Path
from iw.contracts.extractor import ExtractionResult, ExtractorProtocol


class TextExtractor:
    """Extracts content from plain text, markdown, CSV, and code files."""

    SUPPORTED_MIMES = {
        "text/plain",
        "text/markdown",
        "text/csv",
        "text/x-python",
        "application/json",
        "application/x-yaml",
        "text/yaml",
    }
    SUPPORTED_EXTS = {".txt", ".md", ".csv", ".json", ".yaml", ".yml", ".py", ".log"}

    def supports_mime_type(self, mime_type: str) -> bool:
        return mime_type.lower() in self.SUPPORTED_MIMES or mime_type.lower().startswith("text/")

    def supports_extension(self, extension: str) -> bool:
        return extension.lower() in self.SUPPORTED_EXTS

    def extract_from_bytes(
        self,
        data: bytes,
        mime_type: str,
        filename: str | None = None,
    ) -> ExtractionResult:
        encoding = "utf-8"
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = data.decode("latin-1")
                encoding = "latin-1"
            except UnicodeDecodeError:
                text = data.decode("utf-8", errors="replace")
                encoding = "utf-8-replace"

        title: str | None = None
        lines = text.splitlines()
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("# "):
                title = stripped.lstrip("# ").strip()
                break

        metadata = {
            "char_count": len(text),
            "line_count": len(lines),
            "encoding": encoding,
        }
        return ExtractionResult(
            text=text,
            title=title,
            metadata=metadata,
            content_type=mime_type or "text/plain",
        )

    def extract_from_file(self, file_path: Path) -> ExtractionResult:
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        data = file_path.read_bytes()
        ext = file_path.suffix.lower()
        mime = "text/markdown" if ext == ".md" else "text/plain"
        res = self.extract_from_bytes(data, mime_type=mime, filename=file_path.name)
        if not res.title and file_path.stem:
            return ExtractionResult(
                text=res.text,
                title=file_path.stem,
                metadata=res.metadata,
                content_type=res.content_type,
            )
        return res
