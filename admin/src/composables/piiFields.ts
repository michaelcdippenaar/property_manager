/**
 * piiFields.ts — Canonical list of PII field names for Clarity session-recording masking.
 *
 * Any <input> bound to one of these v-model names MUST be wrapped with
 * <MaskedInput> (or carry data-clarity-mask="true") so that Microsoft Clarity
 * does not capture the value in session recordings.
 *
 * POPIA compliance requirement: personal identifiers and financial account
 * numbers are special-category data under POPIA s26 / s11 and must not leak
 * into third-party analytics tools.
 *
 * CI enforcement: admin/scripts/check-pii-masking.sh scans .vue files for
 * bare v-model references to these names without masking.
 */

export const PII_FIELD_NAMES = [
  'id_number',
  'account_number',
  'branch_code',
  'trust_account_number',
  'trust_branch_code',
  'representative_id_number',
  'passport',
] as const

export type PiiFieldName = (typeof PII_FIELD_NAMES)[number]
