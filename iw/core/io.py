"""Filesystem I/O, atomic write, and file scanning helpers for the Markdown Store.

Layer 1 Core module. Depends only on iw.contracts, stdlib, and yaml.
"""

from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any
import yaml

from iw.contracts.models import AttentionItem, Node
from iw.core.frontmatter import parse_node_from_text, slugify_title


def read_raw_frontmatter_and_body(path: Path) -> tuple[dict[str, Any], str]:
    """Extract raw YAML dictionary and prose body from a markdown file."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return {}, ""

    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    try:
        data = yaml.safe_load(parts[1]) or {}
        body = parts[2].lstrip("\r\n")
        return (data if isinstance(data, dict) else {}, body)
    except Exception:
        return {}, text


def atomic_write_markdown(
    target: Path, fm_data: dict[str, Any], body: str
) -> None:
    """Write frontmatter and body to a temporary file then atomically replace target."""
    target.parent.mkdir(parents=True, exist_ok=True)
    fm_yaml = yaml.safe_dump(fm_data, sort_keys=False, allow_unicode=True)
    content = f"---\n{fm_yaml}---\n{body}"
    temp_path = target.with_name(f".{target.name}.tmp")
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, target)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise


def scan_vault_markdown_files(vault_dir: Path) -> list[Path]:
    """Find all entity .md files in the vault, excluding inbox directory."""
    if not vault_dir.exists():
        return []
    return [
        p for p in vault_dir.rglob("*.md")
        if p.is_file() and not p.parts[-2] == "inbox"
    ]


def parse_vault_file(path: Path) -> tuple[Node | None, AttentionItem | None]:
    """Parse markdown file or return sync conflict item."""
    if ".sync-conflict-" in path.name:
        now = datetime.now(timezone.utc)
        return None, AttentionItem(str(path), "Sync conflict file", now)

    try:
        text = path.read_text(encoding="utf-8")
    except Exception as err:
        now = datetime.now(timezone.utc)
        return None, AttentionItem(str(path), f"Read error: {err}", now)

    return parse_node_from_text(text, str(path))


def find_file_by_id(vault_dir: Path, clean_id: str) -> Path | None:
    """Locate existing file path matching an entity ID."""
    for path in scan_vault_markdown_files(vault_dir):
        node, _ = parse_vault_file(path)
        if node and node.id.upper() == clean_id:
            return path
    return None


def build_node_path(vault_dir: Path, node_type: str, title: str, clean_id: str, now: datetime) -> Path:
    """Generate destination path for a new node."""
    slug = slugify_title(title, clean_id)
    date_str = now.strftime("%Y-%m-%d")
    folder = vault_dir / node_type.lower()
    return folder / f"{date_str}-{slug}.md"
