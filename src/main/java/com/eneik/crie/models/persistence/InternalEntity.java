package com.eneik.crie.models.persistence;

import java.io.Serializable;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

/**
 * Persistence and domain model entity for normative regulatory acts (SanPiN, SP, orders,
 * FGOS, VAK passports) within the CRIE specialty contour.
 */
public class InternalEntity implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * Permitted CRIE specialty codes:
     * Residency (Ординатура): 32.08.12, 31.08.35, 31.08.19
     * Postgraduate (Аспирантура): 3.2.2, 3.1.22
     */
    public static final Set<String> ALLOWED_CRIE_SPECIALTIES = Collections.unmodifiableSet(new HashSet<>(Arrays.asList(
            "32.08.12",
            "31.08.35",
            "31.08.19",
            "3.2.2",
            "3.1.22"
    )));

    /**
     * Scopes explicitly excluded from CRIE normative indexing (e.g. general microbiology).
     */
    public static final Set<String> EXCLUDED_SCOPES = Collections.unmodifiableSet(new HashSet<>(Arrays.asList(
            "microbiology",
            "микробиология",
            "general microbiology"
    )));

    public enum ActStatus {
        ACTIVE("active"),
        REPEALED("repealed"),
        SUPERSEDED("superseded");

        private final String code;

        ActStatus(String code) {
            this.code = code;
        }

        public String getCode() {
            return code;
        }

        public static ActStatus fromString(String text) {
            if (text == null) {
                return null;
            }
            for (ActStatus status : ActStatus.values()) {
                if (status.code.equalsIgnoreCase(text.trim()) || status.name().equalsIgnoreCase(text.trim())) {
                    return status;
                }
            }
            throw new IllegalArgumentException("Unknown ActStatus: " + text);
        }
    }

    private String id;
    private String actNumber;
    private String title;
    private String documentType;
    private String legalAuthority;
    private String jurisdiction;
    private String registrationNumber;
    private LocalDate registrationDate;
    private LocalDate effectiveStartDate;
    private LocalDate effectiveEndDate;
    private LocalDate repealedDate;
    private String supersededBy;
    private ActStatus status = ActStatus.ACTIVE;
    private boolean activeSearchFlag = true;
    private boolean vectorIndexEligible = true;
    private boolean quarantined = false;
    private String quarantineReason;
    private Set<String> specialties = new HashSet<>();
    private Set<String> invertedIndexTokens = new HashSet<>();
    private String content;
    private Map<String, Object> metadata = new HashMap<>();
    private Long version = 0L;
    private LocalDateTime createdAt = LocalDateTime.now();
    private LocalDateTime updatedAt = LocalDateTime.now();

    public InternalEntity() {
    }

    public InternalEntity(String id, String actNumber, String title, String legalAuthority, String documentType) {
        this.id = id;
        this.actNumber = actNumber;
        this.title = title;
        this.legalAuthority = legalAuthority;
        this.documentType = documentType;
    }

    /**
     * Transitions status and updates search flags deterministically.
     */
    public synchronized void updateStatus(ActStatus newStatus) {
        this.status = newStatus;
        this.updatedAt = LocalDateTime.now();
        if (newStatus == ActStatus.REPEALED || newStatus == ActStatus.SUPERSEDED) {
            this.activeSearchFlag = false;
            this.vectorIndexEligible = false;
            pruneInvertedIndexTokens();
        } else if (newStatus == ActStatus.ACTIVE && !quarantined) {
            this.activeSearchFlag = true;
            this.vectorIndexEligible = true;
        }
    }

    public void updateStatus(String statusStr) {
        updateStatus(ActStatus.fromString(statusStr));
    }

    /**
     * Evaluates effective end date and repeals the act if expired.
     */
    public synchronized void checkEffectiveDate(LocalDate referenceDate) {
        if (effectiveEndDate != null && !referenceDate.isBefore(effectiveEndDate)) {
            updateStatus(ActStatus.REPEALED);
            if (this.repealedDate == null) {
                this.repealedDate = effectiveEndDate;
            }
        }
    }

    /**
     * Prunes inverted index tokens when repealed, superseded, or quarantined.
     */
    public synchronized void pruneInvertedIndexTokens() {
        if (this.invertedIndexTokens != null) {
            this.invertedIndexTokens.clear();
        }
    }

    /**
     * Assigns and validates CRIE specialties and quarantine scopes.
     */
    public synchronized void applySpecialtiesAndScope(Set<String> inputSpecialties, String scopeDescription) {
        if (scopeDescription != null) {
            String lowerScope = scopeDescription.toLowerCase();
            for (String excluded : EXCLUDED_SCOPES) {
                if (lowerScope.contains(excluded.toLowerCase())) {
                    quarantine("Excluded scope detected: " + excluded);
                    return;
                }
            }
        }

        if (inputSpecialties != null) {
            for (String spec : inputSpecialties) {
                if (spec != null) {
                    String lowerSpec = spec.toLowerCase();
                    for (String excluded : EXCLUDED_SCOPES) {
                        if (lowerSpec.contains(excluded.toLowerCase())) {
                            quarantine("Excluded specialty contour detected: " + spec);
                            return;
                        }
                    }
                }
            }

            Set<String> matched = new HashSet<>();
            for (String spec : inputSpecialties) {
                if (ALLOWED_CRIE_SPECIALTIES.contains(spec)) {
                    matched.add(spec);
                }
            }
            this.specialties = matched;
            if (matched.isEmpty() && !inputSpecialties.isEmpty()) {
                quarantine("No compliant CRIE specialties found in input: " + inputSpecialties);
                return;
            }
        }
        this.updatedAt = LocalDateTime.now();
    }

    /**
     * Quarantines document, removing it from active search and query indices.
     */
    public synchronized void quarantine(String reason) {
        this.quarantined = true;
        this.quarantineReason = reason;
        this.activeSearchFlag = false;
        this.vectorIndexEligible = false;
        pruneInvertedIndexTokens();
        this.updatedAt = LocalDateTime.now();
    }

    public boolean isSearchable() {
        return activeSearchFlag && !quarantined && status == ActStatus.ACTIVE;
    }

    // Getters and Setters

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

    public String getJurisdiction() {
        return jurisdiction;
    }

    public void setJurisdiction(String jurisdiction) {
        this.jurisdiction = jurisdiction;
    }

    public String getRegistrationNumber() {
        return registrationNumber;
    }

    public void setRegistrationNumber(String registrationNumber) {
        this.registrationNumber = registrationNumber;
    }

    public LocalDate getRegistrationDate() {
        return registrationDate;
    }

    public void setRegistrationDate(LocalDate registrationDate) {
        this.registrationDate = registrationDate;
    }

    public LocalDate getEffectiveStartDate() {
        return effectiveStartDate;
    }

    public void setEffectiveStartDate(LocalDate effectiveStartDate) {
        this.effectiveStartDate = effectiveStartDate;
    }

    public LocalDate getEffectiveEndDate() {
        return effectiveEndDate;
    }

    public void setEffectiveEndDate(LocalDate effectiveEndDate) {
        this.effectiveEndDate = effectiveEndDate;
    }

    public LocalDate getRepealedDate() {
        return repealedDate;
    }

    public void setRepealedDate(LocalDate repealedDate) {
        this.repealedDate = repealedDate;
    }

    public String getSupersededBy() {
        return supersededBy;
    }

    public void setSupersededBy(String supersededBy) {
        this.supersededBy = supersededBy;
    }

    public ActStatus getStatus() {
        return status;
    }

    public void setStatus(ActStatus status) {
        updateStatus(status);
    }

    public boolean isActiveSearchFlag() {
        return activeSearchFlag;
    }

    public void setActiveSearchFlag(boolean activeSearchFlag) {
        this.activeSearchFlag = activeSearchFlag;
    }

    public boolean isVectorIndexEligible() {
        return vectorIndexEligible;
    }

    public void setVectorIndexEligible(boolean vectorIndexEligible) {
        this.vectorIndexEligible = vectorIndexEligible;
    }

    public boolean isQuarantined() {
        return quarantined;
    }

    public void setQuarantined(boolean quarantined) {
        this.quarantined = quarantined;
    }

    public String getQuarantineReason() {
        return quarantineReason;
    }

    public void setQuarantineReason(String quarantineReason) {
        this.quarantineReason = quarantineReason;
    }

    public Set<String> getSpecialties() {
        return specialties;
    }

    public void setSpecialties(Set<String> specialties) {
        this.specialties = (specialties != null) ? new HashSet<>(specialties) : new HashSet<>();
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
    }

    public Map<String, Object> getMetadata() {
        return metadata;
    }

    public void setMetadata(Map<String, Object> metadata) {
        this.metadata = (metadata != null) ? new HashMap<>(metadata) : new HashMap<>();
    }

    public Long getVersion() {
        return version;
    }

    public void setVersion(Long version) {
        this.version = version;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(LocalDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        InternalEntity that = (InternalEntity) o;
        return Objects.equals(id, that.id) ||
                (Objects.equals(actNumber, that.actNumber) && Objects.equals(legalAuthority, that.legalAuthority));
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, actNumber, legalAuthority);
    }

    @Override
    public String toString() {
        return "InternalEntity{" +
                "id='" + id + '\'' +
                ", actNumber='" + actNumber + '\'' +
                ", title='" + title + '\'' +
                ", legalAuthority='" + legalAuthority + '\'' +
                ", status=" + status +
                ", activeSearchFlag=" + activeSearchFlag +
                ", quarantined=" + quarantined +
                ", specialties=" + specialties +
                '}' ;
    }
}
