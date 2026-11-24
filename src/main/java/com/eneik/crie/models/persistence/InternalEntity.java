package com.eneik.crie.models.persistence;

import java.time.Clock;
import java.time.Instant;
import java.util.Locale;
import java.util.Objects;
import java.util.Optional;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Persistence schema representation for the {@code enrolled_trainees} SQLite table
 * storing CRIE resident and postgraduate enrollment records extracted from PDFs.
 */
public final class InternalEntity {

    /**
     * Canonical SQLite DDL for the {@code enrolled_trainees} table.
     */
    public static final String ENROLLED_TRAINEES_DDL =
            "CREATE TABLE IF NOT EXISTS enrolled_trainees (\n"
                    + "    id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
                    + "    full_name TEXT NOT NULL,\n"
                    + "    snils_or_code TEXT NOT NULL,\n"
                    + "    level TEXT NOT NULL CHECK (level IN ('ординатура', 'аспирантура')),\n"
                    + "    specialty TEXT NOT NULL,\n"
                    + "    financing_type TEXT NOT NULL CHECK (financing_type IN ('бюджет', 'целевая квота', 'договор', 'допконкурс')),\n"
                    + "    score REAL,\n"
                    + "    order_doc_id TEXT NOT NULL,\n"
                    + "    updated_at TEXT NOT NULL,\n"
                    + "    UNIQUE (snils_or_code, specialty, order_doc_id)\n"
                    + ");";

    private static final Pattern SPECIALTY_CODE_PATTERN = Pattern.compile("(\\d{2}\\.\\d{2}\\.\\d{2})");
    private static final Pattern WHITESPACE_PATTERN = Pattern.compile("\\s+");

    /**
     * Canonical education levels supported by {@code enrolled_trainees.level}.
     */
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
         * Normalizes a raw education level string into a canonical {@link EducationLevel}.
         */
        public static Optional<EducationLevel> fromRaw(String raw) {
            if (raw == null) {
                return Optional.empty();
            }
            String normalized = WHITESPACE_PATTERN.matcher(raw.trim().toLowerCase(Locale.ROOT)).replaceAll(" ");
            if (normalized.contains("ординатур")) {
                return Optional.of(ORDINATURA);
            }
            if (normalized.contains("аспирантур")) {
                return Optional.of(ASPIRANTURA);
            }
            return Optional.empty();
        }
    }

    /**
     * Canonical financing categories supported by {@code enrolled_trainees.financing_type}.
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
         * Normalizes a raw financing category string into a canonical {@link FinancingType}.
         */
        public static Optional<FinancingType> fromRaw(String raw) {
            if (raw == null) {
                return Optional.empty();
            }
            String normalized = WHITESPACE_PATTERN.matcher(raw.trim().toLowerCase(Locale.ROOT)).replaceAll(" ");
            if (normalized.contains("допконкурс")
                    || normalized.contains("доп. конкурс")
                    || normalized.contains("доп конкурс")
                    || normalized.contains("дополнительн")) {
                return Optional.of(ADDITIONAL_COMPETITION);
            }
            if (normalized.contains("целев")) {
                return Optional.of(TARGET_QUOTA);
            }
            if (normalized.contains("договор")
                    || normalized.contains("платн")
                    || normalized.contains("внебюджет")
                    || normalized.contains("коммерч")) {
                return Optional.of(CONTRACT);
            }
            if (normalized.contains("бюджет") || normalized.contains("кцп") || normalized.contains("общ")) {
                return Optional.of(BUDGET);
            }
            return Optional.empty();
        }
    }

    private final Long id;
    private final String fullName;
    private final String snilsOrCode;
    private final EducationLevel level;
    private final String specialty;
    private final FinancingType financingType;
    private final Double score;
    private final String orderDocId;
    private final Instant updatedAt;

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
        this.snilsOrCode = normalizeSnilsOrCode(requireNonBlank(snilsOrCode, "snilsOrCode"));
        this.level = Objects.requireNonNull(level, "level must not be null");
        this.specialty = normalizeSpecialty(requireNonBlank(specialty, "specialty"));
        this.financingType = Objects.requireNonNull(financingType, "financingType must not be null");
        this.score = score;
        this.orderDocId = requireNonBlank(orderDocId, "orderDocId");
        this.updatedAt = Objects.requireNonNull(updatedAt, "updatedAt must not be null");
    }

    public static InternalEntity create(
            String fullName,
            String snilsOrCode,
            EducationLevel level,
            String specialty,
            FinancingType financingType,
            Double score,
            String orderDocId,
            Clock clock) {
        Clock effectiveClock = clock != null ? clock : Clock.systemUTC();
        return new InternalEntity(
                null,
                fullName,
                snilsOrCode,
                level,
                specialty,
                financingType,
                score,
                orderDocId,
                Instant.now(effectiveClock));
    }

    /**
     * Extracts canonical specialty code (e.g. {@code 31.08.19}, {@code 31.08.35}, {@code 32.08.12})
     * when present, otherwise returns whitespace-normalized text.
     */
    public static String normalizeSpecialty(String raw) {
        String cleaned = WHITESPACE_PATTERN.matcher(raw.trim()).replaceAll(" ");
        Matcher matcher = SPECIALTY_CODE_PATTERN.matcher(cleaned);
        if (matcher.find()) {
            return matcher.group(1);
        }
        return cleaned;
    }

    /**
     * Normalizes SNILS or applicant identifier whitespace.
     */
    public static String normalizeSnilsOrCode(String raw) {
        return WHITESPACE_PATTERN.matcher(raw.trim()).replaceAll(" ");
    }

    private static String requireNonBlank(String value, String fieldName) {
        if (value == null || value.trim().isEmpty()) {
            throw new IllegalArgumentException(fieldName + " must not be blank");
        }
        return WHITESPACE_PATTERN.matcher(value.trim()).replaceAll(" ");
    }

    public Long getId() {
        return id;
    }

    public String getFullName() {
        return fullName;
    }

    public String getSnilsOrCode() {
        return snilsOrCode;
    }

    public EducationLevel getLevel() {
        return level;
    }

    public String getSpecialty() {
        return specialty;
    }

    public FinancingType getFinancingType() {
        return financingType;
    }

    public Double getScore() {
        return score;
    }

    public String getOrderDocId() {
        return orderDocId;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    @Override
    public boolean equals(Object other) {
        if (this == other) {
            return true;
        }
        if (!(other instanceof InternalEntity)) {
            return false;
        }
        InternalEntity that = (InternalEntity) other;
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
                + ", level=" + level.getDbValue()
                + ", specialty='" + specialty + '\''
                + ", financingType=" + financingType.getDbValue()
                + ", score=" + score
                + ", orderDocId='" + orderDocId + '\''
                + ", updatedAt=" + updatedAt
                + '}';
    }
}
