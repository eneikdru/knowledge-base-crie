import pytest
from pydantic import ValidationError
from backend.app.schemas.workload import WorkloadInput, WorkloadCalculationResult, WorkloadStatus
from backend.app.services.workload import calculate_workload


def test_valid_workload_calculation_exact():
    inp = WorkloadInput(
        lectures=200.0,
        seminars=300.0,
        practice=200.0,
        supervision=100.0,
        gek=50.0,
        departmental_norm=850.0
    )
    res = calculate_workload(inp)
    assert res.total_hours == 850.0
    assert res.fte_rate == 1.0
    assert res.status == WorkloadStatus.NORMAL
    assert res.warning_message is None


def test_overload_calculation():
    inp = WorkloadInput(
        lectures=300.0,
        seminars=350.0,
        practice=200.0,
        supervision=100.0,
        gek=50.0,
        departmental_norm=800.0
    )
    res = calculate_workload(inp)
    assert res.total_hours == 1000.0
    assert res.fte_rate == 1.25
    assert res.status == WorkloadStatus.OVERLOAD
    assert "Превышение нормы" in res.warning_message


def test_underload_calculation():
    inp = WorkloadInput(
        lectures=100.0,
        seminars=150.0,
        practice=100.0,
        supervision=50.0,
        gek=0.0,
        departmental_norm=800.0
    )
    res = calculate_workload(inp)
    assert res.total_hours == 400.0
    assert res.fte_rate == 0.5
    assert res.status == WorkloadStatus.UNDERLOAD
    assert "Недогрузка" in res.warning_message


def test_negative_hours_validation_error():
    with pytest.raises(ValidationError) as exc_info:
        WorkloadInput(
            lectures=-10.0,
            seminars=100.0,
            practice=50.0,
            supervision=20.0,
            gek=10.0,
            departmental_norm=800.0
        )
    errors = exc_info.value.errors()
    assert any(err["loc"] == ("lectures",) for err in errors)


def test_invalid_departmental_norm_range():
    with pytest.raises(ValidationError) as exc_info_low:
        WorkloadInput(
            lectures=100.0,
            seminars=100.0,
            practice=50.0,
            supervision=20.0,
            gek=10.0,
            departmental_norm=700.0
        )
    assert "departmental_norm must be between 750.0 and 900.0" in str(exc_info_low.value)

    with pytest.raises(ValidationError) as exc_info_high:
        WorkloadInput(
            lectures=100.0,
            seminars=100.0,
            practice=50.0,
            supervision=20.0,
            gek=10.0,
            departmental_norm=950.0
        )
    assert "departmental_norm must be between 750.0 and 900.0" in str(exc_info_high.value)
