"""Account management routes."""

from fastapi import APIRouter, HTTPException, status

from usms.api.dependencies import CacheService, CurrentAccount
from usms.api.models.account import (
    AccountResponse,
    RefreshResponse,
    UpdateStatusResponse,
)
from usms.api.models.meter import MeterResponse

router = APIRouter(prefix="/account", tags=["Account"])


@router.get("", response_model=AccountResponse)
async def get_account(account: CurrentAccount, cache: CacheService) -> AccountResponse:
    """Get account information.

    Returns the authenticated user's account details including
    registration number, name, and list of all associated meters.

    Parameters
    ----------
    account : BaseUSMSAccount
        Authenticated account from JWT token

    Returns
    -------
    AccountResponse
        Account information with meters list

    Examples
    --------
    ```bash
    curl -X GET "http://localhost:8000/account" \\
        -H "Authorization: Bearer YOUR_TOKEN"
    ```
    """
    # Check cache
    cache_key = f"account:{account.reg_no}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    # Convert meters to response models
    meters = [
        MeterResponse(
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
        for meter in account.meters
    ]

    response = AccountResponse(
        reg_no=account.reg_no,
        name=account.name,
        last_refresh=account.last_refresh,
        meters=meters,
    )

    # Cache for 15 min (L1) and 1 hour (L2)
    cache.set(cache_key, response, ttl_memory=900, ttl_disk=3600)

    return response


@router.get("/meters", response_model=list[MeterResponse])
async def list_meters(account: CurrentAccount) -> list[MeterResponse]:
    """List all meters associated with the account.

    Equivalent to `usms --list` CLI command.

    Parameters
    ----------
    account : BaseUSMSAccount
        Authenticated account from JWT token

    Returns
    -------
    list[MeterResponse]
        List of all meters with detailed information

    Examples
    --------
    ```bash
    curl -X GET "http://localhost:8000/account/meters" \\
        -H "Authorization: Bearer YOUR_TOKEN"
    ```
    """
    return [
        MeterResponse(
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
        for meter in account.meters
    ]


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_account(account: CurrentAccount, cache: CacheService) -> RefreshResponse:
    """Force refresh account data from USMS platform.

    Fetches the latest data for all meters and updates the account.

    Parameters
    ----------
    account : BaseUSMSAccount
        Authenticated account from JWT token
    cache : CacheService
        Cache service for invalidation

    Returns
    -------
    RefreshResponse
        Refresh operation result

    Examples
    --------
    ```bash
    curl -X POST "http://localhost:8000/account/refresh" \\
        -H "Authorization: Bearer YOUR_TOKEN"
    ```
    """
    new_data = await account.refresh_data()

    # Invalidate account and meter caches
    cache.invalidate(exact_key=f"account:{account.reg_no}")
    for meter in account.meters:
        cache.invalidate(pattern=f"meter:{meter.no}:*")

    return RefreshResponse(
        success=True, new_data=new_data, last_refresh=account.last_refresh
    )


@router.get("/status", response_model=UpdateStatusResponse)
async def check_update_status(account: CurrentAccount) -> UpdateStatusResponse:
    """Check if account data update is recommended.

    Checks if enough time has passed since last update based on
    configured update intervals.

    Parameters
    ----------
    account : BaseUSMSAccount
        Authenticated account from JWT token

    Returns
    -------
    UpdateStatusResponse
        Update status information

    Examples
    --------
    ```bash
    curl -X GET "http://localhost:8000/account/status" \\
        -H "Authorization: Bearer YOUR_TOKEN"
    ```
    """
    update_due = account.is_update_due()
    last_update = account.get_latest_update() if account.meters else None

    # Calculate next recommended update (15 min from last update)
    next_update = None
    if last_update:
        from datetime import timedelta

        next_update = last_update + timedelta(minutes=15)

    return UpdateStatusResponse(
        update_due=update_due,
        last_update=last_update,
        next_recommended_update=next_update,
    )
