"""Tariff information routes."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from usms.config.constants import ELECTRIC_TARIFF, WATER_TARIFF

router = APIRouter(prefix="/tariffs", tags=["Tariffs"])


class TariffTier(BaseModel):
    """Tariff tier information.

    Attributes
    ----------
    lower_bound : int
        Lower consumption bound
    upper_bound : int | str
        Upper consumption bound ("inf" for infinity)
    rate : float
        Rate per unit in BND
    """

    lower_bound: int
    upper_bound: int | str
    rate: float


class TariffResponse(BaseModel):
    """Tariff information response.

    Attributes
    ----------
    type : str
        Tariff type (Electricity or Water)
    unit : str
        Unit of measurement
    tiers : list[TariffTier]
        List of tariff tiers
    """

    type: str
    unit: str
    tiers: list[TariffTier]


@router.get("/electricity", response_model=TariffResponse)
async def get_electricity_tariff() -> TariffResponse:
    """Get electricity tariff tiers.

    Returns
    -------
    TariffResponse
        Electricity tariff information

    Examples
    --------
    ```bash
    curl -X GET "http://localhost:8000/tariffs/electricity"
    ```
    """
    tiers = [
        TariffTier(
            lower_bound=tier.lower_bound,
            upper_bound="inf" if tier.upper_bound == float("inf") else tier.upper_bound,
            rate=tier.rate,
        )
        for tier in ELECTRIC_TARIFF.tiers
    ]

    return TariffResponse(type="Electricity", unit="kWh", tiers=tiers)


@router.get("/water", response_model=TariffResponse)
async def get_water_tariff() -> TariffResponse:
    """Get water tariff tiers.

    Returns
    -------
    TariffResponse
        Water tariff information

    Examples
    --------
    ```bash
    curl -X GET "http://localhost:8000/tariffs/water"
    ```
    """
    tiers = [
        TariffTier(
            lower_bound=tier.lower_bound,
            upper_bound="inf" if tier.upper_bound == float("inf") else tier.upper_bound,
            rate=tier.rate,
        )
        for tier in WATER_TARIFF.tiers
    ]

    return TariffResponse(type="Water", unit="m³", tiers=tiers)
