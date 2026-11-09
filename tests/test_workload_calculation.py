import random
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

from crie_assistant_api import app
from crie.workload.schemas import (
    TeachingWorkloadInput,
    WorkloadCalculationResult,
    WorkloadStatus,
    calculate_workload,
)


# --- Unit Tests: Formula Logic & Boundary Norms ---

def test_teaching_workload_exact_norm():
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
    assert result.is_overload is False
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
    assert result.is_overload is True
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
    assert result.is_overload is False
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
    assert result.is_overload is False


@pytest.mark.parametrize("norm", [750.0, 850.0, 900.0])
def test_workload_boundary_norms_exact_match(norm):
    """Given unit tests for the workload formula engine across boundary norms (750h, 850h, 900h),"""
    workload_input = TeachingWorkloadInput(
        lectures=norm * 0.4,
        seminars=norm * 0.3,
        practice=norm * 0.2,
        supervision=norm * 0.1,
        gek=0.0,
        departmental_norm=norm,
    )
    result = calculate_workload(workload_input)
    assert result.total_hours == pytest.approx(norm, rel=1e-5)
    assert result.fte_rate == 1.0
    assert result.status == WorkloadStatus.NORMAL
    assert result.is_overload is False


@pytest.mark.parametrize("norm", [750.0, 850.0, 900.0])
def test_workload_boundary_norms_overload_flag(norm):
    # 950 hours total is beyond ceiling (900.0)
    workload_input = TeachingWorkloadInput(
        lectures=300.0,
        seminars=300.0,
        practice=200.0,
        supervision=100.0,
        gek=50.0,
        departmental_norm=norm,
    )
    result = calculate_workload(workload_input)
    assert result.total_hours == 950.0
    expected_fte = round(950.0 / norm, 4)
    assert result.fte_rate == pytest.approx(expected_fte, rel=1e-5)
    assert result.is_overload is True
    assert result.status == WorkloadStatus.OVERLOAD


def test_workload_deterministic_random_vectors():
    """Verify workload calculation against deterministic pseudo-random load vectors using fixed seed."""
    rng = random.Random(42)
    for norm in (750.0, 850.0, 900.0):
        for _ in range(25):
            lectures = round(rng.uniform(0.0, 300.0), 2)
            seminars = round(rng.uniform(0.0, 300.0), 2)
            practice = round(rng.uniform(0.0, 300.0), 2)
            supervision = round(rng.uniform(0.0, 150.0), 2)
            gek = round(rng.uniform(0.0, 100.0), 2)

            inp = TeachingWorkloadInput(
                lectures=lectures,
                seminars=seminars,
                practice=practice,
                supervision=supervision,
                gek=gek,
                departmental_norm=norm,
            )
            res = calculate_workload(inp)
            expected_total = round(lectures + seminars + practice + supervision + gek, 2)
            assert res.total_hours == pytest.approx(expected_total, abs=0.01)
            expected_fte = round(expected_total / norm, 4)
            assert res.fte_rate == pytest.approx(expected_fte, abs=0.0001)
            expected_overload = expected_total > 900.0
            assert res.is_overload == expected_overload


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


# --- Integration Tests: /api/workload/calculate Endpoint ---

client = TestClient(app)


def test_api_calculate_workload_success():
    payload = {
        "lectures": 200.0,
        "seminars": 250.0,
        "practice": 250.0,
        "supervision": 100.0,
        "gek": 50.0,
        "departmental_norm": 850.0,
    }
    response = client.post("/api/workload/calculate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_hours"] == 850.0
    assert data["fte_rate"] == 1.0
    assert data["is_overload"] is False
    assert data["status"] == "NORMAL"


def test_api_calculate_workload_overload_boundary():
    payload = {
        "lectures": 300.0,
        "seminars": 300.0,
        "practice": 200.0,
        "supervision": 100.0,
        "gek": 50.0,
        "departmental_norm": 800.0,
    }
    response = client.post("/api/workload/calculate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_hours"] == 950.0
    assert data["is_overload"] is True
    assert data["status"] == "OVERLOAD"
    assert data["excess_hours"] == 50.0


def test_api_calculate_workload_invalid_norm_returns_422():
    payload = {
        "lectures": 200.0,
        "seminars": 200.0,
        "practice": 200.0,
        "supervision": 100.0,
        "gek": 50.0,
        "departmental_norm": 950.0,  # invalid norm > 900.0
    }
    response = client.post("/api/workload/calculate", json=payload)
    assert response.status_code == 422
    detail = response.json().get("detail", [])
    assert any("departmental_norm" in str(item) for item in detail)


def test_api_calculate_workload_negative_hours_returns_422():
    payload = {
        "lectures": -50.0,
        "seminars": 200.0,
        "practice": 200.0,
        "supervision": 100.0,
        "gek": 50.0,
        "departmental_norm": 800.0,
    }
    response = client.post("/api/workload/calculate", json=payload)
    assert response.status_code == 422


def test_api_calculate_workload_empty_payload_returns_422():
    response = client.post("/api/workload/calculate", json={})
    assert response.status_code == 422
