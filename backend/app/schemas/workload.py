from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class WorkloadStatus(str, Enum):
    NORMAL = "NORMAL"
    OVERLOAD = "OVERLOAD"
    UNDERLOAD = "UNDERLOAD"


class WorkloadInput(BaseModel):
    lectures: float = Field(..., ge=0.0, description="Hours of lectures conducted (non-negative)")
    seminars: float = Field(..., ge=0.0, description="Hours of seminars conducted (non-negative)")
    practice: float = Field(..., ge=0.0, description="Hours of practical training / clinical practice (non-negative)")
    supervision: float = Field(..., ge=0.0, description="Hours of graduate/postgraduate supervision (non-negative)")
    gek: float = Field(..., ge=0.0, description="Hours of State Examination Board (GEK) participation (non-negative)")
    departmental_norm: float = Field(
        default=850.0,
        description="Annual departmental standard workload in hours, typically 750 to 900 hours"
    )

    @field_validator("departmental_norm")
    @classmethod
    def validate_departmental_norm(cls, v: float) -> float:
        if v < 750.0 or v > 900.0:
            raise ValueError("departmental_norm must be between 750.0 and 900.0 hours per year")
        return v


class WorkloadCalculationResult(BaseModel):
    total_hours: float = Field(..., ge=0.0, description="Sum of all pedagogical work hours")
    departmental_norm: float = Field(..., ge=750.0, le=900.0, description="Departmental norm used for calculation")
    fte_rate: float = Field(..., ge=0.0, description="Full-Time Equivalent (FTE) fraction, rounded to 4 decimal places")
    status: WorkloadStatus = Field(..., description="Workload status indicating normal load, overload, or underload")
    warning_message: Optional[str] = Field(None, description="Descriptive warning in case of overload or underload")
