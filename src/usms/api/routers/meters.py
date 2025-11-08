"""Meter information and consumption data routes."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status

from usms.api.dependencies import CurrentAccount
from usms.api.models.consumption import (
    ConsumptionDataPoint,
    ConsumptionResponse,
    CostCalculationRequest,
    CostCalculationResponse,
    EarliestDateResponse,
)
from usms.api.models.meter import (
    MeterCreditResponse,
    MeterResponse,
    MeterStatusResponse,
    MeterUnitResponse,
)
from usms.exceptions.errors import USMSMeterNumberError

router = APIRouter(prefix="/meters", tags=["Meters"])


@router.get("/{meter_no}", response_model=MeterResponse)
async def get_meter(meter_no: str, account: CurrentAccount) -> MeterResponse:
    """Get detailed information for a specific meter.

    Parameters
    ----------
    meter_no : str
        Meter number
    account : BaseUSMSAccount
        Authenticated account

    Returns
    -------
    MeterResponse
        Detailed meter information

    Raises
    ------
    HTTPException
        404 if meter not found
    """
    try:
        meter = account.get_meter(meter_no)
    except USMSMeterNumberError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meter {meter_no} not found",
        ) from e

    return MeterResponse(
        no=meter.no,
        id=meter.id,
        type=meter.type,
        unit=meter.unit,
        remaining_unit=meter.remaining_unit,
        remaining_credit=meter.remaining_credit,
        last_update=meter.last_update,
        status=meter.status,
        is_active=meter.is_active,
        address=meter.address,
        kampong=meter.kampong,
        mukim=meter.mukim,
        district=meter.district,
        postcode=meter.postcode,
    )


@router.get("/{meter_no}/unit", response_model=MeterUnitResponse)
async def get_meter_unit(meter_no: str, account: CurrentAccount) -> MeterUnitResponse:
    """Get remaining units for a meter.

    Equivalent to `usms -m {meter_no} --unit` CLI command.

    Parameters
    ----------
    meter_no : str
        Meter number
    account : BaseUSMSAccount
        Authenticated account

    Returns
    -------
    MeterUnitResponse
        Remaining units information
    """
    try:
        meter = account.get_meter(meter_no)
    except USMSMeterNumberError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meter {meter_no} not found",
        ) from e

    return MeterUnitResponse(
        meter_no=meter.no,
        remaining_unit=meter.remaining_unit,
        unit=meter.unit,
        last_update=meter.last_update,
    )


@router.get("/{meter_no}/credit", response_model=MeterCreditResponse)
async def get_meter_credit(meter_no: str, account: CurrentAccount) -> MeterCreditResponse:
    """Get remaining credit for a meter.

    Equivalent to `usms -m {meter_no} --credit` CLI command.

    Parameters
    ----------
    meter_no : str
        Meter number
    account : BaseUSMSAccount
        Authenticated account

    Returns
    -------
    MeterCreditResponse
        Remaining credit information
    """
    try:
        meter = account.get_meter(meter_no)
    except USMSMeterNumberError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meter {meter_no} not found",
        ) from e

    return MeterCreditResponse(
        meter_no=meter.no,
        remaining_credit=meter.remaining_credit,
        currency="BND",
        last_update=meter.last_update,
    )


@router.get("/{meter_no}/status", response_model=MeterStatusResponse)
async def get_meter_status(meter_no: str, account: CurrentAccount) -> MeterStatusResponse:
    """Get meter status.

    Parameters
    ----------
    meter_no : str
        Meter number
    account : BaseUSMSAccount
        Authenticated account

    Returns
    -------
    MeterStatusResponse
        Meter status information
    """
    try:
        meter = account.get_meter(meter_no)
    except USMSMeterNumberError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meter {meter_no} not found",
        ) from e

    return MeterStatusResponse(
        meter_no=meter.no,
        status=meter.status,
        is_active=meter.is_active,
        last_update=meter.last_update,
    )


@router.get("/{meter_no}/consumption/hourly", response_model=ConsumptionResponse)
async def get_hourly_consumption(
    meter_no: str,
    account: CurrentAccount,
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
) -> ConsumptionResponse:
    """Get hourly consumption data for a specific date.

    Parameters
    ----------
    meter_no : str
        Meter number
    account : BaseUSMSAccount
        Authenticated account
    date : str
        Date in YYYY-MM-DD format

    Returns
    -------
    ConsumptionResponse
        Hourly consumption data
    """
    try:
        meter = account.get_meter(meter_no)
    except USMSMeterNumberError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meter {meter_no} not found",
        ) from e

    # Parse date
    try:
        query_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD",
        ) from e

    # Fetch hourly data
    consumptions = await meter.get_hourly_consumptions(query_date)

    # Convert to response format
    data_points = [
        ConsumptionDataPoint(timestamp=ts, consumption=value)
        for ts, value in consumptions.items()
    ]

    total = meter.calculate_total_consumption(consumptions)
    cost = meter.calculate_total_cost(consumptions)

    return ConsumptionResponse(
        meter_no=meter.no,
        type="hourly",
        date=date,
        unit=meter.unit,
        data=data_points,
        total_consumption=total,
        total_cost=cost,
    )


@router.post("/{meter_no}/cost/calculate", response_model=CostCalculationResponse)
async def calculate_cost(
    meter_no: str,
    account: CurrentAccount,
    request: CostCalculationRequest,
) -> CostCalculationResponse:
    """Calculate cost for given consumption data.

    Parameters
    ----------
    meter_no : str
        Meter number
    account : BaseUSMSAccount
        Authenticated account
    request : CostCalculationRequest
        Consumption values

    Returns
    -------
    CostCalculationResponse
        Cost calculation result
    """
    try:
        meter = account.get_meter(meter_no)
    except USMSMeterNumberError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Meter {meter_no} not found",
        ) from e

    # Calculate total consumption
    import pandas as pd

    consumption_series = pd.Series(request.consumptions)
    total_consumption = meter.calculate_total_consumption(consumption_series)
    total_cost = meter.calculate_total_cost(consumption_series)

    return CostCalculationResponse(
        meter_type=meter.type,
        consumption=total_consumption,
        unit=meter.unit,
        cost=total_cost,
        breakdown=None,  # TODO: Implement tier breakdown
    )
