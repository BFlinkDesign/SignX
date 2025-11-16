from __future__ import annotations


def schedule_for(dia_in: float, depth_in: float) -> str:
    if dia_in >= 36.0 or depth_in >= 72.0:
        return "SCH-36-72-#5@12"
    if dia_in >= 24.0 or depth_in >= 48.0:
        return "SCH-24-48-#4@12"
    return "SCH-18-36-#4@18"


