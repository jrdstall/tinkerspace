# QSTORM — Behaviour Specification

This specification defines the behavior for Questionstorming sessions, Berger questioning moves, question-to-question relations, and question node generation in Innovator's Workspace.

Governed by `docs/InnovatorsWorkspaceVision_12.md` §12, §14.2, §14.8, and `docs/design/DA-03-data-model.md`.

---

## QSTORM — Behaviour

QSTORM-01  A Questionstorm is an analysis session attached to one subject node (`friction` or `idea`) that generates a batch of typed `question` nodes (`QUE-xxx`).
QSTORM-02  Every Question node records a `form` (`"open"` or `"closed"`), an `importance` (`"high"`, `"medium"`, or `"low"`), and a state (`"held_open"` or `"answered"`).
QSTORM-03  `held_open` is a first-class, valid state and is never presented or counted as debt or a backlog requiring reduction.
QSTORM-04  Every generated Question node establishes a `questions` directional edge pointing to the subject node.
QSTORM-05  Question-to-question relationships are supported across 5 canonical edge relations: `broadens`, `narrows`, `presupposes`, `reframes`, and `sibling`.
QSTORM-06  Berger's questioning moves (Why, Constraint Removal, Inversion, How Might We, Dissenter) generate structured prompt stems and categorize question origin.
QSTORM-07  Transforming a question between open and closed forms produces a new linked Question node with a `reframes` or `narrows` edge connecting to the source question.
QSTORM-08  Question creation and relationship linking stamp author attribution and append audit records to `events.jsonl`.
