"""CLI commands for dispatching, submitting, and inspecting units of work.

Implements CLICOUR-01 through CLICOUR-04 for local command-line operations.
"""

import argparse
import os
from pathlib import Path
import sys

from iw.adapters.couriers.cli import CLICourier
from iw.contracts.models import Author, AuthorKind, UnitOfWork, UnitState
from iw.contracts.store import StoreProtocol
from iw.core.events import FileEventLog
from iw.core.store import MarkdownStore
from iw.domain.workflow.collection import collect_unit_results
from iw.domain.workflow.state import transition_unit_state


def _get_store(vault_dir: Path | None = None) -> StoreProtocol:
    """Instantiate MarkdownStore from vault path or environment."""
    if vault_dir is None:
        vault_str = os.environ.get("IW_VAULT_DIR")
        vault_dir = Path(vault_str).resolve() if vault_str else Path(__file__).resolve().parent.parent.parent / "iw-vault"
    event_log = FileEventLog(log_path=vault_dir / "system" / "events.jsonl")
    return MarkdownStore(vault_dir=vault_dir, event_log=event_log)


def handle_dispatch(store: StoreProtocol, unit_id: str, prompt: str = "", model: str | None = None) -> int:
    """Execute dispatch command: seed work folder and transition unit state (CLICOUR-01)."""
    clean_id = unit_id.strip().upper()
    unit = store.get_unit(clean_id)
    if not unit:
        print(f"Error: Unit '{clean_id}' not found.", file=sys.stderr)
        return 1

    courier = CLICourier(store=store, vault_dir=getattr(store, "vault_dir", None))
    courier.deliver_order(clean_id, {"prompt": prompt, "seed_template": True})

    author = courier.build_cli_author(model_name=model)
    if unit.state == UnitState.READY:
        unit = transition_unit_state(unit, UnitState.DISPATCHED, author=author, store=store)

    print(f"Dispatched {clean_id}: '{unit.title}'")
    print(f"State: {unit.state.value} | Folder: work/{clean_id}/")
    if unit.action_guide:
        print("\n--- Action Guide ---\n" + unit.action_guide + "\n--------------------")
    return 0


def handle_submit(store: StoreProtocol, unit_id: str, deliverable: str, accept: bool = False, model: str | None = None) -> int:
    """Execute submit command: write deliverable and return or accept unit (CLICOUR-02, 03)."""
    clean_id = unit_id.strip().upper()
    unit = store.get_unit(clean_id)
    if not unit:
        print(f"Error: Unit '{clean_id}' not found.", file=sys.stderr)
        return 1

    vault_dir = getattr(store, "vault_dir", Path("."))
    folder = vault_dir / "work" / clean_id
    folder.mkdir(parents=True, exist_ok=True)

    text_to_write = Path(deliverable).read_text(encoding="utf-8") if Path(deliverable).is_file() else deliverable
    (folder / "deliverable.md").write_text(text_to_write, encoding="utf-8")

    courier = CLICourier(store=store, vault_dir=vault_dir)
    author = courier.build_cli_author(model_name=model)

    if accept:
        collect_unit_results(store=store, unit_id=clean_id, author=author)
        print(f"Accepted {clean_id} and materialized findings.")
    else:
        if unit.state == UnitState.READY:
            transition_unit_state(unit, UnitState.DISPATCHED, author=author, store=store)
        transition_unit_state(unit, UnitState.RETURNED, author=author, store=store)
        print(f"Submitted {clean_id}: status set to returned (Awaiting Review).")
    return 0


def handle_status(store: StoreProtocol) -> int:
    """Execute status command: print on-demand summary of work units (CLICOUR-04)."""
    units = store.list_units()
    if not units:
        print("No work units found.")
        return 0

    print("=== Tinkerspace Work Units ===")
    for u in units:
        print(f"[{u.state.value.upper():<10}] {u.id}: {u.title}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI argument parsing and command routing."""
    parser = argparse.ArgumentParser(description="Tinkerspace CLI Work Order Courier")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # dispatch
    p_disp = subparsers.add_parser("dispatch", help="Dispatch a ready unit of work")
    p_disp.add_argument("unit_id", help="Unit ID (e.g. UOW-A01)")
    p_disp.add_argument("--prompt", default="", help="Prompt or task instructions")
    p_disp.add_argument("--model", default=None, help="Agent model name if applicable")

    # submit
    p_sub = subparsers.add_parser("submit", help="Submit deliverable output for a unit")
    p_sub.add_argument("unit_id", help="Unit ID (e.g. UOW-A01)")
    p_sub.add_argument("--deliverable", required=True, help="Deliverable text or filepath")
    p_sub.add_argument("--accept", action="store_true", help="Trigger result collection & accept immediately")
    p_sub.add_argument("--model", default=None, help="Agent model name if applicable")

    # status
    subparsers.add_parser("status", help="List work units grouped by state")

    args = parser.parse_args(argv)
    store = _get_store()

    if args.command == "dispatch":
        return handle_dispatch(store, args.unit_id, prompt=args.prompt, model=args.model)
    elif args.command == "submit":
        return handle_submit(store, args.unit_id, deliverable=args.deliverable, accept=args.accept, model=args.model)
    elif args.command == "status":
        return handle_status(store)
    return 0
