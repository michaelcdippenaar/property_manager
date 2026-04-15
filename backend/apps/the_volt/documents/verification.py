"""
The Volt — document verification service.

Records verification metadata against a DocumentVersion:
  - self-attestation (owner declares it is theirs)
  - commissioner-of-oaths signed certified copy (encrypted upload)
  - third-party / official-source verification (external API confirmation)
  - expiry tracking

The certified copy (commissioner-signed) is stored as a separate encrypted
file alongside the original, so you always have:
  1. The original uploaded file (encrypted)
  2. The certified copy bearing the Commissioner of Oaths stamp (encrypted)
"""
from __future__ import annotations

import logging
import mimetypes
from typing import Optional

from django.core.files.base import ContentFile
from django.utils import timezone

from apps.the_volt.encryption.utils import encrypt_bytes, hash_bytes
from .models import DocumentVersion, DocumentVerification, VerificationStatus

logger = logging.getLogger(__name__)


def _get_or_create(version: DocumentVersion) -> DocumentVerification:
    obj, _ = DocumentVerification.objects.get_or_create(document_version=version)
    return obj


def self_attest(
    version: DocumentVersion,
    *,
    verified_by: str,
    expiry_date=None,
    metadata: Optional[dict] = None,
) -> DocumentVerification:
    """Owner declares the document is authentic (lowest trust tier)."""
    v = _get_or_create(version)
    v.verification_status = VerificationStatus.SELF_ATTESTED
    v.verification_source = "owner_self_attestation"
    v.verified_at = timezone.now()
    v.verified_by = verified_by
    if expiry_date:
        v.expiry_date = expiry_date
    if metadata:
        v.verification_metadata = {**(v.verification_metadata or {}), **metadata}
    v.save()
    return v


def record_commissioner_sign(
    version: DocumentVersion,
    *,
    commissioner_name: str,
    commissioner_reference: str,
    certified_copy_bytes: bytes,
    certified_copy_filename: str,
    signed_at=None,
    expiry_date=None,
    metadata: Optional[dict] = None,
) -> DocumentVerification:
    """Attach a Commissioner of Oaths certified copy (encrypted) + metadata."""
    v = _get_or_create(version)
    owner_id = version.document.entity.vault_id

    sha256 = hash_bytes(certified_copy_bytes)
    encrypted = encrypt_bytes(certified_copy_bytes, owner_id)

    v.certified_copy_file.save(
        f"{version.version_number}.enc",
        ContentFile(encrypted),
        save=False,
    )
    v.certified_copy_sha256 = sha256
    v.certified_copy_original_filename = certified_copy_filename
    v.commissioner_name = commissioner_name
    v.commissioner_reference = commissioner_reference
    v.commissioner_signed_at = signed_at or timezone.now()
    v.verification_status = VerificationStatus.COMMISSIONER_SIGNED
    v.verification_source = f"commissioner:{commissioner_reference}"
    v.verified_at = timezone.now()
    v.verified_by = commissioner_name
    if expiry_date:
        v.expiry_date = expiry_date
    if metadata:
        v.verification_metadata = {**(v.verification_metadata or {}), **metadata}
    v.save()
    return v


def record_official_source(
    version: DocumentVersion,
    *,
    source: str,
    verified_by: str,
    expiry_date=None,
    metadata: Optional[dict] = None,
) -> DocumentVerification:
    """Confirmation from an official source (CIPC, Home Affairs, SARS, etc.)."""
    v = _get_or_create(version)
    v.verification_status = VerificationStatus.OFFICIAL_SOURCE
    v.verification_source = source
    v.verified_at = timezone.now()
    v.verified_by = verified_by
    if expiry_date:
        v.expiry_date = expiry_date
    if metadata:
        v.verification_metadata = {**(v.verification_metadata or {}), **metadata}
    v.save()
    return v


def reject(
    version: DocumentVersion,
    *,
    verified_by: str,
    reason: str,
) -> DocumentVerification:
    v = _get_or_create(version)
    v.verification_status = VerificationStatus.REJECTED
    v.verified_at = timezone.now()
    v.verified_by = verified_by
    v.verification_metadata = {**(v.verification_metadata or {}), "rejection_reason": reason}
    v.save()
    return v


def is_valid_now(version: DocumentVersion) -> bool:
    """True iff verification exists, is not rejected, and not expired."""
    v = getattr(version, "verification", None)
    if v is None:
        return False
    if v.verification_status in (VerificationStatus.UNVERIFIED, VerificationStatus.REJECTED):
        return False
    return not v.is_expired
