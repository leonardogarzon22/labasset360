from pydantic import BaseModel
from datetime import date

class EquipmentTypeCreate(BaseModel):
    name: str
    impact_technical: int
    impact_normative: int
    impact_operational: int
    impact_safety: int
    requires_calibration: bool = True
    maintenance_months_high: int = 3
    maintenance_months_medium: int = 6
    calibration_months_high: int = 6
    calibration_months_medium: int = 12


class EquipmentCreate(BaseModel):
    code: str
    equipment_type_id: int
    brand: str | None = None
    model: str | None = None
    serial: str | None = None
    location: str | None = None
    usage_level: str
    last_maintenance: date | None = None
    last_calibration: date | None = None
