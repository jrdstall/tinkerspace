# EXTINT — Subsystem Behaviour Specifications

EXTINT-01  External node ingestion parses external markdown text and imports it into the local vault as a typed node.
EXTINT-02  Non-colliding source IDs are preserved intact without re-allocating a new ID.
EXTINT-03  Colliding source IDs allocate the next local sequential ID, preserve the original ID in `attrs['foreign_id']`, and record provenance.
EXTINT-04  Ingestion automatically appends the foreign vault tag `vault:<source_name>` to the node's tags.
EXTINT-05  Ingestion remaps inter-note edge references when a set of foreign nodes with colliding IDs are imported together.
