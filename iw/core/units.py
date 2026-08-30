"""Core unit-of-work serialization and filesystem storage helpers.

Handles reading, writing, and scanning structured unit.yaml files inside work/UOW-xxx/.
"""

from pathlib import Path
import tempfile
from typing import Any
import yaml

from iw.contracts.models import UnitOfWork, UnitState


def serialize_unit(unit: UnitOfWork) -> dict[str, Any]:
    """Serialize a UnitOfWork dataclass into a clean dictionary."""
    data: dict[str, Any] = {
        "id": unit.id.upper(),
        "title": unit.title,
        "activity": unit.activity,
        "state": unit.state.value if isinstance(unit.state, UnitState) else str(unit.state),
        "subject_ids": unit.subject_ids,
    }
    if unit.workflow_id:
        data["workflow_id"] = unit.workflow_id
    if unit.input_artifacts:
        data["input_artifacts"] = unit.input_artifacts
    if unit.assignee:
        data["assignee"] = unit.assignee
    if unit.deliverable:
        data["deliverable"] = unit.deliverable
    if unit.estimate:
        data["estimate"] = unit.estimate
    if unit.template:
        data["template"] = unit.template
    if unit.action_guide:
        data["action_guide"] = unit.action_guide
    return data


def deserialize_unit(data: dict[str, Any]) -> UnitOfWork:
    """Deserialize a dictionary into a UnitOfWork dataclass."""
    raw_state = data.get("state", "ready")
    state = UnitState(raw_state) if raw_state in UnitState._value2member_map_ else UnitState.READY
    return UnitOfWork(
        id=str(data.get("id", "")).upper(),
        title=str(data.get("title", "")),
        activity=str(data.get("activity", "")),
        state=state,
        subject_ids=list(data.get("subject_ids", [])),
        workflow_id=data.get("workflow_id"),
        input_artifacts=list(data.get("input_artifacts", [])),
        assignee=dict(data.get("assignee", {})),
        deliverable=dict(data.get("deliverable", {})),
        estimate=dict(data.get("estimate", {})),
        template=data.get("template"),
        action_guide=str(data.get("action_guide", "")),
    )


def read_unit_yaml(file_path: Path) -> UnitOfWork | None:
    """Read a unit.yaml file from disk without caching."""
    if not file_path.exists() or not file_path.is_file():
        return None
    try:
        content = file_path.read_text(encoding="utf-8")
        raw_data = yaml.safe_load(content)
        if isinstance(raw_data, dict) and "id" in raw_data:
            return deserialize_unit(raw_data)
        return None
    except Exception:
        return None


def atomic_write_unit_yaml(folder_path: Path, unit: UnitOfWork) -> Path:
    """Atomically write unit.yaml into the specified work unit folder."""
    folder_path.mkdir(parents=True, exist_ok=True)
    target_file = folder_path / "unit.yaml"
    data = serialize_unit(unit)
    yaml_content = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=str(folder_path),
        delete=False,
        suffix=".tmp",
    ) as tmp:
        tmp.write(yaml_content)
        temp_path = Path(tmp.name)

    temp_path.replace(target_file)
    return target_file


def scan_vault_units(vault_dir: Path) -> list[UnitOfWork]:
    """Scan the vault work directory and load all unit.yaml files."""
    work_dir = vault_dir / "work"
    if not work_dir.exists() or not work_dir.is_dir():
        return []

    units: list[UnitOfWork] = []
    for item in work_dir.iterdir():
        if item.is_dir() and item.name.upper().startswith("UOW-"):
            unit_file = item / "unit.yaml"
            loaded = read_unit_yaml(unit_file)
            if loaded is not None:
                units.append(loaded)
    return units
