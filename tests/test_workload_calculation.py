import pytest
from pydantic import ValidationError

from crie.workload.schemas import (
    TeachingWorkloadInput,
    WorkloadCalculationResult,
    WorkloadStatus,
    calculate_workload,
)


def test_teaching_workload_exact_norm():
    # Default norm is 850.0
    workload_input = TeachingWorkloadInput(
        lectures=250.0,
        seminars=300.0,
        practice=150.0,
        supervision=100.0,
        gek=50.0,
        departmental_norm=850.0,
    )
    result = calculate_workload(workload_input)
    assert result.total_hours == 850.0
    assert result.fte_rate == 1.0
    assert result.status == WorkloadStatus.NORMAL
    assert "точно соответствует" in result.status_message


def test_teaching_workload_overload():
    workload_input = TeachingWorkloadInput(
        lectures=300.0,
        seminars=300.0,
        practice=200.0,
        supervision=100.0,
        gek=100.0,
        departmental_norm=800.0,
    )
    result = calculate_workload(workload_input)
    assert result.total_hours == 1000.0
    assert result.fte_rate == 1.25
    assert result.status == WorkloadStatus.OVERLOAD
    assert "Перегрузка" in result.status_message


def test_teaching_workload_underload():
    workload_input = TeachingWorkloadInput(
        lectures=100.0,
        seminars=150.0,
        practice=100.0,
        supervision=50.0,
        gek=0.0,
        departmental_norm=800.0,
    )
    result = calculate_workload(workload_input)
    assert result.total_hours == 400.0
    assert result.fte_rate == 0.5
    assert result.status == WorkloadStatus.UNDERLOAD
    assert "Недогрузка" in result.status_message


def test_teaching_workload_floating_precision():
    workload_input = TeachingWorkloadInput(
        lectures=123.5,
        seminars=211.25,
        practice=98.75,
        supervision=45.0,
        gek=21.5,
        departmental_norm=750.0,
    )
    result = calculate_workload(workload_input)
    assert result.total_hours == 500.0
    assert result.fte_rate == round(500.0 / 750.0, 4)
    assert result.status == WorkloadStatus.UNDERLOAD


def test_validation_negative_hours():
    with pytest.raises(ValidationError) as excinfo:
        TeachingWorkloadInput(lectures=-10.0)
    errors = excinfo.value.errors()
    assert any(err["loc"] == ("lectures",) for err in errors)


def test_validation_departmental_norm_out_of_bounds():
    with pytest.raises(ValidationError) as excinfo_low:
        TeachingWorkloadInput(departmental_norm=700.0)
    assert "Departmental norm must be between 750.0 and 900.0" in str(excinfo_low.value)

    with pytest.raises(ValidationError) as excinfo_high:
        TeachingWorkloadInput(departmental_norm=950.0)
    assert "Departmental norm must be between 750.0 and 900.0" in str(excinfo_high.value)
