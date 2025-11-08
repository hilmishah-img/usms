"""Pydantic models for meter responses."""

from datetime import datetime

from pydantic import BaseModel, Field


class MeterResponse(BaseModel):
    """Response model for meter information.

    Attributes
    ----------
    no : str
        Meter number
    id : str
        Base64-encoded meter number
    type : str
        Meter type (Electricity or Water)
    unit : str
        Unit of measurement (kWh or m³)
    remaining_unit : float
        Current remaining units
    remaining_credit : float
        Current remaining credit in BND
    last_update : datetime
        Last update by USMS system
    status : str
        Meter status (ACTIVE, etc.)
    is_active : bool
        Whether meter is active
    address : str
        Full address
    kampong : str
        Village
    mukim : str
        Sub-district
    district : str
        District
    postcode : str
        Postal code
    """

    no: str = Field(..., description="Meter number")
    id: str = Field(..., description="Base64-encoded meter number")
    type: str = Field(..., description="Meter type (Electricity/Water)")
    unit: str = Field(..., description="Unit of measurement (kWh/m³)")
    remaining_unit: float = Field(..., description="Remaining units")
    remaining_credit: float = Field(..., description="Remaining credit in BND")
    last_update: datetime = Field(..., description="Last update timestamp")
    status: str = Field(..., description="Meter status")
    is_active: bool = Field(..., description="Whether meter is active")
    address: str = Field(..., description="Full address")
    kampong: str = Field(..., description="Village")
    mukim: str = Field(..., description="Sub-district")
    district: str = Field(..., description="District")
    postcode: str = Field(..., description="Postal code")

    model_config = {
        "json_schema_extra": {
            "example": {
                "no": "123456789",
                "id": "MTIzNDU2Nzg5",
                "type": "Electricity",
                "unit": "kWh",
                "remaining_unit": 150.5,
                "remaining_credit": 10.50,
                "last_update": "2025-11-08T13:00:00+08:00",
                "status": "ACTIVE",
                "is_active": True,
                "address": "123 Main Street",
                "kampong": "Kg. Example",
                "mukim": "Mukim Example",
                "district": "Brunei-Muara",
                "postcode": "BA1234",
            }
        }
    }


class MeterUnitResponse(BaseModel):
    """Response for meter unit query.

    Attributes
    ----------
    meter_no : str
        Meter number
    remaining_unit : float
        Remaining units
    unit : str
        Unit of measurement
    last_update : datetime
        Last update timestamp
    """

    meter_no: str
    remaining_unit: float
    unit: str
    last_update: datetime


class MeterCreditResponse(BaseModel):
    """Response for meter credit query.

    Attributes
    ----------
    meter_no : str
        Meter number
    remaining_credit : float
        Remaining credit in BND
    currency : str
        Currency code (BND)
    last_update : datetime
        Last update timestamp
    """

    meter_no: str
    remaining_credit: float
    currency: str = "BND"
    last_update: datetime


class MeterStatusResponse(BaseModel):
    """Response for meter status query.

    Attributes
    ----------
    meter_no : str
        Meter number
    status : str
        Meter status
    is_active : bool
        Whether meter is active
    last_update : datetime
        Last update timestamp
    """

    meter_no: str
    status: str
    is_active: bool
    last_update: datetime
