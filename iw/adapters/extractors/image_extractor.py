"""Image format extractor and metadata reader."""

from pathlib import Path
import re
import struct
from iw.contracts.extractor import ExtractionResult, ExtractorProtocol


class ImageExtractor:
    """Extracts dimensions, format metadata, and embedded text from image files."""

    SUPPORTED_MIMES = {"image/png", "image/jpeg", "image/svg+xml", "image/webp", "image/gif"}
    SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif"}

    def supports_mime_type(self, mime_type: str) -> bool:
        return mime_type.lower() in self.SUPPORTED_MIMES or mime_type.lower().startswith("image/")

    def supports_extension(self, extension: str) -> bool:
        return extension.lower() in self.SUPPORTED_EXTS

    def _get_image_dimensions(self, data: bytes, mime_type: str) -> tuple[int | None, int | None]:
        if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
            width, height = struct.unpack(">II", data[16:24])
            return width, height
        if data.startswith(b"GIF87a") or data.startswith(b"GIF89a") and len(data) >= 10:
            width, height = struct.unpack("<HH", data[6:10])
            return width, height
        return None, None

    def extract_from_bytes(
        self,
        data: bytes,
        mime_type: str,
        filename: str | None = None,
    ) -> ExtractionResult:
        width, height = self._get_image_dimensions(data, mime_type)
        title = Path(filename).stem if filename else "Image"
        text_content: str = ""

        # For SVG files, extract contained text elements
        if "svg" in mime_type or (filename and filename.endswith(".svg")):
            svg_str = data.decode("utf-8", errors="replace")
            svg_texts = re.findall(r"<text[^>]*>(.*?)</text>", svg_str, re.DOTALL)
            clean_texts = [re.sub(r"<[^>]+>", "", t).strip() for t in svg_texts if t.strip()]
            text_content = "\n".join(clean_texts)
            if not text_content:
                text_content = f"[Vector Graphic: {filename or 'image.svg'}]"
        else:
            dim_str = f"{width}x{height}" if width and height else "unknown dimensions"
            text_content = f"[Image: {filename or 'image'} ({dim_str}, {len(data)} bytes)]"

        metadata = {
            "size_bytes": len(data),
            "width": width,
            "height": height,
            "format": mime_type,
        }
        return ExtractionResult(
            text=text_content,
            title=title,
            metadata=metadata,
            content_type=mime_type,
        )

    def extract_from_file(self, file_path: Path) -> ExtractionResult:
        if not file_path.exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")
        ext = file_path.suffix.lower()
        mime = "image/svg+xml" if ext == ".svg" else ("image/png" if ext == ".png" else "image/jpeg")
        return self.extract_from_bytes(
            file_path.read_bytes(),
            mime_type=mime,
            filename=file_path.name,
        )
