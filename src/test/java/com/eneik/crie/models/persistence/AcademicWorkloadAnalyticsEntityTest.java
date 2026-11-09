package com.eneik.crie.models.persistence;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

class AcademicWorkloadAnalyticsEntityTest {

    @Test
    @DisplayName("Should initialize with default zero values and zero progress/workload ratio")
    void testDefaultValues() {
        AcademicWorkloadAnalyticsEntity entity = new AcademicWorkloadAnalyticsEntity();
        assertNotNull(entity.getProgressPercentage());
        assertNotNull(entity.getWorkloadRatio());
        assertEquals(BigDecimal.ZERO, entity.getProgressPercentage());
        assertEquals(BigDecimal.ZERO, entity.getWorkloadRatio());
    }

    @Test
    @DisplayName("Should calculate progress and workload ratio correctly with zero null-pointer anomalies")
    void testMetricCalculation() {
        AcademicWorkloadAnalyticsEntity entity = new AcademicWorkloadAnalyticsEntity(
                "analytics-1",
                "dept-pulm",
                "Department of Pulmonology",
                "2026-2027",
                "RESIDENT",
                "sup-101",
                "Prof. Ivanov",
                15,
                15,
                75,
                100,
                new BigDecimal("120.00"),
                new BigDecimal("150.00")
        );

        assertEquals(new BigDecimal("75.00"), entity.getProgressPercentage());
        assertEquals(new BigDecimal("0.80"), entity.getWorkloadRatio());
    }

    @Test
    @DisplayName("Should prevent division by zero gracefully when total milestones or max hours are zero")
    void testZeroDivisionSafety() {
        AcademicWorkloadAnalyticsEntity entity = new AcademicWorkloadAnalyticsEntity(
                "analytics-2",
                "dept-surg",
                "Department of Surgery",
                "2026-2027",
                "POSTGRADUATE",
                "sup-102",
                "Prof. Smirnov",
                5,
                5,
                0,
                0,
                new BigDecimal("50.00"),
                BigDecimal.ZERO
        );

        assertEquals(new BigDecimal("0.00"), entity.getProgressPercentage());
        assertEquals(new BigDecimal("0.00"), entity.getWorkloadRatio());
    }

    @Test
    @DisplayName("Should handle null hour values safely on setters")
    void testNullHourSetters() {
        AcademicWorkloadAnalyticsEntity entity = new AcademicWorkloadAnalyticsEntity();
        entity.setTotalMilestones(50);
        entity.setCompletedMilestones(25);
        entity.setSupervisorAssignedHours(null);
        entity.setSupervisorMaxHours(null);

        assertEquals(new BigDecimal("50.00"), entity.getProgressPercentage());
        assertEquals(new BigDecimal("0.00"), entity.getWorkloadRatio());
    }
}
