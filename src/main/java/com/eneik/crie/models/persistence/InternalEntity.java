package com.eneik.crie.models.persistence;

import java.time.Clock;
import java.time.Instant;
import java.util.Locale;
import java.util.Objects;

/**
 * Persistence schema representation for the {@code enrolled_trainees} table
 * storing CRIE resident and postgraduate enrollment records extracted from PDFs.
 */
public class InternalEntity {

    public static final String TABLE_NAME = "enrolled_trainees";

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
         * Deterministically normalizes a raw education level or specialty code.
         */
        public static EducationLevel fromRaw(String raw) {
            if (raw == null || raw.trim().isEmpty()) {
                throw new IllegalArgumentException("Education level cannot be null or blank");
            }
            String normalized = raw.trim().toLowerCase(Locale.ROOT);
            if (normalized.contains("ординат") || normalized.startsWith("орд")
                    || normalized.contains("31.08.") || normalized.contains("32.08.")) {
                return ORDINATURA;
            }
            if (normalized.contains("аспирант") || normalized.startsWith("асп")) {
                return ASPIRANTURA;
            }
            throw new IllegalArgumentException("Unsupported education level: " + raw);
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
         * Deterministically normalizes a raw financing category label.
         */
        public static FinancingType fromRaw(String raw) {
            if (raw == null || raw.trim().isEmpty()) {
                throw new IllegalArgumentException("Financing type cannot be null or blank");
            }
            String normalized = raw.trim().toLowerCase(Locale.ROOT).replace('ё', 'е');
            if (normalized.contains("допконкурс") || normalized.contains("доп. конкурс")
                    || normalized.contains("дополнительн")) {
                return ADDITIONAL_COMPETITION;
            }
            if (normalized.contains("целев") || normalized.contains("квот")) {
                return TARGET_QUOTA;
            }
            if (normalized.contains("договор") || normalized.contains("платн")
                    || normalized.contains("внебюджет") || normalized.contains("контракт")) {
                return CONTRACT;
            }
            if (normalized.contains("бюджет") || normalized.contains("кцп")
                    || normalized.contains("основн")) {
                return BUDGET;
            }
            throw new IllegalArgumentException("Unsupported financing type: " + raw);
        }
    }

    private Long id;
    private String fullName;
    private String snilsOrCode;
    private EducationLevel level;
    private String specialty;
    private FinancingType financingType;
    private Double score;
    private String orderDocId;
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
            String orderDocId,
            Instant updatedAt) {
        this.id = id;
        this.fullName = requireNonBlank(fullName, "fullName");
        this.snilsOrCode = requireNonBlank(snilsOrCode, "snilsOrCode");
        this.level = Objects.requireNonNull(level, "level must not be null");
        this.specialty = requireNonBlank(specialty, "specialty");
        this.financingType = Objects.requireNonNull(financingType, "financingType must not be null");
        this.score = score;
        this.orderDocId = requireNonBlank(orderDocId, "orderDocId");
        this.updatedAt = Objects.requireNonNull(updatedAt, "updatedAt must not be null");
    }

    /**
     * Creates an entity using an injectable clock so callers and tests stay deterministic.
     */
    public static InternalEntity create(
            String fullName,
            String snilsOrCode,
            EducationLevel level,
            String specialty,
            FinancingType financingType,
            Double score,
            String orderDocId,
            Clock clock) {
        Clock effectiveClock = Objects.requireNonNull(clock, "clock must not be null");
        return new InternalEntity(
                null,
                fullName,
                snilsOrCode,
                level,
                specialty,
                financingType,
                score,
                orderDocId,
                Instant.now(effectiveClock)
        );
    }

    private static String requireNonBlank(String value, String fieldName) {
        if (value == null || value.trim().isEmpty()) {
            throw new IllegalArgumentException(fieldName + " must not be null or blank");
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

    public EducationLevel getLevel() {
        return level;
    }

    public void setLevel(EducationLevel level) {
        this.level = Objects.requireNonNull(level, "level must not be null");
    }

    public String getSpecialty() {
        return specialty;
    }

    public void setSpecialty(String specialty) {
        this.specialty = requireNonBlank(specialty, "specialty");
    }

    public FinancingType getFinancingType() {
        return financingType;
    }

    public void setFinancingType(FinancingType financingType) {
        this.financingType = Objects.requireNonNull(financingType, "financingType must not be null");
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
        return "InternalEntity{" +
                "id=" + id +
                ", fullName='" + fullName + '\'' +
                ", snilsOrCode='" + snilsOrCode + '\'' +
                ", level=" + level +
                ", specialty='" + specialty + '\'' +
                ", financingType=" + financingType +
                ", score=" + score +
                ", orderDocId='" + orderDocId + '\'' +
                ", updatedAt=" + updatedAt +
                '}';
    }
}
