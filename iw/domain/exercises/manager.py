"""Seed management, LLM prompt templating, and import facilities.

Layer 2 Domain module. Depends only on stdlib and yaml.
Governed by EXERCISE-07.
"""

from pathlib import Path
from typing import Any
import yaml

from iw.domain.exercises.loader import load_seed_bank, reset_vault_seeds, save_seed_bank


def _triad_prompt_template(domain: str, count: int) -> str:
    """Template for 3-word triad nouns prompt."""
    return (
        f"Please generate {count} highly vivid, physical, sensory, or off-the-wall nouns "
        f"for creative lateral thinking. Domain focus: {domain}.\n\n"
        "Return ONLY a clean YAML block structured as follows:\n"
        "```yaml\n"
        "organic:\n"
        "  - barnacle\n"
        "mechanical_tools:\n"
        "  - flywheel\n"
        "technology:\n"
        "  - lidar sensor\n"
        "domestic_apparel:\n"
        "  - scrunchie\n"
        "off_the_wall_sensory:\n"
        "  - sourdough starter\n"
        "frontier_scifi:\n"
        "  - faraday cage\n"
        "```\n"
        "Rule: Every noun must be concrete and tangible (NO abstract concepts like 'system' or 'dynamic')."
    )


def _paradox_prompt_template(domain: str, count: int) -> str:
    """Template for paradoxical constraint prompt."""
    return (
        f"Generate {count} punchy paradoxical negative constraints (everyday objects stripped of "
        f"their defining affordance). Focus domain: {domain}.\n\n"
        "Crucial Rule: Phrase like a human inventor chatting in a workshop, NOT an AI bureaucrat. "
        "Say 'A refrigerator that doesn't cool', NOT 'An appliance that cannot perform its primary function'.\n\n"
        "Return ONLY a clean YAML block formatted as:\n"
        "```yaml\n"
        "curated:\n"
        "  - \"A mower that doesn't mow\"\n"
        "  - \"An oven that doesn't heat\"\n"
        "  - \"A clock that doesn't tell time\"\n"
        "twists:\n"
        "  - \"A microwave that instantly flash-freezes\"\n"
        "```"
    )


def _what_if_prompt_template(count: int) -> str:
    """Template for cross-domain what-if prompt."""
    return (
        f"Please generate {count} cross-domain 'What If?' pairs pairing unexpected organizations with institutions.\n\n"
        "Return ONLY a clean YAML block formatted as:\n"
        "```yaml\n"
        "entities:\n"
        "  - IKEA\n"
        "  - NASA JPL\n"
        "systems:\n"
        "  - an elementary school\n"
        "  - a hospital emergency room\n"
        "curated:\n"
        "  - \"What if IKEA ran an elementary school?\"\n"
        "```"
    )


def build_seed_generation_prompt(
    exercise_type: str = "triads",
    focus_domain: str = "any",
    count: int = 20,
) -> str:
    """Construct structured generation prompt for external LLMs (EXERCISE-07)."""
    t = exercise_type.lower().strip()
    if "triad" in t or "noun" in t:
        return _triad_prompt_template(focus_domain, count)
    if "paradox" in t or "constraint" in t:
        return _paradox_prompt_template(focus_domain, count)
    return _what_if_prompt_template(count)


def _merge_seed_dicts(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    """Merge incoming dictionary into existing dictionary without duplicate list items."""
    merged: dict[str, Any] = dict(existing)
    for key, val in incoming.items():
        if key not in merged:
            merged[key] = val
        elif isinstance(merged[key], list) and isinstance(val, list):
            seen = set()
            new_list = []
            for item in merged[key] + val:
                normalized = str(item).strip().lower()
                if normalized not in seen:
                    seen.add(normalized)
                    new_list.append(item)
            merged[key] = new_list
        else:
            merged[key] = val
    return merged


def import_seed_yaml(
    vault_dir: Path,
    seed_name: str,
    yaml_text: str,
    mode: str = "replace",
) -> dict[str, Any]:
    """Parse and save incoming YAML seed data in replace or merge mode (EXERCISE-07)."""
    raw = yaml_text.strip()
    if raw.startswith("```yaml"):
        raw = raw.replace("```yaml", "", 1)
    if raw.startswith("```"):
        raw = raw.replace("```", "", 1)
    if raw.endswith("```"):
        raw = raw[:-3].strip()

    parsed = yaml.safe_load(raw)
    if not isinstance(parsed, dict):
        raise ValueError("Invalid YAML: top-level element must be a mapping/dictionary")

    target_name = seed_name.replace(".yaml", "").strip()
    if mode == "merge":
        existing = load_seed_bank(target_name, vault_dir=vault_dir)
        final_data = _merge_seed_dicts(existing, parsed)
    else:
        final_data = parsed

    saved_path = save_seed_bank(vault_dir, target_name, final_data)
    total_items = sum(len(v) for v in final_data.values() if isinstance(v, list))
    return {
        "status": "ok",
        "seed_name": target_name,
        "mode": mode,
        "path": str(saved_path),
        "total_items": total_items,
    }


def reset_seeds_to_defaults(vault_dir: Path) -> list[str]:
    """Reset all vault seed files to factory defaults (EXERCISE-07)."""
    return reset_vault_seeds(vault_dir)
