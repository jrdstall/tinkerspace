"""Behaviour tests for the Bookkeeper content-addressed storage adapter.

Proves BOOKKEEP-01 through BOOKKEEP-05 from docs/design/specs/BOOKKEEP.md:
- BOOKKEEP-01: SHA-256 content addressing
- BOOKKEEP-02: Idempotent and immutable storage
- BOOKKEEP-03: Byte-exact retrieval and metadata
- BOOKKEEP-04: Rendition registration and retrieval
- BOOKKEEP-05: Non-existent ID handling and safety
"""

import hashlib
from pathlib import Path
import pytest

from iw.adapters.bookkeeper import FileBookkeeper


def test_bookkeep_01_sha256_content_addressing(tmp_path: Path):
    """BOOKKEEP-01: Files are stored by SHA-256 hash digest."""
    bk = FileBookkeeper(tmp_path / "cas")
    data = b"Innovator's Workspace original CAD drawing data"
    expected_hash = hashlib.sha256(data).hexdigest()

    artifact = bk.store_bytes(data, mime_type="application/octet-stream", original_filename="drawing.step")
    assert artifact.content_id == expected_hash
    assert artifact.size_bytes == len(data)
    assert bk.has_content(expected_hash)


def test_bookkeep_02_idempotent_and_immutable_storage(tmp_path: Path):
    """BOOKKEEP-02: Storing identical bytes multiple times is idempotent and immutable."""
    bk = FileBookkeeper(tmp_path / "cas")
    data = b"Sensor calibration curve data 2026-08-31"

    art1 = bk.store_bytes(data, mime_type="text/csv", original_filename="calib_v1.csv")
    art2 = bk.store_bytes(data, mime_type="text/csv", original_filename="calib_v2.csv")

    assert art1.content_id == art2.content_id
    assert bk.get_bytes(art1.content_id) == data


def test_bookkeep_03_retrieval_returns_exact_bytes_and_path(tmp_path: Path):
    """BOOKKEEP-03: Retrieval by content ID returns exact bytes and valid file path."""
    bk = FileBookkeeper(tmp_path / "cas")
    source_file = tmp_path / "whiteboard_notes.png"
    sample_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRfake_png_header_bytes"
    source_file.write_bytes(sample_bytes)

    art = bk.store_file(source_file)
    assert art.size_bytes == len(sample_bytes)
    assert art.original_filename == "whiteboard_notes.png"

    retrieved_bytes = bk.get_bytes(art.content_id)
    assert retrieved_bytes == sample_bytes

    file_path = bk.get_path(art.content_id)
    assert file_path.exists()
    assert file_path.read_bytes() == sample_bytes


def test_bookkeep_04_rendition_registration_and_retrieval(tmp_path: Path):
    """BOOKKEEP-04: Derived renditions can be registered and retrieved by name."""
    bk = FileBookkeeper(tmp_path / "cas")
    original_data = b"<svg><circle cx='50' cy='50' r='40'/></svg>"
    art = bk.store_bytes(original_data, mime_type="image/svg+xml", original_filename="circuit.svg")

    thumbnail_bytes = b"preview_thumbnail_bitmap_png_data"
    rendition_id = bk.register_rendition(
        content_id=art.content_id,
        rendition_name="thumbnail_128",
        rendition_bytes=thumbnail_bytes,
        mime_type="image/png",
    )
    assert rendition_id == hashlib.sha256(thumbnail_bytes).hexdigest()

    retrieved_thumb = bk.get_rendition_bytes(art.content_id, "thumbnail_128")
    assert retrieved_thumb == thumbnail_bytes

    unknown_thumb = bk.get_rendition_bytes(art.content_id, "nonexistent_rendition")
    assert unknown_thumb is None


def test_bookkeep_05_unknown_content_id_raises_key_error(tmp_path: Path):
    """BOOKKEEP-05: Non-existent content ID raises KeyError without crashing or leaking."""
    bk = FileBookkeeper(tmp_path / "cas")
    fake_id = "0000000000000000000000000000000000000000000000000000000000000000"

    assert not bk.has_content(fake_id)
    with pytest.raises(KeyError):
        bk.get_bytes(fake_id)

    with pytest.raises(KeyError):
        bk.get_path(fake_id)

    with pytest.raises(KeyError):
        bk.register_rendition(fake_id, "thumb", b"data", "image/png")
