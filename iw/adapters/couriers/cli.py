"""CLI Courier adapter implementation.

Implements CourierProtocol for local terminal and script-based work order delivery and retrieval.
"""

from pathlib import Path
from typing import Any

from iw.contracts.courier import CourierProtocol
from iw.contracts.models import Author, AuthorKind, UnitOfWork
from iw.contracts.store import StoreProtocol
from iw.domain.workflow.collection import generate_human_starter_template


class CLICourier:
    """Layer 3 courier adapter managing terminal-based dispatch and collection."""

    def __init__(self, store: StoreProtocol, vault_dir: Path | None = None) -> None:
        self._store = store
        self._vault_dir = vault_dir if vault_dir is not None else getattr(store, "vault_dir", Path("."))

    @property
    def name(self) -> str:
        """Courier unique identifier."""
        return "cli"

    def deliver_order(self, unit_id: str, payload: dict[str, Any]) -> bool:
        """Deliver work order prompt and starter templates to the unit folder."""
        clean_id = unit_id.strip().upper()
        folder = self._vault_dir / "work" / clean_id
        folder.mkdir(parents=True, exist_ok=True)

        prompt_text = payload.get("prompt", "")
        if prompt_text:
            (folder / "prompt.md").write_text(str(prompt_text), encoding="utf-8")

        unit = self._store.get_unit(clean_id)
        if unit:
            generate_human_starter_template(unit, folder)
        return True

    def retrieve_result(self, unit_id: str) -> dict[str, Any] | None:
        """Retrieve output deliverable text and file list from the unit folder."""
        clean_id = unit_id.strip().upper()
        folder = self._vault_dir / "work" / clean_id
        deliv_file = folder / "deliverable.md"
        if not deliv_file.exists():
            return None
        return {
            "deliverable": deliv_file.read_text(encoding="utf-8"),
            "files": [p.name for p in folder.iterdir() if p.is_file()],
        }

    def build_cli_author(self, user_name: str = "jared", model_name: str | None = None) -> Author:
        """Construct Author object stamped with CLI courier attribution."""
        kind = AuthorKind.AGENT if model_name else AuthorKind.HUMAN
        return Author(
            kind=kind,
            courier="cli",
            declared_model=model_name,
        )
