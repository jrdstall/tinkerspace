"""Core workflow DAG serialization and filesystem storage helpers.

Handles reading, writing, and scanning structured workflow.yaml files inside work/WFL-xxx/.
"""

from datetime import datetime, timezone
from pathlib import Path
import tempfile
from typing import Any
import yaml

from iw.contracts.models import Workflow


def serialize_workflow(workflow: Workflow) -> dict[str, Any]:
    """Serialize a Workflow dataclass into a clean dictionary."""
    clean_deps: dict[str, list[str]] = {}
    for k, v in workflow.dependencies.items():
        clean_deps[k.upper()] = [p.upper() for p in v]

    data: dict[str, Any] = {
        "id": workflow.id.upper(),
        "title": workflow.title,
        "subject_ids": workflow.subject_ids,
        "unit_ids": [u.upper() for u in workflow.unit_ids],
        "dependencies": clean_deps,
        "created": workflow.created.isoformat() if isinstance(workflow.created, datetime) else str(workflow.created),
    }
    if workflow.template_id:
        data["template_id"] = workflow.template_id
    return data


def deserialize_workflow(data: dict[str, Any]) -> Workflow:
    """Deserialize a dictionary into a Workflow dataclass."""
    raw_created = data.get("created")
    if isinstance(raw_created, str):
        try:
            created_dt = datetime.fromisoformat(raw_created)
        except Exception:
            created_dt = datetime.now(timezone.utc)
    elif isinstance(raw_created, datetime):
        created_dt = raw_created
    else:
        created_dt = datetime.now(timezone.utc)

    raw_deps = data.get("dependencies", {})
    clean_deps: dict[str, list[str]] = {}
    if isinstance(raw_deps, dict):
        for k, v in raw_deps.items():
            if isinstance(v, list):
                clean_deps[str(k).upper()] = [str(x).upper() for x in v]
            else:
                clean_deps[str(k).upper()] = []

    return Workflow(
        id=str(data.get("id", "")).upper(),
        title=str(data.get("title", "")),
        subject_ids=list(data.get("subject_ids", [])),
        unit_ids=[str(u).upper() for u in data.get("unit_ids", [])],
        dependencies=clean_deps,
        created=created_dt,
        template_id=data.get("template_id"),
    )


def read_workflow_yaml(file_path: Path) -> Workflow | None:
    """Read a workflow.yaml file from disk without caching."""
    if not file_path.exists() or not file_path.is_file():
        return None
    try:
        content = file_path.read_text(encoding="utf-8")
        raw_data = yaml.safe_load(content)
        if isinstance(raw_data, dict) and "id" in raw_data:
            return deserialize_workflow(raw_data)
        return None
    except Exception:
        return None


def atomic_write_workflow_yaml(folder_path: Path, workflow: Workflow) -> Path:
    """Atomically write workflow.yaml into the specified work folder."""
    folder_path.mkdir(parents=True, exist_ok=True)
    target_file = folder_path / "workflow.yaml"
    data = serialize_workflow(workflow)
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


def scan_vault_workflows(vault_dir: Path) -> list[Workflow]:
    """Scan the vault work directory and load all workflow.yaml files."""
    work_dir = vault_dir / "work"
    if not work_dir.exists() or not work_dir.is_dir():
        return []

    workflows: list[Workflow] = []
    for item in work_dir.iterdir():
        if item.is_dir() and item.name.upper().startswith("WFL-"):
            wfl_file = item / "workflow.yaml"
            loaded = read_workflow_yaml(wfl_file)
            if loaded is not None:
                workflows.append(loaded)
    return workflows
