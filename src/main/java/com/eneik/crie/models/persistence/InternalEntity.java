package com.eneik.crie.models.persistence;

import java.time.LocalDate;
import java.util.Collections;
import java.util.HashSet;
import java.util.Objects;
import java.util.Set;

/**
 * Represents a normative regulatory act entity within the CRIE corpus schema.
 * Enforces status tracking (ACTIVE, REPEALED, SUPERSEDED), legal authority metadata,
 * and strict CRIE specialty mappings (Residency: 32.08.12, 31.08.35, 31.08.19; Aspirantura: 3.2.2, 3.1.22).
 */
public class InternalEntity {

    public enum NormativeStatus {
        ACTIVE,
        REPEALED,
        SUPERSEDED
    }

    public static final Set<String> ALLOWED_SPECIALTIES = Set.of(
        "32.08.12", // Residency: Epidemiology
        "31.08.35", // Residency: Infectious Diseases
        "31.08.19", // Residency: Pediatrics
        "3.2.2",    // Aspirantura: Epidemiology
        "3.1.22"    // Aspirantura: Infectious Diseases
    );

    public static final String EXCLUDED_MICROBIOLOGY_KEYWORD = "microbiology";

    private String id;
    private String title;
    private String documentNumber;
    private String legalAuthority;
    private NormativeStatus status;
    private LocalDate effectiveStartDate;
    private LocalDate effectiveEndDate;
    private Set<String> specialties = new HashSet<>();
    private boolean activeSearch;
    private boolean quarantined;

    public InternalEntity() {
        this.status = NormativeStatus.ACTIVE;
        this.activeSearch = true;
        this.quarantined = false;
    }

    public InternalEntity(String id,
                          String title,
                          String documentNumber,
                          String legalAuthority,
                          NormativeStatus status,
                          LocalDate effectiveStartDate,
                          LocalDate effectiveEndDate,
                          Set<String> specialties) {
        this.id = id;
        this.title = title;
        this.documentNumber = documentNumber;
        this.legalAuthority = legalAuthority;
        this.status = status != null ? status : NormativeStatus.ACTIVE;
        this.effectiveStartDate = effectiveStartDate;
        this.effectiveEndDate = effectiveEndDate;
        if (specialties != null) {
            this.specialties = new HashSet<>(specialties);
        }
        evaluateSearchEligibility(LocalDate.now());
    }

    /**
     * Evaluates whether the entity is eligible for vector and inverted search indices.
     * Deactivates search if the act is repealed, superseded, expired by date, or contains excluded scope (microbiology).
     */
    public void evaluateSearchEligibility(LocalDate referenceDate) {
        boolean containsExcludedScope = title != null && title.toLowerCase().contains(EXCLUDED_MICROBIOLOGY_KEYWORD);
        if (containsExcludedScope) {
            this.quarantined = true;
            this.activeSearch = false;
            return;
        }

        boolean isStatusInvalid = (status == NormativeStatus.REPEALED || status == NormativeStatus.SUPERSEDED);
        boolean isDateExpired = (effectiveEndDate != null && referenceDate != null && referenceDate.isAfter(effectiveEndDate));

        if (isStatusInvalid || isDateExpired) {
            this.activeSearch = false;
        } else {
            this.activeSearch = hasValidCrieSpecialty();
        }
    }

    public boolean hasValidCrieSpecialty() {
        if (specialties == null || specialties.isEmpty()) {
            return false;
        }
        for (String specialty : specialties) {
            if (ALLOWED_SPECIALTIES.contains(specialty)) {
                return true;
            }
        }
        return false;
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
        evaluateSearchEligibility(LocalDate.now());
    }

    public String getDocumentNumber() {
        return documentNumber;
    }

    public void setDocumentNumber(String documentNumber) {
        this.documentNumber = documentNumber;
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
        evaluateSearchEligibility(LocalDate.now());
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
        evaluateSearchEligibility(LocalDate.now());
    }

    public Set<String> getSpecialties() {
        return Collections.unmodifiableSet(specialties);
    }

    public void setSpecialties(Set<String> specialties) {
        this.specialties = specialties != null ? new HashSet<>(specialties) : new HashSet<>();
        evaluateSearchEligibility(LocalDate.now());
    }

    public void addSpecialty(String specialty) {
        if (specialty != null) {
            this.specialties.add(specialty);
            evaluateSearchEligibility(LocalDate.now());
        }
    }

    public boolean isActiveSearch() {
        return activeSearch;
    }

    public void setActiveSearch(boolean activeSearch) {
        this.activeSearch = activeSearch;
    }

    public boolean isQuarantined() {
        return quarantined;
    }

    public void setQuarantined(boolean quarantined) {
        this.quarantined = quarantined;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        InternalEntity that = (InternalEntity) o;
        return Objects.equals(id, that.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
    }
}
