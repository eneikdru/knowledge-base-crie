package com.eneik.crie.models.persistence;

import java.io.Serializable;
import java.time.Instant;
import java.util.Objects;
import java.util.UUID;

/**
 * Analytical query model and persistence entity for contingent enrollment,
 * academic progress, supervisor workload, and individual plan completion.
 */
public class InternalEntity implements Serializable {

    private static final long serialVersionUID = 1L;

    private String id;
    private String department;
    private String academicYear;
    private String contingentType; // e.g. "RESIDENT", "POSTGRADUATE"
    private String studentId;
    private String studentName;
    private String supervisorId;
    private String supervisorName;

    private Integer totalPlans;
    private Integer completedPlans;
    private Double plannedWorkloadHours;
    private Double actualWorkloadHours;
    private Integer supervisorStudentCount;
    private Integer maxSupervisorQuota;

    private Double progressPercentage;
    private Double workloadRatio;
    private String status;

    private Instant createdAt;
    private Instant updatedAt;

    public InternalEntity() {
        this.id = UUID.randomUUID().toString();
        this.totalPlans = 0;
        this.completedPlans = 0;
        this.plannedWorkloadHours = 0.0;
        this.actualWorkloadHours = 0.0;
        this.supervisorStudentCount = 0;
        this.maxSupervisorQuota = 0;
        this.progressPercentage = 0.0;
        this.workloadRatio = 0.0;
        this.status = "ACTIVE";
        this.createdAt = Instant.now();
        this.updatedAt = this.createdAt;
    }

    public InternalEntity(String department, String academicYear, String contingentType) {
        this();
        this.department = department;
        this.academicYear = academicYear;
        this.contingentType = contingentType;
    }

    public void prePersist() {
        if (this.id == null || this.id.trim().isEmpty()) {
            this.id = UUID.randomUUID().toString();
        }
        Instant now = Instant.now();
        if (this.createdAt == null) {
            this.createdAt = now;
        }
        if (this.updatedAt == null) {
            this.updatedAt = now;
        }
        recalculateDerivedMetrics();
    }

    public void preUpdate() {
        this.updatedAt = Instant.now();
        recalculateDerivedMetrics();
    }

    public void recalculateDerivedMetrics() {
        this.progressPercentage = calculateProgressPercentage();
        this.workloadRatio = calculateWorkloadRatio();
    }

    public double calculateProgressPercentage() {
        if (totalPlans == null || totalPlans <= 0) {
            return 0.0;
        }
        int completed = (completedPlans != null && completedPlans > 0) ? completedPlans : 0;
        double pct = ((double) completed / (double) totalPlans) * 100.0;
        return Math.min(100.0, Math.max(0.0, Math.round(pct * 100.0) / 100.0));
    }

    public double calculateWorkloadRatio() {
        if (plannedWorkloadHours != null && plannedWorkloadHours > 0.0) {
            double actual = (actualWorkloadHours != null && actualWorkloadHours > 0.0) ? actualWorkloadHours : 0.0;
            return Math.round((actual / plannedWorkloadHours) * 1000.0) / 1000.0;
        }
        if (maxSupervisorQuota != null && maxSupervisorQuota > 0) {
            int currentCount = (supervisorStudentCount != null && supervisorStudentCount > 0) ? supervisorStudentCount : 0;
            return Math.round(((double) currentCount / (double) maxSupervisorQuota) * 1000.0) / 1000.0;
        }
        return 0.0;
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getDepartment() {
        return department;
    }

    public void setDepartment(String department) {
        this.department = department;
    }

    public String getAcademicYear() {
        return academicYear;
    }

    public void setAcademicYear(String academicYear) {
        this.academicYear = academicYear;
    }

    public String getContingentType() {
        return contingentType;
    }

    public void setContingentType(String contingentType) {
        this.contingentType = contingentType;
    }

    public String getStudentId() {
        return studentId;
    }

    public void setStudentId(String studentId) {
        this.studentId = studentId;
    }

    public String getStudentName() {
        return studentName;
    }

    public void setStudentName(String studentName) {
        this.studentName = studentName;
    }

    public String getSupervisorId() {
        return supervisorId;
    }

    public void setSupervisorId(String supervisorId) {
        this.supervisorId = supervisorId;
    }

    public String getSupervisorName() {
        return supervisorName;
    }

    public void setSupervisorName(String supervisorName) {
        this.supervisorName = supervisorName;
    }

    public Integer getTotalPlans() {
        return totalPlans;
    }

    public void setTotalPlans(Integer totalPlans) {
        this.totalPlans = totalPlans;
        this.progressPercentage = calculateProgressPercentage();
    }

    public Integer getCompletedPlans() {
        return completedPlans;
    }

    public void setCompletedPlans(Integer completedPlans) {
        this.completedPlans = completedPlans;
        this.progressPercentage = calculateProgressPercentage();
    }

    public Double getPlannedWorkloadHours() {
        return plannedWorkloadHours;
    }

    public void setPlannedWorkloadHours(Double plannedWorkloadHours) {
        this.plannedWorkloadHours = plannedWorkloadHours;
        this.workloadRatio = calculateWorkloadRatio();
    }

    public Double getActualWorkloadHours() {
        return actualWorkloadHours;
    }

    public void setActualWorkloadHours(Double actualWorkloadHours) {
        this.actualWorkloadHours = actualWorkloadHours;
        this.workloadRatio = calculateWorkloadRatio();
    }

    public Integer getSupervisorStudentCount() {
        return supervisorStudentCount;
    }

    public void setSupervisorStudentCount(Integer supervisorStudentCount) {
        this.supervisorStudentCount = supervisorStudentCount;
        this.workloadRatio = calculateWorkloadRatio();
    }

    public Integer getMaxSupervisorQuota() {
        return maxSupervisorQuota;
    }

    public void setMaxSupervisorQuota(Integer maxSupervisorQuota) {
        this.maxSupervisorQuota = maxSupervisorQuota;
        this.workloadRatio = calculateWorkloadRatio();
    }

    public Double getProgressPercentage() {
        return progressPercentage != null ? progressPercentage : calculateProgressPercentage();
    }

    public void setProgressPercentage(Double progressPercentage) {
        this.progressPercentage = progressPercentage;
    }

    public Double getWorkloadRatio() {
        return workloadRatio != null ? workloadRatio : calculateWorkloadRatio();
    }

    public void setWorkloadRatio(Double workloadRatio) {
        this.workloadRatio = workloadRatio;
    }

    public String getStatus() {

        return status;
    }

    public void setStatus(String status) {
        this.status = status;
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
                ", department='" + department + '\'' +
                ", academicYear='" + academicYear + '\'' +
                ", contingentType='" + contingentType + '\'' +
                ", studentId='" + studentId + '\'' +
                ", supervisorId='" + supervisorId + '\'' +
                ", progressPercentage=" + progressPercentage +
                ", workloadRatio=" + workloadRatio +
                ", status='" + status + '\'' +
                '}';
    }
}
