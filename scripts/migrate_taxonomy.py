"""Migration script to normalize taxonomy, clean tags, and strip keywords.

Applies the approved 10 canonical domains and cleans redundant tags across the vault.
"""

import argparse
from pathlib import Path
from typing import Any

from iw.contracts.models import Author, AuthorKind, Node
from iw.core.store import MarkdownStore

CANONICAL_DOMAINS = [
    "Computing & Architecture",
    "Space Systems",
    "Defense & C2",
    "Mobility & Transportation",
    "Creativity & Expression",
    "Enterprise & Organization",
    "Health & Performance",
    "Living & Preparedness",
    "Learning & Education",
    "Tools & Prototyping",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate Tinkerspace taxonomy and clean tags.")
    parser.add_argument("--vault", type=str, default=r"C:\Users\jrdst\software\IW\vault", help="Vault directory path")
    parser.add_argument("--apply", action="store_true", help="Apply updates to disk (defaults to dry-run)")
    return parser.parse_args()


def classify_node(node: Node) -> str:
    """Classify a node into one of the 10 canonical domains."""
    nid = node.id
    if nid in ["AST-A01", "AST-A02", "AST-A03"]:
        return "Tools & Prototyping"
    if nid in ["AST-A04", "AST-A05", "ART-A01", "FRI-A04", "FRI-A21", "FRI-A40", "FRI-A41", "FRI-A42", "FRI-A43", "FRI-A44", "IDEA-A02", "IDEA-A11", "IDEA-A25", "IDEA-A33", "IDEA-A35", "QUE-A02"]:
        return "Mobility & Transportation"
    if nid in ["FRI-A12", "IDEA-A09", "IDEA-A39", "IDEA-A43"] or (nid.startswith("QUE-A") and int(nid[5:]) in range(9, 22)):
        return "Space Systems"
    if nid in ["FRI-A08", "FRI-A31", "FRI-A59", "IDEA-A34", "IDEA-A36", "IDEA-A37", "IDEA-A41", "IDEA-A46", "QUE-A06"]:
        return "Defense & C2"
    if nid in ["FRI-A09", "FRI-A10", "FRI-A16", "FRI-A19", "FRI-A25", "FRI-A27", "FRI-A29", "FRI-A45", "FRI-A46", "IDEA-A05", "IDEA-A07", "IDEA-A10", "IDEA-A40", "OBS-A01"]:
        return "Enterprise & Organization"
    if nid in ["FRI-A11", "FRI-A28", "FRI-A30", "FRI-A35", "FRI-A52", "FRI-A60", "FRI-A61", "FRI-A62", "FRI-A63", "IDEA-A04", "IDEA-A06", "IDEA-A30", "IDEA-A32", "IDEA-A38", "IDEA-A47", "QUE-A04", "QUE-A05"]:
        return "Creativity & Expression"
    if nid in ["FRI-A15", "FRI-A48", "FRI-A49", "IDEA-A08", "IDEA-A12", "IDEA-A14", "IDEA-A15", "IDEA-A20", "IDEA-A22", "IDEA-A31"]:
        return "Health & Performance"
    if nid in ["IDEA-A17", "IDEA-A19", "QUE-A03"]:
        return "Learning & Education"
    if nid in ["FRI-A01", "FRI-A03", "FRI-A13", "FRI-A17", "FRI-A20", "FRI-A32", "FRI-A33", "FRI-A51", "IDEA-A13", "IDEA-A16", "IDEA-A18", "IDEA-A21", "IDEA-A24", "IDEA-A27", "IDEA-A28", "IDEA-A42"]:
        return "Living & Preparedness"
    return "Computing & Architecture"


def clean_node_tags(node: Node, target_domain: str) -> list[str]:
    """Normalize tags: drop type/domain echoes, split space-separated tokens, normalize kebab-case."""
    raw_tokens: list[str] = []
    for t in node.tags:
        cleaned = t.strip().lstrip("#").lower()
        if " " in cleaned:
            for sub in cleaned.split():
                if sub.strip():
                    raw_tokens.append(sub.strip())
        elif cleaned:
            raw_tokens.append(cleaned)

    # Exclusions
    drop_words = {
        node.type.lower(),
        "question", "artifact", "asset", "idea", "friction", "observation",
        "space", "compute", "computing", "c2", "defense", "health", "creativity",
        "cycling", "automotive", "enterprise", "consumer", "lifestyle",
    }
    filtered: list[str] = []
    for token in raw_tokens:
        tok = token.replace("_", "-")
        if tok not in drop_words and tok not in filtered:
            filtered.append(tok)
    return filtered


def run_migration(vault_dir: Path, apply: bool) -> None:
    event_log = None
    events_file = vault_dir / "events.jsonl"
    if events_file.exists():
        from iw.core.events import FileEventLog
        event_log = FileEventLog(events_file)

    store = MarkdownStore(vault_dir, event_log=event_log)
    nodes = store.list_nodes()
    author = Author(kind=AuthorKind.HUMAN, courier="taxonomy-migration")
    updated_count = 0

    print(f"Scanning {len(nodes)} nodes in {vault_dir} (Apply={apply})...")
    for node in sorted(nodes, key=lambda n: (n.type, n.id)):
        target_domain = classify_node(node)
        cleaned_tags = clean_node_tags(node, target_domain)
        attrs = dict(node.attrs)
        had_keywords = "keywords" in attrs
        if had_keywords:
            del attrs["keywords"]

        changed = (node.domain != target_domain) or (node.tags != cleaned_tags) or had_keywords
        if changed:
            updated_count += 1
            if apply:
                node.domain = target_domain
                node.tags = cleaned_tags
                node.attrs = attrs
                store.write_node(node, author=author)

    if apply and (vault_dir / ".git").exists() and updated_count > 0:
        import subprocess
        subprocess.run(["git", "add", "-A"], cwd=vault_dir, check=False)
        subprocess.run(
            ["git", "commit", "-m", f"chore(taxonomy): migrate {updated_count} nodes to canonical domains and clean tags"],
            cwd=vault_dir,
            check=False,
        )

    mode_label = "Applied" if apply else "Found changes for"
    print(f"Done. {mode_label} {updated_count} of {len(nodes)} nodes.")


if __name__ == "__main__":
    args = parse_args()
    run_migration(Path(args.vault), apply=args.apply)
