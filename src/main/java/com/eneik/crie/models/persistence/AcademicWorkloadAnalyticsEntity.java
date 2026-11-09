package com.eneik.crie.models.persistence;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.Objects;

public class AcademicWorkloadAnalyticsEntity {

    private String id;
    private String departmentId;
    private String departmentName;
    private String academicYear;
    private String contingentType;
    private String supervisorId;
    private String supervisorName;
    private int enrolledCount;
    private int activePlansCount;
    private int completedMilestones;
    private int totalMilestones;
    private BigDecimal supervisorAssignedHours;
    private BigDecimal supervisorMaxHours;
    private BigDecimal progressPercentage;
    private BigDecimal workloadRatio;
    private Instant createdAt;
    private Instant updatedAt;

    public AcademicWorkloadAnalyticsEntity() {
        this.supervisorAssignedHours = BigDecimal.ZERO;
        this.supervisorMaxHours = BigDecimal.ZERO;
        this.progressPercentage = BigDecimal.ZERO;
        this.workloadRatio = BigDecimal.ZERO;
        this.createdAt = Instant.now();
        this.updatedAt = Instant.now();
    }

    public AcademicWorkloadAnalyticsEntity(
            String id,
            String departmentId,
            String departmentName,
            String academicYear,
            String contingentType,
            String supervisorId,
            String supervisorName,
            int enrolledCount,
            int activePlansCount,
            int completedMilestones,
            int totalMilestones,
            BigDecimal supervisorAssignedHours,
            BigDecimal supervisorMaxHours) {
        this.id = id;
        this.departmentId = departmentId;
        this.departmentName = departmentName;
        this.academicYear = academicYear;
        this.contingentType = contingentType;
        this.supervisorId = supervisorId;
        this.supervisorName = supervisorName;
        this.enrolledCount = enrolledCount;
        this.activePlansCount = activePlansCount;
        this.completedMilestones = completedMilestones;
        this.totalMilestones = totalMilestones;
        this.supervisorAssignedHours = Objects.requireNonNullElse(supervisorAssignedHours, BigDecimal.ZERO);
        this.supervisorMaxHours = Objects.requireNonNullElse(supervisorMaxHours, BigDecimal.ZERO);
        this.createdAt = Instant.now();
        this.updatedAt = Instant.now();
        recalculateMetrics();
    }

    public void recalculateMetrics() {
        if (totalMilestones <= 0 || completedMilestones <= 0) {
            this.progressPercentage = BigDecimal.ZERO.setScale(2, RoundingMode.HALF_UP);
        } else {
            BigDecimal completed = BigDecimal.valueOf(Math.min(completedMilestones, totalMilestones));
            BigDecimal total = BigDecimal.valueOf(totalMilestones);
            this.progressPercentage = completed
                    .multiply(BigDecimal.valueOf(100))
                    .divide(total, 2, RoundingMode.HALF_UP);
        }

        BigDecimal assigned = Objects.requireNonNullElse(this.supervisorAssignedHours, BigDecimal.ZERO);
        BigDecimal max = Objects.requireNonNullElse(this.supervisorMaxHours, BigDecimal.ZERO);
        if (max.compareTo(BigDecimal.ZERO) <= 0 || assigned.compareTo(BigDecimal.ZERO) <= 0) {
            this.workloadRatio = BigDecimal.ZERO.setScale(2, RoundingMode.HALF_UP);
        } else {
            this.workloadRatio = assigned
                    .divide(max, 4, RoundingMode.HALF_UP)
                    .setScale(2, RoundingMode.HALF_UP);
        }
        this.updatedAt = Instant.now();
    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getDepartmentId() {
        return departmentId;
    }

    public void setDepartmentId(String departmentId) {
        this.departmentId = departmentId;
    }

    public String getDepartmentName() {
        return departmentName;
    }

    public void setDepartmentName(String departmentName) {
        this.departmentName = departmentName;
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

    public int getEnrolledCount() {
        return enrolledCount;
    }

    public void setEnrolledCount(int enrolledCount) {
        this.enrolledCount = enrolledCount;
    }

    public int getActivePlansCount() {
        return activePlansCount;
    }

    public void setActivePlansCount(int activePlansCount) {
        this.activePlansCount = activePlansCount;
    }

    public int getCompletedMilestones() {
        return completedMilestones;
    }

    public void setCompletedMilestones(int completedMilestones) {
        this.completedMilestones = completedMilestones;
        recalculateMetrics();
    }

    public int getTotalMilestones() {
        return totalMilestones;
    }

    public void setTotalMilestones(int totalMilestones) {
        this.totalMilestones = totalMilestones;
        recalculateMetrics();
    }

    public BigDecimal getSupervisorAssignedHours() {
        return supervisorAssignedHours;
    }

    public void setSupervisorAssignedHours(BigDecimal supervisorAssignedHours) {
        this.supervisorAssignedHours = Objects.requireNonNullElse(supervisorAssignedHours, BigDecimal.ZERO);
        recalculateMetrics();
    }

    public BigDecimal getSupervisorMaxHours() {
        return supervisorMaxHours;
    }

    public void setSupervisorMaxHours(BigDecimal supervisorMaxHours) {
        this.supervisorMaxHours = Objects.requireNonNullElse(supervisorMaxHours, BigDecimal.ZERO);
        recalculateMetrics();
    }

    public BigDecimal getProgressPercentage() {
        return progressPercentage;
    }

    public BigDecimal getWorkloadRatio() {
        return workloadRatio;
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
}
