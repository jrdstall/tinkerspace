# ASSESS — Behaviour Specification

This specification defines the behavior for Idea Maturity Assessment, CML calculation, Worth ratings, Screening verdicts, and Concept Graphic identification in Innovator's Workspace.

Governed by `docs/InnovatorsWorkspaceVision_12.md` §11, §14.2, §14.8, §14.15, and `docs/design/DA-03-data-model.md`.

---

## ASSESS — Behaviour

ASSESS-01  An assessment records 4 maturity scores (`novel`, `works`, `reach`, `story`), each scored on an integer scale from 1 to 5.
ASSESS-02  An idea's Concept Maturity Level (CML) is the integer minimum of its four maturity scores (`cml = min(scores.values())`).
ASSESS-03  An unassessed idea cleanly defaults to CML 1 without requiring score fields to be present.
ASSESS-04  An assessment records two independent worth ratings (`worth_to_me` and `worth_to_others`), each rated as `"high"`, `"medium"`, or `"low"`.
ASSESS-05  Worth ratings never modify or lower the CML; they are tracked as independent orthogonal dimensions.
ASSESS-06  A screening verdict is one of `"pursue"`, `"park"`, or `"let_go"`, accompanied by a recorded text reason.
ASSESS-07  Laggard scores are identified as the score key(s) equal to the minimum score, mapping directly to recommended advancement activities.
ASSESS-08  An idea may specify a `concept_graphic` designating a relative file path or artifact ID for its primary visual representation, which renders as a hero graphic on node detail.
