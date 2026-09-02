"""Behaviour tests for Activity Template Library.

Proves ACTLIB-01 through ACTLIB-06 from docs/design/specs/ACTLIB.md:
- ACTLIB-01: Valid schema and required fields on all templates
- ACTLIB-02: Divergent generation enforces zero filtering
- ACTLIB-03: Convergent screening mandates pre-declared criteria and rejected_because edges
- ACTLIB-04: Trade study specifies weighted criteria and sensitivity analysis
- ACTLIB-05: Point design and parts survey specify costing and asset cross-referencing
- ACTLIB-06: Empirical templates specify measurable thresholds and advance kill criteria
"""

from pathlib import Path
import pytest
import yaml

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "content" / "templates"


def load_template(filename: str) -> dict:
    """Helper to parse a template YAML file."""
    path = TEMPLATES_DIR / filename
    assert path.exists(), f"Template {filename} does not exist in {TEMPLATES_DIR}"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_actlib_01_all_templates_conform_to_schema():
    """ACTLIB-01: Each activity template contains required metadata and deliverable schema."""
    yaml_files = list(TEMPLATES_DIR.glob("*.yaml"))
    assert len(yaml_files) >= 12, f"Expected at least 12 activity templates, found {len(yaml_files)}"

    required_keys = {
        "id",
        "title",
        "version",
        "category",
        "target_output",
        "description",
        "prompt_instructions",
        "deliverable_schema",
    }

    for path in yaml_files:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict), f"{path.name} did not parse to a dictionary"
        missing = required_keys - set(data.keys())
        assert not missing, f"{path.name} is missing required keys: {missing}"
        assert "@" in data["id"], f"{path.name} id must be in format name@version"
        assert isinstance(data["version"], int)
        assert "required_sections" in data["deliverable_schema"]


def test_actlib_02_divergent_generation_enforces_unfiltered_generation():
    """ACTLIB-02: Divergent generation explicitly forbids filtering during generation."""
    data = load_template("divergent-generation.v1.yaml")
    assert data["category"] == "divergence"
    instructions = data["prompt_instructions"].lower()
    assert "no filter" in instructions or "not filter" in instructions
    assert "candidate_architectures" in data["deliverable_schema"]["required_sections"]


def test_actlib_03_convergent_screening_mandates_rejection_criteria_and_edges():
    """ACTLIB-03: Convergent screening mandates pre-declared criteria and rejected_because rationales."""
    data = load_template("convergent-screening.v1.yaml")
    assert data["category"] == "convergence"
    instructions = data["prompt_instructions"].lower()
    assert "rejection criteria" in instructions
    assert "rejected_because" in instructions or "rejected_because" in data["description"]
    sections = data["deliverable_schema"]["required_sections"]
    assert "pre_declared_rejection_criteria" in sections
    assert "rejected_candidates" in sections


def test_actlib_04_trade_study_specifies_weighted_criteria_and_sensitivity():
    """ACTLIB-04: Trade study specifies weighted criteria, scoring, and sensitivity pass."""
    data = load_template("trade-study.v1.yaml")
    assert data["category"] == "trade_space"
    sections = data["deliverable_schema"]["required_sections"]
    assert "criteria_and_weights" in sections
    assert "trade_matrix" in sections
    assert "sensitivity_analysis" in sections
    assert "architectural_recommendation" in sections


def test_actlib_05_point_design_and_parts_survey_specify_costing_and_assets():
    """ACTLIB-05: Point design and parts survey require costing and AST-xxx cross-referencing."""
    point = load_template("point-design.v1.yaml")
    assert "bill_of_materials" in point["deliverable_schema"]["required_sections"]
    assert "effort_and_schedule" in point["deliverable_schema"]["required_sections"]

    parts = load_template("parts-and-skills-survey.v1.yaml")
    assert "ast-" in parts["prompt_instructions"].lower() or "ast-" in parts["description"].lower()
    assert "matched_assets" in parts["deliverable_schema"]["required_sections"]
    assert "capability_gaps" in parts["deliverable_schema"]["required_sections"]


def test_actlib_06_empirical_templates_require_advance_kill_criteria():
    """ACTLIB-06: Empirical templates mandate test parameters and advance kill criteria."""
    exp = load_template("experiment-design.v1.yaml")
    assert "advance_kill_criteria" in exp["deliverable_schema"]["required_sections"]

    proto = load_template("prototype-and-measure.v1.yaml")
    assert "advance_kill_threshold" in proto["deliverable_schema"]["required_sections"]

    audit = load_template("assumption-audit.v1.yaml")
    assert "cheapest_test_plan" in audit["deliverable_schema"]["required_sections"]

    heilmeier = load_template("heilmeier-screening.v1.yaml")
    assert "success_exams" in heilmeier["deliverable_schema"]["required_sections"]


def test_actlib_07_prior_art_and_questionstorm_templates():
    """ACTLIB-07: Prior-art survey and questionstorm inquiry templates are present and valid."""
    prior = load_template("prior-art-survey.v1.yaml")
    assert prior["id"] == "prior-art-survey@1"
    assert prior["advances"] == "novel"
    assert "freedom_to_operate_assessment" in prior["deliverable_schema"]["required_sections"]

    qstorm = load_template("questionstorm.v1.yaml")
    assert qstorm["id"] == "questionstorm@1"
    assert "why_root_inquiries" in qstorm["deliverable_schema"]["required_sections"]
    assert "what_if_divergent_reframes" in qstorm["deliverable_schema"]["required_sections"]

