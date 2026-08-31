# MATBOARD — Behaviour Specification

This specification defines the behavior for the visual Maturity Board and Worth Matrix surfaces in Innovator's Workspace.

Governed by `docs/InnovatorsWorkspaceVision_12.md` §11, §14.2, §14.8, §14.15, and `docs/design/specs/ASSESS.md`.

---

## MATBOARD — Behaviour

MATBOARD-01  The Maturity Board (`/maturity`) presents all ideas in the corpus categorized into 5 sequential CML progression columns (1: Spark, 2: Plausible, 3: Explored, 4: Chosen, 5: Real).
MATBOARD-02  Each idea card on the board visually renders the 4-score equalizer breakdown across Novel, Works, Reach, and Story.
MATBOARD-03  If an idea specifies a `concept_graphic`, the card displays a compressed visual thumbnail tile at the top of the card.
MATBOARD-04  The laggard score holding back the CML is highlighted in a distinct callout with a 1-click action button that instantiates or suggests the targeted advancement activity.
MATBOARD-05  The Maturity Board provides filtering by domain, screening verdict (pursue, park, let_go), worth ratings, and sorting by lowest laggard score.
MATBOARD-06  The Maturity Board supports a Worth Matrix view toggle categorizing ideas into Passion Projects (High me / Low others), High Impact (High me / High others), and The Trap (Low me / High others).
