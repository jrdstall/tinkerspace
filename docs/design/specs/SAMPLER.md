# SAMPLER — Behaviour Specification

This specification defines the behavior for Association Pairing Samplers, Distilled Corpus Generation, and Competing Sampling Strategies in Innovator's Workspace.

Governed by `docs/InnovatorsWorkspaceVision_12.md` §13, §14.2, §14.8, §14.17, and `docs/design/DA-14-forward-compatibility.md` Audits 3, 4, 5.

---

## SAMPLER — Behaviour

SAMPLER-01  The association pairing pool includes all nodes of type `friction`, `observation`, `idea`, and `asset` across the corpus.
SAMPLER-02  Corpus distillation extracts a uniform summary structure (`id`, `title`, `type`, `domain`, `tags`, `origin`, `state`, `excerpt`) for all pool records without revealing vault filesystem paths.
SAMPLER-03  Pairing samplers select candidates state-blindly across the pool, including parked and dead ideas.
SAMPLER-04  The `random` sampler strategy acts as the control arm, selecting pairs uniformly at random to establish the empirical baseline yield.
SAMPLER-05  The `anti_similar` sampler selects pairs with maximum structural and domain distance (maximizing cross-domain mechanism transfer).
SAMPLER-06  The `mid_band` sampler selects pairs with moderate structural overlap (adjacent tags/capabilities across distinct domains).
