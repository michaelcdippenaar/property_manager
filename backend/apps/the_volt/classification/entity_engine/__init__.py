"""
Entity engine — knows what every entity type needs and what it has.

Three pieces:

  attributes.py
    Canonical attribute registry per EntityType. e.g. PERSONAL has
    id_number, surname, given_names, date_of_birth, residential_address,
    phone, email, tax_number, …. Each attribute carries its data type
    and which document slots can fill it.

  required_docs.py
    For each EntityType, the slot-map of documents required (e.g. for
    FICA compliance, for a property transfer, for a CIPC mandate).
    A slot is e.g. (PERSONAL, ID_DOCUMENT, REQUIRED) or
    (COMPANY, COR14_3, REQUIRED).

  slot_engine.py
    Given an entity + its known documents (Claims with Citations) and a
    target purpose (FICA / TRANSFER / KYC), report:
      - filled_slots
      - empty_slots (and what attributes they would fill)
      - expired_slots (POA > 3 months, etc.)
      - mismatched_slots (claims that disagree)
      - autofill_proposals (entity attribute → blank form slot)

The engine speaks the same Claim/Citation vocabulary as the extractors,
so every "filled" status traces back to a citation in a real document.
"""
