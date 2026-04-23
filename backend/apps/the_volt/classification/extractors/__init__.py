"""Identity-document extractors for The Volt.

Each extractor takes a file (image or PDF page), detects the document
layout (Smart ID Card, Green ID Book, Birth Certificate, Passport,
Driver's Licence) and extracts the structured identity fields with
field-level confidence.

Identity-First doctrine: ID-class documents are processed BEFORE any
other document group, become the root-of-trust for a NaturalPersonSilo,
and are validated against a 3rd-party register (DHA / ContactAble / etc.)
before any related party documents are linked to that silo.
"""
