from backend.app.schemas.workload import WorkloadInput, WorkloadCalculationResult, WorkloadStatus


def calculate_workload(workload_data: WorkloadInput) -> WorkloadCalculationResult:
    """
    Calculate total workload hours, FTE rate, and overload/underload status.
    Norm is guaranteed to be between 750 and 900 by WorkloadInput validation.
    """
    total_hours = (
        workload_data.lectures +
        workload_data.seminars +
        workload_data.practice +
        workload_data.supervision +
        workload_data.gek
    )
    
    # FTE fraction rounded to 4 decimal places
    fte_rate = round(total_hours / workload_data.departmental_norm, 4)
    
    # Status threshold:
    # FTE > 1.05 or total_hours > norm is overload
    # FTE < 0.95 or total_hours < norm is underload
    # Exact 1.0 (or within [0.95, 1.05]) is considered normal
    if total_hours > workload_data.departmental_norm:
        status = WorkloadStatus.OVERLOAD
        warning_message = f"Превышение нормы кафедральной нагрузки на {round(total_hours - workload_data.departmental_norm, 2)} ч. (Ставка: {fte_rate})"
    elif total_hours < workload_data.departmental_norm:
        status = WorkloadStatus.UNDERLOAD
        warning_message = f"Недогрузка относительно нормы кафедры на {round(workload_data.departmental_norm - total_hours, 2)} ч. (Ставка: {fte_rate})"
    else:
        status = WorkloadStatus.NORMAL
        warning_message = None

    return WorkloadCalculationResult(
        total_hours=round(total_hours, 2),
        departmental_norm=workload_data.departmental_norm,
        fte_rate=fte_rate,
        status=status,
        warning_message=warning_message
    )
