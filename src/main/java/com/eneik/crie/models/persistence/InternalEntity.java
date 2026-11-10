package com.eneik.crie.models.persistence;

import java.io.Serializable;
import java.time.Instant;
import java.time.LocalDate;
import java.util.Collections;
import java.util.HashSet;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

/**
 * Persistence and data schema entity representing normative legal acts (SanPiN, SP,
 * Minzdrav / Minobrnauki orders, FGOS VO, VAK passports) with CRIE specialty verification,
 * status lifecycle management, and deterministic index filtering.
 */
public class InternalEntity implements Serializable {

    private static final long serialVersionUID = 1L;

    public enum Status {
        ACTIVE("active"),
        REPEALED("repealed"),
        SUPERSEDED("superseded");

        private final String code;

        Status(String code) {
            this.code = code;
        }

        public String getCode() {
            return code;
        }

        public static Status fromString(String value) {
            if (value == null) {
                return ACTIVE;
            }
            String normalized = value.trim().toLowerCase(Locale.ROOT);
            for (Status s : values()) {
                if (s.code.equalsIgnoreCase(normalized) || s.name().equalsIgnoreCase(normalized)) {
                    return s;
                }
            }
            return ACTIVE;
        }
    }

    public static final Set<String> ALLOWED_SPECIALTIES = Collections.unmodifiableSet(new HashSet<>() {{
        // Residency (Ординатура)
        add("32.08.12"); // Epidemiology
        add("31.08.35"); // Infectious Diseases
        add("31.08.19"); // Pediatrics
        // Postgraduate (Аспирантура)
        add("3.2.2");    // Epidemiology
        add("3.1.22");   // Infectious Diseases
    }});

    public static final Set<String> EXCLUDED_SCOPE_KEYWORDS = Collections.unmodifiableSet(new HashSet<>() {{
        add("microbiology");
        add("микробиология");
        add("микробиологический");
    }});

    private String id;
    private String actNumber;
    private String title;
    private String documentType; // SanPiN, SP, MinzdravOrder, MinobrnaukiOrder, FGOS_VO, VAK_Passport
    private String legalAuthority; // Минздрав, Роспотребнадзор, Минобрнауки, ВАК
    private Status status = Status.ACTIVE;
    private LocalDate adoptionDate;
    private LocalDate effectiveDate;
    private LocalDate effectiveEndDate;
    private Set<String> specialties = new HashSet<>();
    private boolean activeSearchFlag = true;
    private boolean quarantined = false;
    private String quarantineReason;
    private Set<String> invertedIndexTokens = new HashSet<>();
    private String content;
    private Map<String, Object> metadata;
    private Long version = 0L;
    private Instant createdAt = Instant.now();
    private Instant updatedAt = Instant.now();

    public InternalEntity() {
    }

    public InternalEntity(String id, String actNumber, String title, String documentType, String legalAuthority) {
        this.id = id;
        this.actNumber = actNumber;
        this.title = title;
        this.documentType = documentType;
        this.legalAuthority = legalAuthority;
    }

    public void updateStatus(Status newStatus) {
        this.status = (newStatus != null) ? newStatus : Status.ACTIVE;
        this.updatedAt = Instant.now();
        if (this.status == Status.REPEALED || this.status == Status.SUPERSEDED) {
            this.activeSearchFlag = false;
            pruneInvertedIndexTokens();
        }
    }

    public void updateStatus(String statusStr) {
        updateStatus(Status.fromString(statusStr));
    }

    public void checkEffectiveEndDate(LocalDate currentDate) {
        if (currentDate != null && this.effectiveEndDate != null && currentDate.isAfter(this.effectiveEndDate)) {
            updateStatus(Status.REPEALED);
        }
    }

    public void evaluateSpecialtyAndQuarantine() {
        if (title != null) {
            String lowerTitle = title.toLowerCase(Locale.ROOT);
            for (String kw : EXCLUDED_SCOPE_KEYWORDS) {
                if (lowerTitle.contains(kw)) {
                    quarantine("Matches excluded scope: " + kw);
                    return;
                }
            }
        }
        if (content != null) {
            String lowerContent = content.toLowerCase(Locale.ROOT);
            for (String kw : EXCLUDED_SCOPE_KEYWORDS) {
                if (lowerContent.contains(kw)) {
                    quarantine("Matches excluded scope: " + kw);
                    return;
                }
            }
        }
        boolean hasValidSpecialty = false;
        for (String specialty : specialties) {
            if (specialty != null) {
                String trimmed = specialty.trim();
                if (ALLOWED_SPECIALTIES.contains(trimmed)) {
                    hasValidSpecialty = true;
                    break;
                }
            }
        }
        if (!specialties.isEmpty() && !hasValidSpecialty) {
            quarantine("No matching allowed CRIE specialty found");
        }
    }

    public void quarantine(String reason) {
        this.quarantined = true;
        this.quarantineReason = reason;
        this.activeSearchFlag = false;
        this.updatedAt = Instant.now();
        pruneInvertedIndexTokens();
    }

    public void pruneInvertedIndexTokens() {
        if (this.invertedIndexTokens != null) {
            this.invertedIndexTokens.clear();
        }
    }

    public boolean isSearchable() {
        return this.activeSearchFlag && !this.quarantined && this.status == Status.ACTIVE;
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getActNumber() {
        return actNumber;
    }

    public void setActNumber(String actNumber) {
        this.actNumber = actNumber;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
        evaluateSpecialtyAndQuarantine();
    }

    public String getDocumentType() {
        return documentType;
    }

    public void setDocumentType(String documentType) {
        this.documentType = documentType;
    }

    public String getLegalAuthority() {
        return legalAuthority;
    }

    public void setLegalAuthority(String legalAuthority) {
        this.legalAuthority = legalAuthority;
    }

    public Status getStatus() {
        return status;
    }

    public void setStatus(Status status) {
        updateStatus(status);
    }

    public LocalDate getAdoptionDate() {
        return adoptionDate;
    }

    public void setAdoptionDate(LocalDate adoptionDate) {
        this.adoptionDate = adoptionDate;
    }

    public LocalDate getEffectiveDate() {
        return effectiveDate;
    }

    public void setEffectiveDate(LocalDate effectiveDate) {
        this.effectiveDate = effectiveDate;
    }

    public LocalDate getEffectiveEndDate() {
        return effectiveEndDate;
    }

    public void setEffectiveEndDate(LocalDate effectiveEndDate) {
        this.effectiveEndDate = effectiveEndDate;
        checkEffectiveEndDate(LocalDate.now());
    }

    public Set<String> getSpecialties() {
        return specialties;
    }

    public void setSpecialties(Set<String> specialties) {
        this.specialties = (specialties != null) ? new HashSet<>(specialties) : new HashSet<>();
        evaluateSpecialtyAndQuarantine();
    }

    public void addSpecialty(String specialty) {
        if (this.specialties == null) {
            this.specialties = new HashSet<>();
        }
        if (specialty != null) {
            this.specialties.add(specialty.trim());
        }
        evaluateSpecialtyAndQuarantine();
    }

    public boolean isActiveSearchFlag() {
        return activeSearchFlag;
    }

    public void setActiveSearchFlag(boolean activeSearchFlag) {
        this.activeSearchFlag = activeSearchFlag;
        if (!activeSearchFlag) {
            pruneInvertedIndexTokens();
        }
    }

    public boolean isQuarantined() {
        return quarantined;
    }

    public void setQuarantined(boolean quarantined) {
        this.quarantined = quarantined;
        if (quarantined) {
            this.activeSearchFlag = false;
            pruneInvertedIndexTokens();
        }
    }

    public String getQuarantineReason() {
        return quarantineReason;
    }

    public void setQuarantineReason(String quarantineReason) {
        this.quarantineReason = quarantineReason;
    }

    public Set<String> getInvertedIndexTokens() {
        return invertedIndexTokens;
    }

    public void setInvertedIndexTokens(Set<String> invertedIndexTokens) {
        this.invertedIndexTokens = (invertedIndexTokens != null) ? new HashSet<>(invertedIndexTokens) : new HashSet<>();
    }

    public String getContent() {
        return content;
    }

    public void setContent(String content) {
        this.content = content;
        evaluateSpecialtyAndQuarantine();
    }

    public Map<String, Object> getMetadata() {
        return metadata;
    }

    public void setMetadata(Map<String, Object> metadata) {
        this.metadata = metadata;
    }

    public Long getVersion() {
        return version;
    }

    public void setVersion(Long version) {
        this.version = version;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Instant createdAt) {
        this.createdAt = createdAt;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(Instant updatedAt) {
        this.updatedAt = updatedAt;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof InternalEntity)) return false;
        InternalEntity that = (InternalEntity) o;
        return Objects.equals(id, that.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
    }
}
