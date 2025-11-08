"""Pydantic models for account responses."""

from datetime import datetime

from pydantic import BaseModel, Field

from usms.api.models.meter import MeterResponse


class AccountResponse(BaseModel):
    """Response model for account information.

    Attributes
    ----------
    reg_no : str
        Registration/IC number
    name : str
        Account holder name
    last_refresh : datetime | None
        Last time account data was refreshed
    meters : list[MeterResponse]
        List of meters associated with the account
    """

    reg_no: str = Field(..., description="Registration/IC number")
    name: str = Field(..., description="Account holder name")
    last_refresh: datetime | None = Field(
        None, description="Last refresh timestamp"
    )
    meters: list[MeterResponse] = Field(
        default_factory=list, description="List of associated meters"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "reg_no": "00-123456",
                "name": "John Doe",
                "last_refresh": "2025-11-08T14:30:00+08:00",
                "meters": [
                    {
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
                ],
            }
        }
    }


class RefreshResponse(BaseModel):
    """Response for account refresh operation.

    Attributes
    ----------
    success : bool
        Whether refresh was successful
    new_data : bool
        Whether new data was found
    last_refresh : datetime
        Timestamp of the refresh
    """

    success: bool
    new_data: bool
    last_refresh: datetime


class UpdateStatusResponse(BaseModel):
    """Response for update status check.

    Attributes
    ----------
    update_due : bool
        Whether an update is recommended
    last_update : datetime | None
        Last update timestamp
    next_recommended_update : datetime | None
        When next update is recommended
    """

    update_due: bool
    last_update: datetime | None = None
    next_recommended_update: datetime | None = None
