package com.eneik.crie.models.persistence;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.Collections;
import java.util.HashSet;
import java.util.Objects;
import java.util.Set;

/**
 * Persistence entity representing a normative act within the CRIE corpus.
 * Manages status tags (ACTIVE, REPEALED, SUPERSEDED), legal authority metadata,
 * active search indexing state, and strict CRIE specialty mapping.
 */
public class InternalEntity {

    public enum NormativeStatus {
        ACTIVE,
        REPEALED,
        SUPERSEDED
    }

    /**
     * Approved CRIE specialties:
     * Residency (Ordinatura): 32.08.12 (Epidemiology), 31.08.35 (Infectious Diseases), 31.08.19 (Pediatrics)
     * Postgraduate (Aspirantura): 3.2.2 (Epidemiology), 3.1.22 (Infectious Diseases)
     */
    public static final Set<String> ALLOWED_SPECIALTIES = Set.of(
            "32.08.12",
            "31.08.35",
            "31.08.19",
            "3.2.2",
            "3.1.22"
    );

    private Long id;
    private String actNumber;
    private String title;
    private String legalAuthority;
    private NormativeStatus status = NormativeStatus.ACTIVE;
    private LocalDate effectiveStartDate;
    private LocalDate effectiveEndDate;
    private boolean activeSearchFlag = true;
    private boolean quarantined = false;
    private Set<String> specialtyCodes = new HashSet<>();
    private Set<String> invertedIndexTokens = new HashSet<>();
    private OffsetDateTime updatedAt;

    public InternalEntity() {
    }

    public InternalEntity(Long id, String actNumber, String title, String legalAuthority) {
        this.id = id;
        this.actNumber = actNumber;
        this.title = title;
        this.legalAuthority = legalAuthority;
        this.updatedAt = OffsetDateTime.now();
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
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

    public String getLegalAuthority() {
        return legalAuthority;
    }

    public void setLegalAuthority(String legalAuthority) {
        this.legalAuthority = legalAuthority;
    }

    public NormativeStatus getStatus() {
        return status;
    }

    public void setStatus(NormativeStatus status) {
        this.status = status;
        recalculateSearchAndIndexingState(LocalDate.now());
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
        recalculateSearchAndIndexingState(LocalDate.now());
    }

    public boolean isActiveSearchFlag() {
        return activeSearchFlag;
    }

    public void setActiveSearchFlag(boolean activeSearchFlag) {
        this.activeSearchFlag = activeSearchFlag;
    }

    public boolean isQuarantined() {
        return quarantined;
    }

    public void setQuarantined(boolean quarantined) {
        this.quarantined = quarantined;
        if (quarantined) {
            this.activeSearchFlag = false;
            this.invertedIndexTokens.clear();
        }
    }

    public Set<String> getSpecialtyCodes() {
        return Collections.unmodifiableSet(specialtyCodes);
    }

    public void setSpecialtyCodes(Set<String> codes) {
        this.specialtyCodes = new HashSet<>();
        if (codes != null) {
            for (String code : codes) {
                addSpecialtyCode(code);
            }
        }
    }

    public void addSpecialtyCode(String code) {
        if (code == null) {
            return;
        }
        String trimmed = code.trim();
        if (ALLOWED_SPECIALTIES.contains(trimmed)) {
            this.specialtyCodes.add(trimmed);
        } else {
            // Excluded scopes (e.g. general microbiology or non-CRIE specialty) trigger quarantine
            this.quarantined = true;
            this.activeSearchFlag = false;
            this.invertedIndexTokens.clear();
        }
    }

    public Set<String> getInvertedIndexTokens() {
        return Collections.unmodifiableSet(invertedIndexTokens);
    }

    public void setInvertedIndexTokens(Set<String> tokens) {
        this.invertedIndexTokens = tokens != null ? new HashSet<>(tokens) : new HashSet<>();
        if (!this.activeSearchFlag || this.quarantined) {
            this.invertedIndexTokens.clear();
        }
    }

    public OffsetDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(OffsetDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }

    /**
     * Evaluates whether the normative act remains valid at the given reference date.
     * If repealed, superseded, expired, or quarantined, disables the active search flag
     * and prunes inverted index tokens.
     */
    public void recalculateSearchAndIndexingState(LocalDate referenceDate) {
        boolean isExpired = effectiveEndDate != null && referenceDate != null && referenceDate.isAfter(effectiveEndDate);
        boolean isInvalid = status == NormativeStatus.REPEALED || status == NormativeStatus.SUPERSEDED || isExpired || quarantined;

        if (isInvalid) {
            this.activeSearchFlag = false;
            this.invertedIndexTokens.clear();
        } else {
            this.activeSearchFlag = true;
        }
        this.updatedAt = OffsetDateTime.now();
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        InternalEntity that = (InternalEntity) o;
        return Objects.equals(id, that.id) && Objects.equals(actNumber, that.actNumber);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, actNumber);
    }
}
