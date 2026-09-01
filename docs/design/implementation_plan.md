# Tinkerspace (Innovator's Workspace) Development Plan

This plan operationalizes **`docs/DesignPhasePlan_2.md`** and **`docs/InnovatorsWorkspaceVision_12.md`** into an actionable, chunked execution roadmap.

Every task is sized for a single work session (1 block ≈ 90 min, ≤400 lines of code for build slices) and assigned to either **Jared (Human)** or **Antigravity / Claude (AI)**.

---

## Operating Rules & Principles

1. **AI Task Status Rule (§01)**: The AI may mark tasks `in work`. Only **Jared** marks tasks `done` after reviewing outputs.
2. **Review Protocol (§09)**:
   - Run it first.
   - Read behaviour spec → test → interface → implementation.
   - If a test does not read as a clear English specification, reject the slice.
   - Check against the component map (DA-04).
   - Enforce Python limits: file ≤ 200 lines, function ≤ 40 lines, comprehension nesting ≤ 1.
3. **No Mocking the Store**: Store tests always run against real markdown files in temporary directories.
4. **Simulate the Other Writer**: The store must always handle files written or modified outside the service (by tablet sync, text editor, or git).

---

## Phase 4 Build Slices (B4-1 through B4-7) — Make It Mature

| Slice | Status | Focus | Deliverables & Verification |
|---|:--:|---|---|
| **B4-1** | `in work` | Full Activity Template Library | All 10 core activity templates authored in `content/templates/` (`divergent-generation@1`, `convergent-screening@1`, `trade-study@1`, `point-design@1`, `experiment-design@1`, `parts-and-skills-survey@1`, `story-draft@1`, `assumption-audit@1`, `prototype-and-measure@1`, `heilmeier-screening@1`). Validated by `ACTLIB.md` & `test_activity_library.py`. |
| **B4-2** | `in work` | Bookkeeper CAS Adapter | SHA-256 content-addressed storage adapter for immutable binary storage and derived renditions. Validated by `BOOKKEEP.md`, `test_bookkeeper_contract.py`, and `test_bookkeeper_storage.py`. |
| **B4-3** | `in work` | Content Extractors | Pluggable format extractors (Text, HTML, PDF, Image) and registry router. Validated by `EXTRACT.md`, `test_extractor_contract.py`, and `test_extractors.py`. |
| **B4-4** | `in work` | Scout Standing Interests | On-demand staleness evaluation and recommendation engine without background threads/daemons. Validated by `SCOUT.md` and `test_scout_service.py`. |
| **B4-5** | `in work` | Maturation Planner Service | Domain planner service translating maturity scores/laggards into ordered, sized, DAG-linked workflows. Validated by `PLANNER.md` and `test_maturation_planner.py`. |
| **B4-6** | `in work` | Web UI: Planner & Scout | Interactive Maturation Planner view (`/ideas/{id}/plan`) and Scout Recommended Activities panel. Validated by `PLANNERUI.md` and `test_planner_and_scout_web.py`. |
| **B4-7** | `in work` | CML 1→5 Lifecycle & A-Team Verification | End-to-end integration test validating full maturation progression from Spark to Real with A-Team discipline. Validated by `MATURITY.md` and `test_cml_maturation_e2e.py`. |
