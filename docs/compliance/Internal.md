# Contingent Data Compliance Policy & Controls (BARCAN-TAG-10)

## 1. Purpose and Scope

This document defines the regulatory compliance baseline, legal-disclaimer boundaries, and verification requirements for contingent admission data stored in the local SQLite database (`crie_persistent_memory.py`) and backed up or restored via `scripts/backup_restore.py`.

It specifically governs personal data contained in:
- `uploaded_documents` (`id`, `filename`, `uploaded_at`, `raw_text`, `doc_type`)
- `admission_records` (`id`, `doc_id`, `order_number`, `order_date`, `education_level`, `specialty_code`, `specialty_name`, `financing_type`, `admission_stage`, `enrolled_count`, `student_identifiers_json`)

> **Legal Disclaimer**: This document establishes technical and operational compliance controls aligned with GDPR Articles 15, 17, and 32(1)(c). It does not constitute formal legal advice. Institutional deployment remains subject to review and sign-off by the organization's Data Protection Officer (DPO) and compliance with applicable national education and personal-data statutes.

---

## 2. Regulatory Control Mapping

### 2.1 Right of Access / Data-Subject Export (GDPR Art. 15)
- **Control**: `crie_persistent_memory.py` must provide a deterministic data-subject export helper keyed by student identifier.
- **Behavior**:
  - Locate all rows in `admission_records` whose `student_identifiers_json` contains an exact match for the requested student identifier.
  - Return a structured, machine-readable JSON payload containing the matching identifier record(s) along with non-personal institutional context (`doc_id`, `order_number`, `order_date`, `education_level`, `specialty_code`, `specialty_name`, `financing_type`, `admission_stage`).
  - Do not expose third-party student identifiers belonging to other individuals in the same admission order.
- **Operational Boundary**: Export requests must only be fulfilled after operator/DPO identity verification outside the automated CLI or API layer.

### 2.2 Right to Erasure / Pseudonymization (GDPR Art. 17)
- **Control**: `crie_persistent_memory.py` must provide an irreversible data-subject erasure or cryptographic pseudonymization helper for a targeted student identifier.
- **Behavior**:
  - Remove or irreversibly replace matching entries in `admission_records.student_identifiers_json` so the natural person can no longer be re-identified from the database.
  - **Aggregate Statistical Integrity**: Erasure must NOT decrement or corrupt aggregate reporting fields (`enrolled_count`, `specialty_code`, `specialty_name`, `education_level`, `financing_type`, `admission_stage`, `order_number`, `order_date`) or orphan `uploaded_documents` lineage required for statutory enrollment statistics.
  - Any operational audit log entry recording the erasure must omit the raw erased student identifier (record only timestamp, affected record count, and operation status).
- **LLM Context Minimization Boundary**: Aggregated contingent queries routed to LLM prompts must supply aggregate counts and structural summaries rather than raw `student_identifiers_json` lists unless explicitly authorized and necessary.

### 2.3 Resilience, Backup Integrity & Verified Restore (GDPR Art. 32(1)(c))
- **Control**: `scripts/backup_restore.py` must support consistent SQLite backup and clean-path restore operations for the contingent database.
- **Behavior**:
  - Backup archives must capture a transactionally consistent snapshot of `uploaded_documents` and `admission_records` (using SQLite online backup semantics rather than unsafe raw file copies during active writes).
  - Restore to a clean target path must validate post-restore integrity by verifying that `uploaded_documents` and `admission_records` row counts and deterministic content checksums exactly match the pre-backup state.
  - Backup artifacts containing `student_identifiers_json` must be stored in restricted-access paths with least-privilege filesystem permissions and excluded from version control.
- **Erasure Propagation Boundary**: When a GDPR Art. 17 erasure is executed on live data, retention policies for prior backup snapshots must be documented by the DPO so erased identifiers are not silently reintroduced via stale restores without re-applying the erasure ledger.

---

## 3. Compliance Verification Checklist

Implementation and QA slices covering `scripts/backup_restore.py` and `crie_persistent_memory.py` must satisfy the following checks:

1. **Backup/Restore Round-Trip Integrity**:
   - Given a populated contingent SQLite database, running backup followed by restore to a clean target path yields identical row counts and checksums for `uploaded_documents` and `admission_records`.
2. **Data-Subject Export Completeness & Isolation**:
   - Invoking the export helper for a target student identifier returns all matching `admission_records` entries without leaking other students' identifiers from `student_identifiers_json`.
3. **Irreversible Erasure with Preserved Aggregates**:
   - Invoking the erasure/pseudonymization helper removes/irreversibly masks the target identifier in `admission_records.student_identifiers_json` (a subsequent export returns no matching raw identifier) while `enrolled_count` and specialty/financing/stage aggregates remain intact.

### Reference Verification Targets
- `pytest tests/test_backup_restore.py` (backup/restore verification suite, once aligned with contingent SQLite tables)
- `npx playwright test tests/compliance/compliance-audit.spec.ts` (compliance audit E2E check, if enabled in the CI environment)

*Verification Note (BARCAN-TAG-10)*: This policy file (`docs/compliance/Internal.md`) was authored under a documentation-only compliance file scope without executing local test runners.
