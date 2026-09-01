"""File-based content-addressed storage adapter for Bookkeeper."""

from datetime import datetime, timezone
import hashlib
import json
import mimetypes
from pathlib import Path
import tempfile

from iw.contracts.bookkeeper import BookkeeperProtocol, StoredArtifact


class FileBookkeeper:
    """Implements BookkeeperProtocol using local content-addressed files."""

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.cas_dir = root_dir / "cas"
        self.meta_dir = root_dir / "meta"
        self.cas_dir.mkdir(parents=True, exist_ok=True)
        self.meta_dir.mkdir(parents=True, exist_ok=True)

    def _blob_path(self, content_id: str) -> Path:
        prefix = content_id[:2]
        return self.cas_dir / prefix / content_id

    def _meta_path(self, content_id: str) -> Path:
        prefix = content_id[:2]
        return self.meta_dir / prefix / f"{content_id}.json"

    def _save_metadata(self, artifact: StoredArtifact) -> None:
        meta_path = self._meta_path(artifact.content_id)
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "content_id": artifact.content_id,
            "size_bytes": artifact.size_bytes,
            "mime_type": artifact.mime_type,
            "stored_at": artifact.stored_at.isoformat(),
            "original_filename": artifact.original_filename,
            "renditions": artifact.renditions,
        }
        with tempfile.NamedTemporaryFile("w", dir=meta_path.parent, delete=False, encoding="utf-8") as tf:
            json.dump(data, tf, indent=2)
            tmp_name = tf.name
        Path(tmp_name).replace(meta_path)

    def _load_metadata(self, content_id: str) -> StoredArtifact:
        meta_path = self._meta_path(content_id)
        if not meta_path.exists():
            raise KeyError(f"Metadata for content ID '{content_id}' not found")
        with open(meta_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return StoredArtifact(
            content_id=data["content_id"],
            size_bytes=data["size_bytes"],
            mime_type=data["mime_type"],
            stored_at=datetime.fromisoformat(data["stored_at"]),
            original_filename=data.get("original_filename"),
            renditions=data.get("renditions", {}),
        )

    def store_bytes(
        self,
        data: bytes,
        mime_type: str,
        original_filename: str | None = None,
    ) -> StoredArtifact:
        content_id = hashlib.sha256(data).hexdigest()
        blob_path = self._blob_path(content_id)

        if not blob_path.exists():
            blob_path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile("wb", dir=blob_path.parent, delete=False) as tf:
                tf.write(data)
                tmp_name = tf.name
            Path(tmp_name).replace(blob_path)

        meta_path = self._meta_path(content_id)
        if meta_path.exists():
            return self._load_metadata(content_id)

        artifact = StoredArtifact(
            content_id=content_id,
            size_bytes=len(data),
            mime_type=mime_type,
            stored_at=datetime.now(timezone.utc),
            original_filename=original_filename,
            renditions={},
        )
        self._save_metadata(artifact)
        return artifact

    def store_file(
        self,
        source_path: Path,
        mime_type: str | None = None,
    ) -> StoredArtifact:
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")
        data = source_path.read_bytes()
        detected_type = mime_type
        if detected_type is None:
            guessed, _ = mimetypes.guess_type(source_path.name)
            detected_type = guessed or "application/octet-stream"
        return self.store_bytes(data=data, mime_type=detected_type, original_filename=source_path.name)

    def get_bytes(self, content_id: str) -> bytes:
        return self.get_path(content_id).read_bytes()

    def get_path(self, content_id: str) -> Path:
        blob_path = self._blob_path(content_id)
        if not blob_path.exists():
            raise KeyError(f"Content ID '{content_id}' not found in store")
        return blob_path

    def has_content(self, content_id: str) -> bool:
        return self._blob_path(content_id).exists()

    def register_rendition(
        self,
        content_id: str,
        rendition_name: str,
        rendition_bytes: bytes,
        mime_type: str,
    ) -> str:
        parent = self._load_metadata(content_id)
        rendition_artifact = self.store_bytes(
            data=rendition_bytes,
            mime_type=mime_type,
            original_filename=f"{rendition_name}_{parent.original_filename or content_id}",
        )
        updated_renditions = dict(parent.renditions)
        updated_renditions[rendition_name] = rendition_artifact.content_id
        updated_parent = StoredArtifact(
            content_id=parent.content_id,
            size_bytes=parent.size_bytes,
            mime_type=parent.mime_type,
            stored_at=parent.stored_at,
            original_filename=parent.original_filename,
            renditions=updated_renditions,
        )
        self._save_metadata(updated_parent)
        return rendition_artifact.content_id

    def get_rendition_bytes(
        self,
        content_id: str,
        rendition_name: str,
    ) -> bytes | None:
        try:
            meta = self._load_metadata(content_id)
        except KeyError:
            return None
        rendition_id = meta.renditions.get(rendition_name)
        if not rendition_id:
            return None
        return self.get_bytes(rendition_id)
