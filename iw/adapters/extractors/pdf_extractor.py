"""PDF document extractor with graceful degradation."""

from pathlib import Path
import re
from iw.contracts.extractor import ExtractionResult, ExtractorProtocol


class PdfExtractor:
    """Extracts text content and metadata from PDF files."""

    SUPPORTED_MIMES = {"application/pdf"}
    SUPPORTED_EXTS = {".pdf"}

    def supports_mime_type(self, mime_type: str) -> bool:
        return mime_type.lower() in self.SUPPORTED_MIMES

    def supports_extension(self, extension: str) -> bool:
        return extension.lower() in self.SUPPORTED_EXTS

    def _extract_title(self, raw_content: str, filename: str | None) -> str | None:
        title_match = re.search(r"/Title\s*\(([^)]+)\)", raw_content)
        if title_match:
            return title_match.group(1).strip()
        return Path(filename).stem if filename else None

    def _extract_text_chunks(self, raw_content: str) -> list[str]:
        extracted: list[str] = []
        for piece in re.findall(r"\(([^)]+)\)\s*Tj", raw_content):
            cleaned = piece.replace("\\(", "(").replace("\\)", ")").strip()
            if cleaned:
                extracted.append(cleaned)
        return extracted

    def extract_from_bytes(
        self,
        data: bytes,
        mime_type: str,
        filename: str | None = None,
    ) -> ExtractionResult:
        warnings: list[str] = []
        if not data.startswith(b"%PDF-"):
            warnings.append("Header does not start with standard %PDF- magic bytes")

        raw_content = data.decode("latin-1", errors="replace")
        title = self._extract_title(raw_content, filename)
        extracted_pieces = self._extract_text_chunks(raw_content)

        full_text = " ".join(extracted_pieces).strip()
        if not full_text:
            full_text = f"[PDF Document: {filename or 'unnamed.pdf'} ({len(data)} bytes)]"
            warnings.append("No uncompressed text streams found; PDF may be compressed or rasterized")

        metadata = {
            "size_bytes": len(data),
            "pdf_version": raw_content[:8].strip() if raw_content.startswith("%PDF-") else "unknown",
            "extracted_token_count": len(extracted_pieces),
        }
        return ExtractionResult(
            text=full_text,
            title=title,
            metadata=metadata,
            content_type="application/pdf",
            warnings=warnings,
        )

    def extract_from_file(self, file_path: Path) -> ExtractionResult:
        if not file_path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        return self.extract_from_bytes(
            file_path.read_bytes(),
            mime_type="application/pdf",
            filename=file_path.name,
        )
