"""Seed bank loader and storage manager for Creative Exercises.

Layer 2 Domain module. Depends on stdlib and yaml.
Governed by EXERCISE-01 and EXERCISE-07.
"""

from pathlib import Path
import shutil
import tempfile
from typing import Any
import yaml


def get_default_content_dir() -> Path:
    """Return repository content directory path."""
    return Path(__file__).resolve().parents[3] / "content"


def resolve_seed_path(
    seed_name: str,
    vault_dir: Path | None = None,
    content_dir: Path | None = None,
) -> Path:
    """Resolve seed file path with vault taking precedence over content."""
    filename = f"{seed_name}.yaml" if not seed_name.endswith(".yaml") else seed_name
    if vault_dir is not None:
        vault_path = vault_dir / "exercises" / filename
        if vault_path.exists():
            return vault_path
    base_content = content_dir or get_default_content_dir()
    return base_content / "exercises" / filename


def load_seed_bank(
    seed_name: str,
    vault_dir: Path | None = None,
    content_dir: Path | None = None,
) -> dict[str, Any]:
    """Load YAML seed bank file returning parsed dictionary."""
    target_path = resolve_seed_path(seed_name, vault_dir=vault_dir, content_dir=content_dir)
    if not target_path.exists():
        return {}
    content = target_path.read_text(encoding="utf-8")
    parsed = yaml.safe_load(content)
    return parsed if isinstance(parsed, dict) else {}


def save_seed_bank(
    vault_dir: Path,
    seed_name: str,
    data: dict[str, Any],
) -> Path:
    """Atomically save seed data to vault exercises folder."""
    filename = f"{seed_name}.yaml" if not seed_name.endswith(".yaml") else seed_name
    target_dir = vault_dir / "exercises"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / filename

    raw_yaml = yaml.dump(data, sort_keys=False, allow_unicode=True)
    with tempfile.NamedTemporaryFile("w", dir=target_dir, delete=False, encoding="utf-8") as tf:
        tf.write(raw_yaml)
        temp_path = Path(tf.name)

    temp_path.replace(target_file)
    return target_file


def reset_vault_seeds(
    vault_dir: Path,
    content_dir: Path | None = None,
) -> list[str]:
    """Reset all vault exercises to factory defaults by copying content files."""
    base_content = content_dir or get_default_content_dir()
    src_dir = base_content / "exercises"
    target_dir = vault_dir / "exercises"
    target_dir.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    if src_dir.exists():
        for item in src_dir.glob("*.yaml"):
            dest = target_dir / item.name
            shutil.copy2(item, dest)
            copied.append(item.name)
    return copied


def load_done_exercises(vault_dir: Path | None) -> set[str]:
    """Load set of completed/retired exercise prompt texts (EXERCISE-09)."""
    if vault_dir is None:
        return set()
    target_path = vault_dir / "exercises" / "done.yaml"
    if not target_path.exists():
        return set()
    try:
        content = target_path.read_text(encoding="utf-8")
        parsed = yaml.safe_load(content)
        if isinstance(parsed, dict) and "done" in parsed:
            return {str(item).strip() for item in parsed["done"] if str(item).strip()}
        if isinstance(parsed, list):
            return {str(item).strip() for item in parsed if str(item).strip()}
    except Exception:
        pass
    return set()


def save_done_exercise(vault_dir: Path, prompt_text: str) -> None:
    """Append a prompt text to vault exercises done.yaml atomically (EXERCISE-09)."""
    clean = prompt_text.strip()
    if not clean:
        return
    existing = load_done_exercises(vault_dir)
    existing.add(clean)
    target_dir = vault_dir / "exercises"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / "done.yaml"
    data = {"done": sorted(existing)}
    raw_yaml = yaml.dump(data, sort_keys=False, allow_unicode=True)
    with tempfile.NamedTemporaryFile("w", dir=target_dir, delete=False, encoding="utf-8") as tf:
        tf.write(raw_yaml)
        temp_path = Path(tf.name)
    temp_path.replace(target_file)


def clear_done_exercises(vault_dir: Path) -> None:
    """Clear all completed exercises from vault done.yaml (EXERCISE-09)."""
    target_file = vault_dir / "exercises" / "done.yaml"
    if target_file.exists():
        target_file.unlink()
