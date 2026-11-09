from enum import Enum
from pydantic import BaseModel, Field, field_validator


class WorkloadStatus(str, Enum):
    UNDERLOAD = "UNDERLOAD"
    NORMAL = "NORMAL"
    OVERLOAD = "OVERLOAD"


class TeachingWorkloadInput(BaseModel):
    lectures: float = Field(
        default=0.0,
        ge=0.0,
        description="Lecture hours (academic hours, must be >= 0)",
    )
    seminars: float = Field(
        default=0.0,
        ge=0.0,
        description="Seminar/workshop hours (academic hours, must be >= 0)",
    )
    practice: float = Field(
        default=0.0,
        ge=0.0,
        description="Practical training hours (academic hours, must be >= 0)",
    )
    supervision: float = Field(
        default=0.0,
        ge=0.0,
        description="Postgraduate student guidance/supervision hours (must be >= 0)",
    )
    gek: float = Field(
        default=0.0,
        ge=0.0,
        description="State Examination Commission (ГЭК) work hours (must be >= 0)",
    )
    departmental_norm: float = Field(
        default=850.0,
        description="Annual departmental standard workload norm in hours (750.0 - 900.0)",
    )

    @field_validator("departmental_norm")
    @classmethod
    def validate_departmental_norm(cls, v: float) -> float:
        if v < 750.0 or v > 900.0:
            raise ValueError(
                f"Departmental norm must be between 750.0 and 900.0 hours per year, got {v}"
            )
        return v


class WorkloadCalculationResult(BaseModel):
    total_hours: float = Field(..., description="Total aggregated teaching hours")
    departmental_norm: float = Field(..., description="Departmental norm used for calculation")
    fte_rate: float = Field(..., description="Calculated FTE fraction (e.g., 1.0 = full stake)")
    status: WorkloadStatus = Field(..., description="Workload balance status (UNDERLOAD, NORMAL, OVERLOAD)")
    is_overload: bool = Field(default=False, description="True if total_hours > departmental_norm")
    status_message: str = Field(..., description="Human-readable explanatory summary")


def calculate_workload(input_data: TeachingWorkloadInput) -> WorkloadCalculationResult:
    total_hours = round(
        input_data.lectures
        + input_data.seminars
        + input_data.practice
        + input_data.supervision
        + input_data.gek,
        4,
    )

    fte_rate = round(total_hours / input_data.departmental_norm, 4)

    # In Russian higher education and CRIE regulations:
    # A stake is considered underloaded when fte < 1.0 (or below standard hours),
    # normal when fte == 1.0 (or within 1.0 equivalent load), and overloaded when fte > 1.0 (or > norm).
    if total_hours < input_data.departmental_norm:
        status = WorkloadStatus.UNDERLOAD
        status_message = (
            f"Недогрузка: текущая нагрузка ({total_hours:.1f} ч) ниже нормы "
            f"({input_data.departmental_norm:.1f} ч). Доля ставки: {fte_rate:.2f}."
        )
    elif total_hours > input_data.departmental_norm:
        status = WorkloadStatus.OVERLOAD
        status_message = (
            f"Перегрузка: текущая нагрузка ({total_hours:.1f} ч) превышает норму "
            f"({input_data.departmental_norm:.1f} ч). Доля ставки: {fte_rate:.2f}."
        )
    else:
        status = WorkloadStatus.NORMAL
        status_message = (
            f"Норма: нагрузка точно соответствует годовой норме кафедральной ставки "
            f"({input_data.departmental_norm:.1f} ч). Доля ставки: {fte_rate:.2f}."
        )

    is_overload = total_hours > input_data.departmental_norm

    return WorkloadCalculationResult(
        total_hours=total_hours,
        departmental_norm=input_data.departmental_norm,
        fte_rate=fte_rate,
        status=status,
        is_overload=is_overload,
        status_message=status_message,
    )
