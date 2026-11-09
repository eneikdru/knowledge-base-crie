-- Academic Contingent & Workload Analytics Schema
-- Migration reserved version: V20261109224031677

CREATE TABLE IF NOT EXISTS academic_workload_analytics (
    id VARCHAR(64) PRIMARY KEY,
    department_id VARCHAR(64) NOT NULL,
    department_name VARCHAR(255) NOT NULL,
    academic_year VARCHAR(16) NOT NULL,
    contingent_type VARCHAR(32) NOT NULL, -- RESIDENT, POSTGRADUATE
    supervisor_id VARCHAR(64) NOT NULL,
    supervisor_name VARCHAR(255) NOT NULL,
    enrolled_count INT NOT NULL DEFAULT 0,
    active_plans_count INT NOT NULL DEFAULT 0,
    completed_milestones INT NOT NULL DEFAULT 0,
    total_milestones INT NOT NULL DEFAULT 0,
    supervisor_assigned_hours NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    supervisor_max_hours NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    progress_percentage NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    workload_ratio NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_workload_dept_year ON academic_workload_analytics(department_id, academic_year);
CREATE INDEX IF NOT EXISTS idx_workload_supervisor ON academic_workload_analytics(supervisor_id, academic_year);
CREATE INDEX IF NOT EXISTS idx_workload_contingent ON academic_workload_analytics(contingent_type, academic_year);
