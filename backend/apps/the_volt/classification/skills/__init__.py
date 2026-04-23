"""
Per-document-type extraction skills.

Each subpackage is a self-contained "micro-service" for ONE identity
document type:
  - SKILL.md       — capability description (also loadable by sub-agents)
  - prompt.md      — system prompt used when running the local agent
  - layout.py      — bbox map (where every field lives)
  - tools.py       — callable tools the local agent uses
  - validators.py  — type-specific validators (Luhn, DOB cross-check, …)
  - examples/      — gold-labelled inputs/outputs for regression tests
  - run.py         — local-agent runner (the entry point)

The orchestrator (`classification.skills.router`) detects the document
type and dispatches to exactly ONE skill. Skills know nothing about
each other.

Vectorisation rule (Identity-First doctrine):
  • The raw ID image is NEVER vectorised.
  • Only the extracted FIELD VALUES (id_number, surname, names, dob, …)
    and the small bbox CROPS (photo, signature, MRZ) are persisted.
  • Each crop is stored as a separate VoltDocumentChunk with metadata
    {field_name, doc_type, person_silo_id} so retrieval is field-typed.
"""
