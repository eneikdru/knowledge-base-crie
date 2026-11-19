# Contingent SQLite Registry Compliance Policy & Disclaimers (Internal)

**Slice / Role:** `BARCAN-TAG-10` (Compliance)  
**Covered Components:** `scripts/backup_restore.py`, `crie_persistent_memory.py`  
**Covered Tables:** `uploaded_documents`, `admission_records` (specifically `student_identifiers_json`)  

---

## 1. Purpose and Scope

This document defines the internal compliance requirements, legal disclaimer boundaries, and verification criteria for processing contingent admission and enrollment records in the SQLite persistent store (`uploaded_documents` and `admission_records`). It applies to:

1. **Verified Backup and Restore (`scripts/backup_restore.py`):** Ensuring availability, integrity, and recoverability of `uploaded_documents` and `admission_records`.
2. **Data-Subject Rights Helpers (`crie_persistent_memory.py`):** Supporting targeted data-subject access export and irreversible erasure/pseudonymization of personal identifiers in `admission_records.student_identifiers_json`.

---

## 2. Regulatory Control Mapping (GDPR)

### 2.1 GDPR Art. 15 — Right of Access (Data-Subject Export)
- **Requirement:** When a data-subject export helper is invoked for a specific student identifier, matching entries in `admission_records.student_identifiers_json` must be exported in a structured, machine-readable format together with non-sensitive record context (`doc_id`, `order_number`, `order_date`, `education_level`, `specialty_code`, `specialty_name`, `financing_type`, `admission_stage`).
- **Minimization Boundary:** Export payloads for a single data subject must **not** leak unrelated students' identifiers from `student_identifiers_json`.

### 2.2 GDPR Art. 17 — Right to Erasure / Pseudonymization
- **Requirement:** When a data-subject erasure helper is invoked for a student identifier, all matching entries in `admission_records.student_identifiers_json` must be irreversibly erased or replaced with an irreversible, non-attributable pseudonymized token.
- **Statistical Integrity Boundary:** Erasure or pseudonymization of individual identifiers must preserve aggregate statistical integrity (`enrolled_count` and aggregate breakdowns by `education_level`, `specialty_code`, `specialty_name`, `financing_type`, and `admission_stage`) so institutional reporting and aggregate assistant queries remain accurate without retaining personal data.

### 2.3 GDPR Art. 32(1)(c) — Resilience, Availability, and Verified Restore
- **Requirement:** `scripts/backup_restore.py` must support creating a consistent SQLite backup and restoring it to a clean target path.
- **Integrity Boundary:** Post-restore verification must confirm that row counts and deterministic table/content checksums for both `uploaded_documents` and `admission_records` match the pre-backup state.

---

## 3. Legal and Operational Disclaimers

1. **Not Formal Legal Counsel:** This policy documents technical and procedural compliance controls for internal engineering alignment and does not constitute formal legal advice. Production deployment involving real applicant or enrollee personal data requires formal review and sign-off by the institution's Data Protection Officer (DPO) and legal counsel.
2. **LLM Context & Prompt Boundary:** Aggregate analytics supplied to LLM context slots (such as contingent registry summaries from `admission_records`) should transmit aggregated counts and document registry metadata rather than raw personal identifiers from `student_identifiers_json`, unless an authorized workflow explicitly requires and logs access to personal data.
3. **Backup Retention vs. Erasure Propagation:** Restoring an older backup snapshot may reintroduce previously erased identifiers unless backup retention windows and post-restore erasure replay/suppression logs are enforced according to institutional retention schedules.
4. **Synthetic vs. Production Data:** Automated tests and local verification fixtures must use synthetic or anonymized identifiers rather than unredacted production personal data.

---

## 4. Verification Criteria & Scope Notes

- **Scope Boundary Note:** This document fulfills the `BARCAN-TAG-10` compliance documentation slice only. Code changes to `scripts/backup_restore.py`, creation/modification of `crie_persistent_memory.py`, and executable test suites (such as `tests/test_backup_restore.py`) are outside this file's scope and are handled by their respective engineering slices.
- **Acceptance Verification Checklist (to be executed in the engineering/verification slices once code changes are present):**
  1. **Backup/Restore Integrity:** Run `scripts/backup_restore.py` to back up a populated SQLite database and restore to a clean target path; verify `uploaded_documents` and `admission_records` row counts and checksums match pre-backup state.
  2. **Data-Subject Export (Art. 15):** Invoke the data-subject export helper for a known student identifier in `admission_records.student_identifiers_json` and verify only matching records are returned.
  3. **Data-Subject Erasure (Art. 17):** Invoke the erasure/pseudonymization helper for a student identifier and verify the raw identifier is absent across `admission_records.student_identifiers_json` while `enrolled_count` and aggregate totals remain unchanged.
  4. **Test Execution:** Run the relevant backup/restore and compliance tests (e.g., `pytest tests/test_backup_restore.py`) in the integrated engineering branch and record the exact command and output.
