# CLICOUR — Subsystem Behaviour Specifications

CLICOUR-01  CLI `dispatch` command transitions unit to `dispatched`, seeds work folder with `prompt.md`/`deliverable.md`, and prints Action Guide instructions to stdout.
CLICOUR-02  CLI `submit` command writes output files into `work/<UOW-id>/`, stamps attribution with `courier: "cli"`, and transitions unit state to `returned`.
CLICOUR-03  CLI `submit` with `--accept` flag triggers the full collection pipeline and transitions unit directly to `accepted`.
CLICOUR-04  CLI `status` / `list` command queries the vault on-demand and prints units grouped by lifecycle state.
CLICOUR-05  `CLICourier` adapter satisfies `CourierProtocol` in `iw/contracts/courier.py`.
