package com.eneik.crie.models.persistence;

import java.time.Instant;
import java.util.Locale;
import java.util.Objects;
import java.util.Optional;

/**
 * Persistence schema model and canonical normalization contract for the
 * {@code enrolled_trainees} SQLite contingency table.
 */
public class InternalEntity {

    public static final String TABLE_NAME = "enrolled_trainees";

    public static final String ENROLLED_TRAINEES_DDL =
        "CREATE TABLE IF NOT EXISTS enrolled_trainees ("
        + "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        + "full_name TEXT NOT NULL, "
        + "snils_or_code TEXT NOT NULL, "
        + "level TEXT NOT NULL CHECK (level IN ('ординатура', 'аспирантура')), "
        + "specialty TEXT NOT NULL, "
        + "financing_type TEXT NOT NULL CHECK (financing_type IN ('бюджет', 'целевая квота', 'договор', 'допконкурс')), "
        + "score REAL, "
        + "order_doc_id TEXT NOT NULL, "
        + "updated_at TEXT NOT NULL, "
        + "UNIQUE (snils_or_code, level, specialty, financing_type, order_doc_id)"
        + ");";

    /**
     * Canonical trainee education levels.
     */
    public enum EducationLevel {
        RESIDENCY("ординатура"),
        POSTGRADUATE("аспирантура");

        private final String dbValue;

        EducationLevel(String dbValue) {
            this.dbValue = dbValue;
        }

        public String getDbValue() {
            return dbValue;
        }

        /**
         * Deterministically normalizes raw level labels to canonical enum values.
         */
        public static Optional<EducationLevel> fromRaw(String raw) {
            if (raw == null) {
                return Optional.empty();
            }
            String normalized = raw.trim().toLowerCase(Locale.ROOT);
            if (normalized.contains("ординат")) {
                return Optional.of(RESIDENCY);
            }
            if (normalized.contains("аспирант")) {
                return Optional.of(POSTGRADUATE);
            }
            return Optional.empty();
        }
    }

    /**
     * Canonical financing categories for CRIE enrollment records.
     */
    public enum FinancingType {
        BUDGET("бюджет"),
        TARGET_QUOTA("целевая квота"),
        CONTRACT("договор"),
        ADDITIONAL_COMPETITION("допконкурс");

        private final String dbValue;

        FinancingType(String dbValue) {
            this.dbValue = dbValue;
        }

        public String getDbValue() {
            return dbValue;
        }

        /**
         * Deterministically maps raw Russian financing phrases to canonical enum values.
         */
        public static Optional<FinancingType> fromRaw(String raw) {
            if (raw == null) {
                return Optional.empty();
            }
            String normalized = raw.trim().toLowerCase(Locale.ROOT);
            if (normalized.contains("допконкурс")
                || normalized.contains("доп. конкурс")
                || normalized.contains("доп конкурс")
                || normalized.contains("дополнительн")) {
                return Optional.of(ADDITIONAL_COMPETITION);
            }
            if (normalized.contains("целев") || normalized.contains("квот")) {
                return Optional.of(TARGET_QUOTA);
            }
            if (normalized.contains("внебюджет")
                || normalized.contains("договор")
                || normalized.contains("платн")
                || normalized.contains("коммерч")) {
                return Optional.of(CONTRACT);
            }
            if (normalized.contains("бюджет")
                || normalized.contains("кцп")
                || normalized.contains("основн")) {
                return Optional.of(BUDGET);
            }
            return Optional.empty();
        }
    }

    private Long id;
    private String fullName;
    private String snilsOrCode;
    private String level;
    private String specialty;
    private String financingType;
    private Double score;
    private String orderDocId;
    private Instant updatedAt;

    public InternalEntity() {
    }

    public InternalEntity(
        Long id,
        String fullName,
        String snilsOrCode,
        String level,
        String specialty,
        String financingType,
        Double score,
        String orderDocId,
        Instant updatedAt
    ) {
        this.id = id;
        this.fullName = requireNonBlank(fullName, "fullName");
        this.snilsOrCode = requireNonBlank(snilsOrCode, "snilsOrCode");
        this.level = EducationLevel.fromRaw(level)
            .orElseThrow(() -> new IllegalArgumentException("Unsupported education level: " + level))
            .getDbValue();
        this.specialty = requireNonBlank(specialty, "specialty");
        this.financingType = FinancingType.fromRaw(financingType)
            .orElseThrow(() -> new IllegalArgumentException("Unsupported financing type: " + financingType))
            .getDbValue();
        this.score = score;
        this.orderDocId = requireNonBlank(orderDocId, "orderDocId");
        this.updatedAt = Objects.requireNonNull(updatedAt, "updatedAt must not be null");
    }

    private static String requireNonBlank(String value, String fieldName) {
        if (value == null || value.trim().isEmpty()) {
            throw new IllegalArgumentException(fieldName + " must not be blank");
        }
        return value.trim();
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getFullName() {
        return fullName;
    }

    public void setFullName(String fullName) {
        this.fullName = requireNonBlank(fullName, "fullName");
    }

    public String getSnilsOrCode() {
        return snilsOrCode;
    }

    public void setSnilsOrCode(String snilsOrCode) {
        this.snilsOrCode = requireNonBlank(snilsOrCode, "snilsOrCode");
    }

    public String getLevel() {
        return level;
    }

    public void setLevel(String level) {
        this.level = EducationLevel.fromRaw(level)
            .orElseThrow(() -> new IllegalArgumentException("Unsupported education level: " + level))
            .getDbValue();
    }

    public String getSpecialty() {
        return specialty;
    }

    public void setSpecialty(String specialty) {
        this.specialty = requireNonBlank(specialty, "specialty");
    }

    public String getFinancingType() {
        return financingType;
    }

    public void setFinancingType(String financingType) {
        this.financingType = FinancingType.fromRaw(financingType)
            .orElseThrow(() -> new IllegalArgumentException("Unsupported financing type: " + financingType))
            .getDbValue();
    }

    public Double getScore() {
        return score;
    }

    public void setScore(Double score) {
        this.score = score;
    }

    public String getOrderDocId() {
        return orderDocId;
    }

    public void setOrderDocId(String orderDocId) {
        this.orderDocId = requireNonBlank(orderDocId, "orderDocId");
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(Instant updatedAt) {
        this.updatedAt = Objects.requireNonNull(updatedAt, "updatedAt must not be null");
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (!(o instanceof InternalEntity)) {
            return false;
        }
        InternalEntity that = (InternalEntity) o;
        return Objects.equals(id, that.id)
            && Objects.equals(fullName, that.fullName)
            && Objects.equals(snilsOrCode, that.snilsOrCode)
            && Objects.equals(level, that.level)
            && Objects.equals(specialty, that.specialty)
            && Objects.equals(financingType, that.financingType)
            && Objects.equals(score, that.score)
            && Objects.equals(orderDocId, that.orderDocId)
            && Objects.equals(updatedAt, that.updatedAt);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, fullName, snilsOrCode, level, specialty, financingType, score, orderDocId, updatedAt);
    }

    @Override
    public String toString() {
        return "InternalEntity{"
            + "id=" + id
            + ", fullName='" + fullName + '\''
            + ", snilsOrCode='" + snilsOrCode + '\''
            + ", level='" + level + '\''
            + ", specialty='" + specialty + '\''
            + ", financingType='" + financingType + '\''
            + ", score=" + score
            + ", orderDocId='" + orderDocId + '\''
            + ", updatedAt=" + updatedAt
            + '}';
    }
}
