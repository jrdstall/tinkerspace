"""Inbox management and file-based thought capture.

Layer 1 Core component for scanning, appending, and deleting raw inbox items.
"""

from datetime import datetime, timezone
from pathlib import Path
import uuid

from iw.contracts.models import InboxItem


class InboxManager:
    """Manages raw captured thoughts in the vault inbox directory."""

    def __init__(self, inbox_dir: Path) -> None:
        self.inbox_dir = inbox_dir

    def list_items(self) -> list[InboxItem]:
        """Scan and return all raw captured items in the inbox."""
        if not self.inbox_dir.exists():
            return []

        items: list[InboxItem] = []
        # 1. Process quick.txt if present
        quick_file = self.inbox_dir / "quick.txt"
        if quick_file.exists() and quick_file.is_file():
            items.extend(self._parse_quick_lines(quick_file))

        # 2. Process individual files
        for path in sorted(self.inbox_dir.iterdir()):
            if path.is_file() and path.name != "quick.txt" and not path.name.startswith("."):
                item = self._parse_file_item(path)
                if item:
                    items.append(item)

        return items

    def append_item(
        self,
        raw_text: str,
        inlet: str = "quick-capture",
        source_filename: str | None = None,
    ) -> InboxItem:
        """Append a raw captured thought to the store inbox."""
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc)
        clean_text = raw_text.strip()
        uid = uuid.uuid4().hex[:4].upper()
        now_str = now.strftime("%Y%m%d-%H%M%S")
        item_id = f"INB-{now_str}-{uid}"

        target_file = self.inbox_dir / f"{item_id}.md"
        target_file.write_text(clean_text + "\n", encoding="utf-8")

        return InboxItem(
            id=item_id,
            raw_text=clean_text,
            created=now,
            inlet=inlet,
            source_filename=target_file.name,
        )

    def delete_item(self, item_id: str) -> bool:
        """Remove a processed or discarded inbox item from disk."""
        if not self.inbox_dir.exists():
            return False

        # Check for matching filename or stem
        for path in self.inbox_dir.iterdir():
            if path.is_file() and (path.stem == item_id or path.name == item_id):
                path.unlink()
                return True

        # Check for line in quick.txt
        if item_id.startswith("line-"):
            return self._delete_quick_line(item_id)

        return False

    def _parse_quick_lines(self, quick_file: Path) -> list[InboxItem]:
        """Parse individual non-empty lines from quick.txt."""
        items: list[InboxItem] = []
        try:
            mtime = datetime.fromtimestamp(quick_file.stat().st_mtime, timezone.utc)
            lines = quick_file.read_text(encoding="utf-8").splitlines()
            for idx, line in enumerate(lines):
                line_clean = line.strip()
                if line_clean:
                    items.append(
                        InboxItem(
                            id=f"line-{idx}",
                            raw_text=line_clean,
                            created=mtime,
                            inlet="quick-line",
                            source_filename="quick.txt",
                        )
                    )
        except Exception:
            pass
        return items

    def _parse_file_item(self, path: Path) -> InboxItem | None:
        """Parse a standalone file into an InboxItem."""
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
            text = path.read_text(encoding="utf-8").strip()
            if not text:
                return None
            return InboxItem(
                id=path.stem,
                raw_text=text,
                created=mtime,
                inlet="synced-file" if "sync" in path.name.lower() else "quick-capture",
                source_filename=path.name,
            )
        except Exception:
            return None

    def _delete_quick_line(self, line_id: str) -> bool:
        """Remove specific line from quick.txt."""
        quick_file = self.inbox_dir / "quick.txt"
        if not quick_file.exists():
            return False
        try:
            target_idx = int(line_id.replace("line-", ""))
            lines = quick_file.read_text(encoding="utf-8").splitlines()
            valid_lines = [l for l in lines if l.strip()]
            if 0 <= target_idx < len(valid_lines):
                valid_lines.pop(target_idx)
                quick_file.write_text("\n".join(valid_lines) + ("\n" if valid_lines else ""), encoding="utf-8")
                return True
        except Exception:
            pass
        return False
