package com.eneik.crie.models.persistence;

import java.io.Serializable;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.Objects;

/**
 * Persistence entity representing aggregated academic contingent and workload analytics.
 * Supports analytical queries across postgraduates, residents, individual plan completion,
 * and supervisor workload ratios.
 */
public class InternalEntity implements Serializable {

    private static final long serialVersionUID = 1L;

    private Long id;
    private String departmentId;
    private String academicYear;
    private String contingentType; // RESIDENT, POSTGRADUATE, etc.
    private Long studentCount;
    private Long completedPlansCount;
    private Long totalAssignedPlansCount;
    private Long supervisorCount;
    private BigDecimal totalWorkloadHours;
    private Instant createdAt;
    private Instant updatedAt;

    public InternalEntity() {
        this.studentCount = 0L;
        this.completedPlansCount = 0L;
        this.totalAssignedPlansCount = 0L;
        this.supervisorCount = 0L;
        this.totalWorkloadHours = BigDecimal.ZERO;
        this.createdAt = Instant.now();
        this.updatedAt = Instant.now();
    }

    public InternalEntity(Long id, String departmentId, String academicYear, String contingentType) {
        this();
        this.id = id;
        this.departmentId = departmentId;
        this.academicYear = academicYear;
        this.contingentType = contingentType;
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getDepartmentId() {
        return departmentId;
    }

    public void setDepartmentId(String departmentId) {
        this.departmentId = departmentId;
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

    public Long getStudentCount() {
        return studentCount != null ? studentCount : 0L;
    }

    public void setStudentCount(Long studentCount) {
        this.studentCount = studentCount != null ? studentCount : 0L;
    }

    public Long getCompletedPlansCount() {
        return completedPlansCount != null ? completedPlansCount : 0L;
    }

    public void setCompletedPlansCount(Long completedPlansCount) {
        this.completedPlansCount = completedPlansCount != null ? completedPlansCount : 0L;
    }

    public Long getTotalAssignedPlansCount() {
        return totalAssignedPlansCount != null ? totalAssignedPlansCount : 0L;
    }

    public void setTotalAssignedPlansCount(Long totalAssignedPlansCount) {
        this.totalAssignedPlansCount = totalAssignedPlansCount != null ? totalAssignedPlansCount : 0L;
    }

    public Long getSupervisorCount() {
        return supervisorCount != null ? supervisorCount : 0L;
    }

    public void setSupervisorCount(Long supervisorCount) {
        this.supervisorCount = supervisorCount != null ? supervisorCount : 0L;
    }

    public BigDecimal getTotalWorkloadHours() {
        return totalWorkloadHours != null ? totalWorkloadHours : BigDecimal.ZERO;
    }

    public void setTotalWorkloadHours(BigDecimal totalWorkloadHours) {
        this.totalWorkloadHours = totalWorkloadHours != null ? totalWorkloadHours : BigDecimal.ZERO;
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

    /**
     * Calculates student progress percentage (completed plans / total assigned plans * 100).
     * Returns 0.0 with zero null-pointer anomalies when total assigned plans is 0 or unassigned.
     */
    public double calculateStudentProgressPercentage() {
        long total = getTotalAssignedPlansCount();
        if (total == 0L) {
            return 0.0;
        }
        long completed = getCompletedPlansCount();
        return BigDecimal.valueOf(completed)
                .multiply(BigDecimal.valueOf(100))
                .divide(BigDecimal.valueOf(total), 2, RoundingMode.HALF_UP)
                .doubleValue();
    }

    /**
     * Calculates supervisor workload ratio (students / supervisor).
     * Returns 0.0 with zero null-pointer anomalies when supervisor count is 0 or unassigned.
     */
    public double calculateSupervisorWorkloadRatio() {
        long supervisors = getSupervisorCount();
        if (supervisors == 0L) {
            return 0.0;
        }
        long students = getStudentCount();
        return BigDecimal.valueOf(students)
                .divide(BigDecimal.valueOf(supervisors), 2, RoundingMode.HALF_UP)
                .doubleValue();
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        InternalEntity that = (InternalEntity) o;
        return Objects.equals(id, that.id) &&
                Objects.equals(departmentId, that.departmentId) &&
                Objects.equals(academicYear, that.academicYear) &&
                Objects.equals(contingentType, that.contingentType);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, departmentId, academicYear, contingentType);
    }

    @Override
    public String toString() {
        return "InternalEntity{" +
                "id=" + id +
                ", departmentId='" + departmentId + '\'' +
                ", academicYear='" + academicYear + '\'' +
                ", contingentType='" + contingentType + '\'' +
                ", studentCount=" + studentCount +
                ", completedPlansCount=" + completedPlansCount +
                ", totalAssignedPlansCount=" + totalAssignedPlansCount +
                ", supervisorCount=" + supervisorCount +
                ", totalWorkloadHours=" + totalWorkloadHours +
                '}';
    }
}
