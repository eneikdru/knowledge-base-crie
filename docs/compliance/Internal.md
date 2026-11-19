# Contingent Data Compliance & Resilience Policy (BARCAN-TAG-10)

## 1. Purpose and Regulatory Scope

This document defines the internal compliance, data-protection, and resilience requirements for contingent admission and enrollment records stored in the CRIE SQLite persistence layer (`uploaded_documents` and `admission_records`). It aligns technical operations in `crie_persistent_memory.py` and `scripts/backup_restore.py` with:

- **GDPR Article 15 (Right of Access):** Timely, structured export of personal identifiers associated with a data subject.
- **GDPR Article 17 (Right to Erasure / 'Right to be Forgotten'):** Irreversible erasure or cryptographic pseudonymization of personal identifiers in `admission_records.student_identifiers_json` without corrupting aggregate institutional statistics.
- **GDPR Article 32(1)(c) (Resilience and Availability):** Verifiable backup and restoration procedures ensuring timely recovery of personal and operational data after physical or technical incidents.

---

## 2. Covered Data Assets

| Table | Sensitive / Regulated Fields | Aggregate / Operational Fields |
| :--- | :--- | :--- |
| `uploaded_documents` | `raw_text` (may contain embedded admission order text), `filename` | `id`, `uploaded_at`, `doc_type` |
| `admission_records` | `student_identifiers_json` (JSON array/object of enrolled or applicant identifiers) | `id`, `doc_id`, `order_number`, `order_date`, `education_level`, `specialty_code`, `specialty_name`, `financing_type`, `admission_stage`, `enrolled_count` |

---

## 3. Compliance Controls

### 3.1 Data-Subject Access Export (GDPR Art. 15)
1. **Lookup Scope:** Querying by a student identifier against `admission_records.student_identifiers_json` must return all matching admission records along with provenance metadata (`doc_id`, `order_number`, `order_date`, `education_level`, `specialty_code`, `specialty_name`, `financing_type`, `admission_stage`).
2. **Output Format:** Export payloads must be machine-readable (JSON) and limited strictly to records matching the requested data-subject identifier, avoiding unintended disclosure of unrelated third-party identifiers in the same `student_identifiers_json` collection.
3. **Auditability:** Export operations must be deterministic and reproducible against the populated SQLite database.

### 3.2 Data-Subject Erasure & Pseudonymization (GDPR Art. 17)
1. **Irreversible Removal / Pseudonymization:** When erasure is invoked for a student identifier in `admission_records.student_identifiers_json`, the matching identifier entry must be permanently removed or replaced with an irreversible, non-linkable pseudonym token.
2. **Aggregate Statistical Integrity:** Erasure or pseudonymization of `student_identifiers_json` **must not** decrement `enrolled_count` or delete the enclosing `admission_records` row, preserving aggregate enrollment reporting by specialty, education level, financing type, and admission stage.
3. **Transactional Atomicity:** Updates to `student_identifiers_json` must execute inside an atomic SQLite transaction so partial erasure states cannot occur.

### 3.3 Verified SQLite Backup & Restore (GDPR Art. 32(1)(c))
1. **Consistent Snapshot:** `scripts/backup_restore.py` must produce a consistent SQLite backup (e.g., via SQLite online backup API / transactional snapshot) rather than an uncoordinated file copy while writes may be active.
2. **Integrity Verification:** Both backup and restore workflows must compute and verify row counts and cryptographic checksums for `uploaded_documents` and `admission_records`.
3. **Clean-Target Restoration:** Restoring a backup to a clean target path must yield exact parity in `uploaded_documents` and `admission_records` row counts and table checksums relative to the pre-backup state.

---

## 4. Legal & Operational Disclaimer Boundaries

- **Internal Technical Policy Only:** This document specifies internal engineering and operational compliance controls for the BARCAN-TAG-10 slice and does not constitute formal legal advice or supersede institutional Data Protection Officer (DPO) directives or local statutory retention mandates (e.g., mandatory archival retention periods for official admission orders).
- **Scope Boundary:** Implementation of Python persistence helpers (`crie_persistent_memory.py`) and backup/restore CLI routines (`scripts/backup_restore.py`) is governed by their respective implementation slices; this policy defines the acceptance boundaries those components must satisfy.
- **Third-Party / LLM Context Minimization:** When aggregate `admission_records` summaries are supplied to downstream assistant or LLM context slots, only aggregate counts and non-personal metadata should be included unless explicit access-control authorization requires otherwise.

---

## 5. Verification Notes

- **Target Test Suites:**
  - Backup/restore parity verification (`scripts/backup_restore.py` / `tests/test_backup_restore.py`): confirm `uploaded_documents` and `admission_records` row counts and checksums match pre-backup state after restoring to a clean target path.
  - Compliance audit checks (`tests/compliance/compliance-audit.spec.ts`) and data-subject export/erasure unit tests on `crie_persistent_memory.py`: confirm matching `student_identifiers_json` entries are exported or irreversibly erased/pseudonymized while `enrolled_count` and aggregate distributions remain intact.
- **Execution Status Note:** This documentation-only change (`docs/compliance/Internal.md`) was authored without running repository test commands; runtime verification of code changes belongs to the corresponding implementation and test-execution stages.
