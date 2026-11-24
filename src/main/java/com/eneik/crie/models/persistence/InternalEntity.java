package com.eneik.crie.models.persistence;

import java.time.Instant;
import java.util.Locale;
import java.util.Objects;
import java.util.Optional;

/**
 * Persistence schema model for the {@code enrolled_trainees} table storing
 * resident and postgraduate enrollment records extracted from CRIE PDF orders.
 */
public class InternalEntity {

    public static final String TABLE_NAME = "enrolled_trainees";

    public static final String DDL_SQL =
            "CREATE TABLE IF NOT EXISTS enrolled_trainees (\n"
                    + "    id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
                    + "    full_name TEXT NOT NULL,\n"
                    + "    snils_or_code TEXT NOT NULL,\n"
                    + "    level TEXT NOT NULL CHECK (level IN ('ординатура', 'аспирантура')),\n"
                    + "    specialty TEXT NOT NULL,\n"
                    + "    financing_type TEXT NOT NULL CHECK (financing_type IN ('бюджет', 'целевая квота', 'договор', 'допконкурс')),\n"
                    + "    score REAL,\n"
                    + "    order_doc_id INTEGER NOT NULL,\n"
                    + "    updated_at TEXT NOT NULL\n"
                    + ");";

    public enum EducationLevel {
        ORDINATURA("ординатура"),
        ASPIRANTURA("аспирантура");

        private final String dbValue;

        EducationLevel(String dbValue) {
            this.dbValue = dbValue;
        }

        public String getDbValue() {
            return dbValue;
        }

        /**
         * Deterministically normalizes raw PDF text or specialty prefixes to a canonical level.
         */
        public static Optional<EducationLevel> fromRaw(String raw) {
            if (raw == null) {
                return Optional.empty();
            }
            String normalized = raw.trim().toLowerCase(Locale.ROOT);
            if (normalized.isEmpty()) {
                return Optional.empty();
            }
            if (normalized.contains("аспирант") || normalized.matches(".*\\b\\d{1,2}\\.06\\.\\d{2}\\b.*")) {
                return Optional.of(ASPIRANTURA);
            }
            if (normalized.contains("ординат") || normalized.matches(".*\\b\\d{2}\\.08\\.\\d{2}\\b.*")) {
                return Optional.of(ORDINATURA);
            }
            return Optional.empty();
        }
    }

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
         * Deterministically normalizes raw financing labels to one of the four canonical categories.
         */
        public static Optional<FinancingType> fromRaw(String raw) {
            if (raw == null) {
                return Optional.empty();
            }
            String normalized = raw.trim().toLowerCase(Locale.ROOT).replace('ё', 'е');
            if (normalized.isEmpty()) {
                return Optional.empty();
            }
            if (normalized.contains("допконкурс") || normalized.contains("дополнительн")) {
                return Optional.of(ADDITIONAL_COMPETITION);
            }
            if (normalized.contains("целев")) {
                return Optional.of(TARGET_QUOTA);
            }
            if (normalized.contains("договор") || normalized.contains("платн") || normalized.contains("внебюджет") || normalized.contains("контракт")) {
                return Optional.of(CONTRACT);
            }
            if (normalized.contains("бюджет") || normalized.contains("кцп") || normalized.contains("основн")) {
                return Optional.of(BUDGET);
            }
            return Optional.empty();
        }
    }

    private Long id;
    private String fullName;
    private String snilsOrCode;
    private EducationLevel level;
    private String specialty;
    private FinancingType financingType;
    private Double score;
    private Long orderDocId;
    private Instant updatedAt;

    public InternalEntity() {
    }

    public InternalEntity(
            Long id,
            String fullName,
            String snilsOrCode,
            EducationLevel level,
            String specialty,
            FinancingType financingType,
            Double score,
            Long orderDocId,
            Instant updatedAt) {
        this.id = id;
        this.fullName = fullName;
        this.snilsOrCode = snilsOrCode;
        this.level = level;
        this.specialty = specialty;
        this.financingType = financingType;
        this.score = score;
        this.orderDocId = orderDocId;
        this.updatedAt = updatedAt;
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
        this.fullName = fullName;
    }

    public String getSnilsOrCode() {
        return snilsOrCode;
    }

    public void setSnilsOrCode(String snilsOrCode) {
        this.snilsOrCode = snilsOrCode;
    }

    public EducationLevel getLevel() {
        return level;
    }

    public void setLevel(EducationLevel level) {
        this.level = level;
    }

    public String getSpecialty() {
        return specialty;
    }

    public void setSpecialty(String specialty) {
        this.specialty = specialty;
    }

    public FinancingType getFinancingType() {
        return financingType;
    }

    public void setFinancingType(FinancingType financingType) {
        this.financingType = financingType;
    }

    public Double getScore() {
        return score;
    }

    public void setScore(Double score) {
        this.score = score;
    }

    public Long getOrderDocId() {
        return orderDocId;
    }

    public void setOrderDocId(Long orderDocId) {
        this.orderDocId = orderDocId;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(Instant updatedAt) {
        this.updatedAt = updatedAt;
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
                && level == that.level
                && Objects.equals(specialty, that.specialty)
                && financingType == that.financingType
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
                + ", level=" + level
                + ", specialty='" + specialty + '\''
                + ", financingType=" + financingType
                + ", score=" + score
                + ", orderDocId=" + orderDocId
                + ", updatedAt=" + updatedAt
                + '}';
    }
}
