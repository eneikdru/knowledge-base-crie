package com.eneik.crie.models.persistence;

import java.io.Serializable;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.Objects;

/**
 * Persistence entity representing aggregated academic contingent, supervisor workload,
 * and individual curriculum plan execution records for analytical querying.
 */
public class InternalEntity implements Serializable {

    private static final long serialVersionUID = 1L;

    private Long id;
    private String contingentType; // RESIDENT, POSTGRADUATE
    private String departmentId;
    private String academicYear;
    private String supervisorId;
    private String studentId;
    private Integer totalCurriculumTasks;
    private Integer completedCurriculumTasks;
    private BigDecimal supervisorAllocatedHours;
    private BigDecimal supervisorMaxHoursLimit;
    private String planStatus; // IN_PROGRESS, COMPLETED, DEFENDED, OVERDUE
    private Instant createdAt;
    private Instant updatedAt;

    public InternalEntity() {
        this.createdAt = Instant.now();
        this.updatedAt = Instant.now();
        this.totalCurriculumTasks = 0;
        this.completedCurriculumTasks = 0;
        this.supervisorAllocatedHours = BigDecimal.ZERO;
        this.supervisorMaxHoursLimit = BigDecimal.ZERO;
    }

    public InternalEntity(
            Long id,
            String contingentType,
            String departmentId,
            String academicYear,
            String supervisorId,
            String studentId,
            Integer totalCurriculumTasks,
            Integer completedCurriculumTasks,
            BigDecimal supervisorAllocatedHours,
            BigDecimal supervisorMaxHoursLimit,
            String planStatus) {
        this.id = id;
        this.contingentType = contingentType;
        this.departmentId = departmentId;
        this.academicYear = academicYear;
        this.supervisorId = supervisorId;
        this.studentId = studentId;
        this.totalCurriculumTasks = totalCurriculumTasks != null ? totalCurriculumTasks : 0;
        this.completedCurriculumTasks = completedCurriculumTasks != null ? completedCurriculumTasks : 0;
        this.supervisorAllocatedHours = supervisorAllocatedHours != null ? supervisorAllocatedHours : BigDecimal.ZERO;
        this.supervisorMaxHoursLimit = supervisorMaxHoursLimit != null ? supervisorMaxHoursLimit : BigDecimal.ZERO;
        this.planStatus = planStatus != null ? planStatus : "IN_PROGRESS";
        this.createdAt = Instant.now();
        this.updatedAt = Instant.now();
    }

    /**
     * Calculates curriculum plan completion percentage with zero null-pointer and division-by-zero anomaly guarantees.
     * @return percentage from 0.00 to 100.00
     */
    public BigDecimal calculateProgressPercentage() {
        if (totalCurriculumTasks == null || totalCurriculumTasks <= 0) {
            return BigDecimal.ZERO.setScale(2, RoundingMode.HALF_UP);
        }
        int completed = completedCurriculumTasks != null ? Math.max(0, completedCurriculumTasks) : 0;
        BigDecimal comp = BigDecimal.valueOf(completed);
        BigDecimal tot = BigDecimal.valueOf(totalCurriculumTasks);
        return comp.multiply(BigDecimal.valueOf(100)).divide(tot, 2, RoundingMode.HALF_UP);
    }

    /**
     * Calculates supervisor workload utilization ratio safely without null or division by zero errors.
     * @return workload ratio (allocated / max limit)
     */
    public BigDecimal calculateSupervisorWorkloadRatio() {
        BigDecimal limit = supervisorMaxHoursLimit != null ? supervisorMaxHoursLimit : BigDecimal.ZERO;
        if (limit.compareTo(BigDecimal.ZERO) <= 0) {
            return BigDecimal.ZERO.setScale(2, RoundingMode.HALF_UP);
        }
        BigDecimal allocated = supervisorAllocatedHours != null ? supervisorAllocatedHours : BigDecimal.ZERO;
        return allocated.divide(limit, 4, RoundingMode.HALF_UP);
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getContingentType() {
        return contingentType;
    }

    public void setContingentType(String contingentType) {
        this.contingentType = contingentType;
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

    public String getSupervisorId() {
        return supervisorId;
    }

    public void setSupervisorId(String supervisorId) {
        this.supervisorId = supervisorId;
    }

    public String getStudentId() {
        return studentId;
    }

    public void setStudentId(String studentId) {
        this.studentId = studentId;
    }

    public Integer getTotalCurriculumTasks() {
        return totalCurriculumTasks;
    }

    public void setTotalCurriculumTasks(Integer totalCurriculumTasks) {
        this.totalCurriculumTasks = totalCurriculumTasks != null ? totalCurriculumTasks : 0;
    }

    public Integer getCompletedCurriculumTasks() {
        return completedCurriculumTasks;
    }

    public void setCompletedCurriculumTasks(Integer completedCurriculumTasks) {
        this.completedCurriculumTasks = completedCurriculumTasks != null ? completedCurriculumTasks : 0;
    }

    public BigDecimal getSupervisorAllocatedHours() {
        return supervisorAllocatedHours;
    }

    public void setSupervisorAllocatedHours(BigDecimal supervisorAllocatedHours) {
        this.supervisorAllocatedHours = supervisorAllocatedHours != null ? supervisorAllocatedHours : BigDecimal.ZERO;
    }

    public BigDecimal getSupervisorMaxHoursLimit() {
        return supervisorMaxHoursLimit;
    }

    public void setSupervisorMaxHoursLimit(BigDecimal supervisorMaxHoursLimit) {
        this.supervisorMaxHoursLimit = supervisorMaxHoursLimit != null ? supervisorMaxHoursLimit : BigDecimal.ZERO;
    }

    public String getPlanStatus() {
        return planStatus;
    }

    public void setPlanStatus(String planStatus) {
        this.planStatus = planStatus;
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
        return Objects.equals(id, that.id) &&
                Objects.equals(studentId, that.studentId) &&
                Objects.equals(departmentId, that.departmentId) &&
                Objects.equals(academicYear, that.academicYear);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, studentId, departmentId, academicYear);
    }

    @Override
    public String toString() {
        return "InternalEntity{" +
                "id=" + id +
                ", contingentType='" + contingentType + '\'' +
                ", departmentId='" + departmentId + '\'' +
                ", academicYear='" + academicYear + '\'' +
                ", supervisorId='" + supervisorId + '\'' +
                ", studentId='" + studentId + '\'' +
                ", totalCurriculumTasks=" + totalCurriculumTasks +
                ", completedCurriculumTasks=" + completedCurriculumTasks +
                ", supervisorAllocatedHours=" + supervisorAllocatedHours +
                ", supervisorMaxHoursLimit=" + supervisorMaxHoursLimit +
                ", planStatus='" + planStatus + '\'' +
                ", createdAt=" + createdAt +
                ", updatedAt=" + updatedAt +
                '}';
    }
}
