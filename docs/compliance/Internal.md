# Internal Compliance Specification: Contingent SQLite Backup/Restore & Data-Subject Rights

- **Role:** BARCAN-TAG-10 (Compliance)
- **Reference:** Slice `afed14ff` / Wishlist `f83b2e27-4743-4ca4-a421-e6a2e78c72d3`
- **Effective Date:** 2026-11-24
- **Target Components (Policy Scope):** `scripts/backup_restore.py`, `crie_persistent_memory.py`, SQLite tables `uploaded_documents` and `admission_records`

## 1. Legal & Policy Disclaimer Boundaries

1. **Engineering Compliance Policy Only:** This document defines technical and operational controls intended to support compliance with GDPR Articles 15, 17, and 32(1)(c) for contingent admission and enrollment records. It does not constitute formal legal advice and does not replace Data Protection Officer (DPO) review or institutional legal sign-off prior to production deployment.
2. **Purpose Limitation & Scope Boundary:** Controls in this document apply strictly to contingent SQLite records stored in `uploaded_documents` (`id`, `filename`, `uploaded_at`, `raw_text`, `doc_type`) and `admission_records` (`id`, `doc_id`, `order_number`, `order_date`, `education_level`, `specialty_code`, `specialty_name`, `financing_type`, `admission_stage`, `enrolled_count`, `student_identifiers_json`).
3. **No Silent Cross-Subject Disclosure:** Data-subject export operations must return only records matching the verified target identifier and must not expose identifiers belonging to other individuals stored within the same `student_identifiers_json` array.
4. **Statistical Integrity Boundary:** Erasure or irreversible pseudonymization of personal identifiers must preserve aggregate enrollment counts (`enrolled_count`) and non-identifying dimensions (`education_level`, `specialty_code`, `specialty_name`, `financing_type`, `admission_stage`) so institutional reporting remains accurate.

## 2. Regulatory Control Mapping

| GDPR Provision | Control Objective | Target Implementation Surface | Required Behavior |
| :--- | :--- | :--- | :--- |
| **Art. 15** (Right of Access) | Data-subject export | `crie_persistent_memory.py` | Locate and export all entries in `admission_records.student_identifiers_json` matching a given student identifier together with non-sensitive record context (`order_number`, `order_date`, `specialty_code`, `specialty_name`, `financing_type`, `admission_stage`). |
| **Art. 17** (Right to Erasure) | Irreversible erasure / pseudonymization | `crie_persistent_memory.py` | Remove or irreversibly pseudonymize matching entries in `admission_records.student_identifiers_json` across all matching rows without decrementing or corrupting `enrolled_count` or breaking JSON schema validity. |
| **Art. 32(1)(c)** (Availability & Resilience) | Verified backup and restore | `scripts/backup_restore.py` | Create consistent SQLite backups and restore to a clean target path while verifying pre-backup and post-restore row counts and integrity checksums for `uploaded_documents` and `admission_records`. |

## 3. Detailed Compliance Requirements

### 3.1 Data-Subject Export (GDPR Art. 15)
- Matching must inspect parsed entries inside `admission_records.student_identifiers_json` rather than performing unanchored substring matches that could leak unrelated records.
- Export payloads must omit third-party entries from `student_identifiers_json` on rows where multiple students share an admission order.
- When no matching identifier exists, the helper must return an empty deterministic result rather than raising an unhandled error.

### 3.2 Data-Subject Erasure / Irreversible Pseudonymization (GDPR Art. 17)
- Matching entries in `admission_records.student_identifiers_json` must be either removed or replaced with an irreversible, non-reidentifiable pseudonym token (not a reversible hash without salt destruction or deterministic cleartext-recoverable mapping).
- Updates to `admission_records` must be atomic per transaction and preserve valid JSON serialization in `student_identifiers_json`.
- Aggregate fields (`enrolled_count`, `education_level`, `specialty_code`, `specialty_name`, `financing_type`, `admission_stage`) must remain unchanged after erasure.
- **Boundary Note on `uploaded_documents.raw_text`:** If raw source PDFs or `uploaded_documents.raw_text` retain unredacted personal identifiers after `student_identifiers_json` erasure, a follow-up redaction/retention policy for `raw_text` must be executed or documented before claiming full Art. 17 closure across unstructured text.

### 3.3 Verified SQLite Backup & Restore (GDPR Art. 32(1)(c))
- Backups must use an atomic/consistent SQLite backup mechanism (avoiding raw file copies during active writes).
- Restores targeting a clean path must verify:
  1. Exact row-count parity for `uploaded_documents` and `admission_records` before backup vs. after restore.
  2. Content checksum parity (deterministic canonical table/database checksum) before backup vs. after restore.
  3. SQLite integrity verification (`PRAGMA integrity_check` or equivalent) returning `ok` on the restored database.
- Backup and restore helpers must avoid writing transient artifacts into tracked repository paths or `.eneik/`.

## 4. Verification Procedures & Notes

This slice creates the compliance specification document (`docs/compliance/Internal.md`) only; runtime verification applies to the corresponding implementation and test slices:

1. **Backup/Restore Parity Check:** Run the repository backup/restore test suite (e.g., `pytest tests/test_backup_restore.py`) against a populated SQLite database containing `uploaded_documents` and `admission_records`, confirming matching row counts and checksums on restore to a clean target path.
2. **Data-Subject Export & Erasure Check:** Run unit/integration tests for `crie_persistent_memory.py` verifying that:
   - Export returns only matching `student_identifiers_json` entries for the requested identifier.
   - Erasure removes or irreversibly pseudonymizes the target identifier across all matching `admission_records` rows.
   - Re-running export after erasure yields zero cleartext matches for the erased identifier.
   - `enrolled_count` and specialty/financing/stage aggregates remain identical pre- and post-erasure.
3. **Compliance Scope Check:** Inspect `git diff` to confirm changes are isolated to required documentation, source, config, or test files with clear disclaimer boundaries.
