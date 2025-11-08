"""Pydantic models for consumption data responses."""

from datetime import datetime

from pydantic import BaseModel, Field


class ConsumptionDataPoint(BaseModel):
    """Single consumption data point.

    Attributes
    ----------
    timestamp : datetime
        Time of the consumption reading
    consumption : float
        Consumption value
    """

    timestamp: datetime
    consumption: float


class ConsumptionResponse(BaseModel):
    """Response model for consumption data.

    Attributes
    ----------
    meter_no : str
        Meter number
    type : str
        Data type (hourly or daily)
    date : str
        Query date (YYYY-MM-DD or YYYY-MM for monthly)
    unit : str
        Unit of measurement (kWh or m³)
    data : list[ConsumptionDataPoint]
        List of consumption data points
    total_consumption : float
        Total consumption for the period
    total_cost : float | None
        Total cost in BND (if calculated)
    """

    meter_no: str = Field(..., description="Meter number")
    type: str = Field(..., description="Data type (hourly/daily)")
    date: str = Field(..., description="Query date")
    unit: str = Field(..., description="Unit of measurement")
    data: list[ConsumptionDataPoint] = Field(..., description="Consumption data points")
    total_consumption: float = Field(..., description="Total consumption")
    total_cost: float | None = Field(None, description="Total cost in BND")

    model_config = {
        "json_schema_extra": {
            "example": {
                "meter_no": "123456789",
                "type": "hourly",
                "date": "2025-11-08",
                "unit": "kWh",
                "data": [
                    {"timestamp": "2025-11-08T00:00:00+08:00", "consumption": 1.2},
                    {"timestamp": "2025-11-08T01:00:00+08:00", "consumption": 1.5},
                ],
                "total_consumption": 45.6,
                "total_cost": 2.50,
            }
        }
    }


class CostCalculationRequest(BaseModel):
    """Request for cost calculation.

    Attributes
    ----------
    consumptions : list[float]
        List of consumption values
    """

    consumptions: list[float] = Field(..., description="List of consumption values", min_length=1)


class CostCalculationResponse(BaseModel):
    """Response for cost calculation.

    Attributes
    ----------
    meter_type : str
        Meter type (Electricity/Water)
    consumption : float
        Total consumption
    unit : str
        Unit of measurement
    cost : float
        Total cost in BND
    breakdown : list[TierBreakdown] | None
        Cost breakdown by tariff tiers
    """

    meter_type: str
    consumption: float
    unit: str
    cost: float
    breakdown: list["TierBreakdown"] | None = None


class TierBreakdown(BaseModel):
    """Tariff tier breakdown.

    Attributes
    ----------
    tier : int
        Tier number
    range : str
        Consumption range for this tier
    rate : float
        Rate per unit in BND
    consumption : float
        Consumption in this tier
    cost : float
        Cost for this tier
    """

    tier: int
    range: str
    rate: float
    consumption: float
    cost: float


class EarliestDateResponse(BaseModel):
    """Response for earliest available date query.

    Attributes
    ----------
    meter_no : str
        Meter number
    earliest_date : datetime
        Earliest date with available data
    """

    meter_no: str
    earliest_date: datetime
