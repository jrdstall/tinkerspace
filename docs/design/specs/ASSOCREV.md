# ASSOCREV — Behaviour Specification

This specification defines the behavior for the rapid Association Review Deck, keyboard triage shortcuts (`K` / `D`), Idea node promotion with lineage, and sampler telemetry in Innovator's Workspace.

Governed by `docs/InnovatorsWorkspaceVision_12.md` §13, §14.2, §14.8, §14.17, and `docs/design/specs/ASSOC.md`.

---

## ASSOCREV — Behaviour

ASSOCREV-01  The Association Review surface (`/associations`) presents generated proposals sequentially as an interactive review deck.
ASSOCREV-02  Pressing `K` (Keep) or clicking the Keep action promotes the proposal into an active `idea` node with bidirectional `derived_from` lineage edges pointing to both parent nodes, logs the keeper telemetry, and advances the deck.
ASSOCREV-03  Pressing `D` (Discard) or clicking the Discard action archives the candidate, records discard telemetry for the sampler strategy, and advances to the next proposal.
ASSOCREV-04  The proposal review card displays parent node titles, domain badges, Stage 1 Abstract Mechanism, Stage 2 Transfer Proposal, and the Adversarial Judge refutation verdict & strongest objection.
ASSOCREV-05  When the review deck is empty, the surface displays an empty state with a 1-click sampler trigger to generate a fresh batch of candidate pairs using a selectable strategy (`random`, `anti_similar`, `mid_band`).
ASSOCREV-06  Sampler yield telemetry (total sampled, kept, discarded, and empirical yield percentage per sampler strategy) is displayed on the review surface.
