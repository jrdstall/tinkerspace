# EXERCISE — Behaviour Specification

This specification defines the behavior for Creative Exercises, Combinatorial Seed Engines, Repeatable Seed Management (Flush/Replace/Merge), and Frictionless Inbox Capture in Innovator's Workspace.

Governed by `docs/InnovatorsWorkspaceVision_12.md` §13, §14.2, and `docs/design/specs/CAPTURE.md`.

---

## EXERCISE — Behaviour

EXERCISE-01  The exercise loader resolves seed banks from `vault/exercises/`, falling back to built-in template seed files in `content/exercises/`.
EXERCISE-02  The Triad generator samples 3 concrete, evocative nouns across mutually distinct categories, including organic/nature, mechanical/tools, technology/digital, domestic/apparel, off-the-wall/sensory, and frontier/sci-fi.
EXERCISE-03  The Paradoxical Constraint generator samples negative functional constraints that negate the defining affordance of common objects or systems.
EXERCISE-04  The Cross-Domain "What If?" generator pairs iconic organizational archetypes and philosophies with alien institutions and systems.
EXERCISE-05  The Biomimicry and Assumption Inversion generators provide structured lateral-thinking provocations based on biological adaptations and orthogonal dogmas.
EXERCISE-06  The Vault Cross-Pollination generator samples active ideas or frictions from the vault corpus and pairs them with creative seeds.
EXERCISE-07  The Seed Manager generates pre-formatted LLM generation prompts and supports YAML import with both flush-and-replace and merge modes, as well as one-click reset to factory defaults.
EXERCISE-08  The Capture action accepts scratchpad reflections, formats them with exercise prompt provenance metadata, and appends them to the triage inbox via the `creative-exercises` inlet.
