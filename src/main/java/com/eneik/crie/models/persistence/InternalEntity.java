package com.eneik.crie.models.persistence;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;

/**
 * Persistence domain entity for CRIE regulatory normative acts and their validity states.
 */
public class InternalEntity {

    public enum ActStatus {
        ACTIVE("active"),
        REPEALED("repealed"),
        SUPERSEDED("superseded");

        private final String value;

        ActStatus(String value) {
            this.value = value;
        }

        public String getValue() {
            return value;
        }

        public static ActStatus fromString(String text) {
            if (text == null) {
                return null;
            }
            for (ActStatus b : ActStatus.values()) {
                if (b.value.equalsIgnoreCase(text.trim()) || b.name().equalsIgnoreCase(text.trim())) {
                    return b;
                }
            }
            return null;
        }
    }

    public static final Set<String> ALLOWED_CRIE_SPECIALTIES;
    static {
        Set<String> specialties = new HashSet<>();
        // Residency (Ординатура)
        specialties.add("32.08.12"); // Эпидемиология
        specialties.add("31.08.35"); // Инфекционные болезни
        specialties.add("31.08.19"); // Педиатрия
        // Postgraduate (Аспирантура)
        specialties.add("3.2.2");   // Эпидемиология
        specialties.add("3.1.22");  // Инфекционные болезни
        ALLOWED_CRIE_SPECIALTIES = Collections.unmodifiableSet(specialties);
    }

    private String id;
    private String title;
    private String actType;
    private String legalAuthority;
    private ActStatus status = ActStatus.ACTIVE;
    private LocalDate effectiveStartDate;
    private LocalDate effectiveEndDate;
    private Set<String> specialtyCodes = new HashSet<>();
    private String scope;
    private boolean activeSearchFlag = true;
    private boolean quarantined = false;
    private String quarantineReason;
    private List<String> invertedIndexTokens = new ArrayList<>();

    public InternalEntity() {
    }

    public InternalEntity(String id, String title, String actType, String legalAuthority) {
        this.id = id;
        this.title = title;
        this.actType = actType;
        this.legalAuthority = legalAuthority;
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
    }

    public String getActType() {
        return actType;
    }

    public void setActType(String actType) {
        this.actType = actType;
    }

    public String getLegalAuthority() {
        return legalAuthority;
    }

    public void setLegalAuthority(String legalAuthority) {
        this.legalAuthority = legalAuthority;
    }

    public ActStatus getStatus() {
        return status;
    }

    public void setStatus(ActStatus status) {
        this.status = status;
        evaluateValidity(LocalDate.now());
    }

    public void setStatus(String statusStr) {
        ActStatus parsed = ActStatus.fromString(statusStr);
        this.status = parsed != null ? parsed : ActStatus.REPEALED;
        evaluateValidity(LocalDate.now());
    }

    public LocalDate getEffectiveStartDate() {
        return effectiveStartDate;
    }

    public void setEffectiveStartDate(LocalDate effectiveStartDate) {
        this.effectiveStartDate = effectiveStartDate;
        evaluateValidity(LocalDate.now());
    }

    public LocalDate getEffectiveEndDate() {
        return effectiveEndDate;
    }

    public void setEffectiveEndDate(LocalDate effectiveEndDate) {
        this.effectiveEndDate = effectiveEndDate;
        evaluateValidity(LocalDate.now());
    }

    public Set<String> getSpecialtyCodes() {
        return specialtyCodes;
    }

    public void setSpecialtyCodes(Set<String> specialtyCodes) {
        this.specialtyCodes = specialtyCodes != null ? new HashSet<>(specialtyCodes) : new HashSet<>();
        validateSpecialtyScope();
    }

    public void addSpecialtyCode(String code) {
        if (code != null) {
            this.specialtyCodes.add(code.trim());
            validateSpecialtyScope();
        }
    }

    public String getScope() {
        return scope;
    }

    public void setScope(String scope) {
        this.scope = scope;
        validateSpecialtyScope();
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
            pruneInvertedIndexTokens();
        }
    }

    public String getQuarantineReason() {
        return quarantineReason;
    }

    public void setQuarantineReason(String quarantineReason) {
        this.quarantineReason = quarantineReason;
    }

    public List<String> getInvertedIndexTokens() {
        return invertedIndexTokens;
    }

    public void setInvertedIndexTokens(List<String> invertedIndexTokens) {
        this.invertedIndexTokens = invertedIndexTokens != null ? new ArrayList<>(invertedIndexTokens) : new ArrayList<>();
    }

    public void pruneInvertedIndexTokens() {
        if (this.invertedIndexTokens != null) {
            this.invertedIndexTokens.clear();
        }
    }

    public boolean evaluateValidity(LocalDate referenceDate) {
        LocalDate today = referenceDate != null ? referenceDate : LocalDate.now();

        boolean isRepealedOrSuperseded = this.status == ActStatus.REPEALED || this.status == ActStatus.SUPERSEDED;
        boolean isExpired = this.effectiveEndDate != null && this.effectiveEndDate.isBefore(today);
        boolean notYetEffective = this.effectiveStartDate != null && this.effectiveStartDate.isAfter(today);

        if (isRepealedOrSuperseded || isExpired || notYetEffective || this.quarantined) {
            this.activeSearchFlag = false;
            pruneInvertedIndexTokens();
            return false;
        }

        this.activeSearchFlag = true;
        return true;
    }

    public boolean validateSpecialtyScope() {
        // Exclude general microbiology
        if (this.scope != null) {
            String lowerScope = this.scope.toLowerCase();
            if (lowerScope.contains("microbiology") || lowerScope.contains("микробиолог")) {
                this.quarantined = true;
                this.quarantineReason = "Excluded scope: microbiology";
                this.activeSearchFlag = false;
                pruneInvertedIndexTokens();
                return false;
            }
        }

        // If specialties are assigned, check if at least one matches CRIE contour
        if (!this.specialtyCodes.isEmpty()) {
            boolean hasAllowedSpecialty = false;
            for (String code : this.specialtyCodes) {
                if (ALLOWED_CRIE_SPECIALTIES.contains(code)) {
                    hasAllowedSpecialty = true;
                    break;
                }
            }
            if (!hasAllowedSpecialty) {
                this.quarantined = true;
                this.quarantineReason = "No matching allowed CRIE specialty contour";
                this.activeSearchFlag = false;
                pruneInvertedIndexTokens();
                return false;
            }
        }

        return true;
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

    @Override
    public String toString() {
        return "InternalEntity{" +
                "id='" + id + '\'' +
                ", title='" + title + '\'' +
                ", actType='" + actType + '\'' +
                ", legalAuthority='" + legalAuthority + '\'' +
                ", status=" + status +
                ", activeSearchFlag=" + activeSearchFlag +
                ", quarantined=" + quarantined +
                '}';
    }
}
