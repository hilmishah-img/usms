# ruff: noqa: C901, T201

"""
CLI module for USMS.

This module contains the CLI logic to interact with the USMS package, including
commands and options for users to interact with the system through the command line.
"""

import argparse
import asyncio
import os
import sys
from importlib.metadata import PackageNotFoundError, version

from usms import initialize_usms_account
from usms.exceptions.errors import USMSLoginError, USMSMeterNumberError
from usms.utils.logging_config import init_console_logging, logging

# get usms_version dynamically
try:
    usms_version = version("usms")
except PackageNotFoundError:
    usms_version = "unknown"


def run_cli() -> None:  # noqa: PLR0912
    """Run the command-line interface for USMS."""
    parser = argparse.ArgumentParser(description="USMS CLI")
    parser.add_argument("--version", action="version", version=f"USMS CLI v{usms_version}")

    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Serve command (API server)
    serve_parser = subparsers.add_parser("serve", help="Start API server")
    serve_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)",
    )
    serve_parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )
    serve_parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (default: 1)",
    )

    # Default command arguments (backwards compatibility - no subcommand needed)
    parser.add_argument(
        "-log",
        "--log-level",
        default="warning",
        help="Set log level (e.g., debug, info, warning, error)",
    )
    parser.add_argument(
        "-u",
        "--username",
        default=os.getenv("USMS_USERNAME"),
        help="USMS account username",
    )
    parser.add_argument(
        "-p",
        "--password",
        default=os.getenv("USMS_PASSWORD"),
        help="USMS account password",
    )

    # optional arguments
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Run in synchronous mode instead of the default async mode",
    )
    parser.add_argument("-l", "--list", action="store_true", help="List all available meters")
    parser.add_argument("-m", "--meter", help="Meter number to query")

    # meter data options
    data_group = parser.add_argument_group("Meter Data Options")
    data_group.add_argument("--unit", action="store_true", help="Show remaining unit")
    data_group.add_argument("--credit", action="store_true", help="Show remaining credit balance")

    args = parser.parse_args()

    # Handle serve command
    if args.command == "serve":
        from usms.api.server import run_server

        run_server(
            host=args.host,
            port=args.port,
            reload=args.reload,
            workers=args.workers,
        )
        return

    # check passed arguments
    if not getattr(logging, args.log_level.upper(), None):
        print(f"Invalid log level: {args.log_level}")
        sys.exit(1)
    init_console_logging(args.log_level.upper())

    if not args.username or not args.password:
        print("Username and password must be provided (via arguments or environment variables).")
        sys.exit(1)

    if not args.list and not args.meter:
        print("No meter option (--list, --meter) specified.")
        parser.print_help()
        sys.exit(0)

    if args.meter and not (args.unit or args.credit or args.consumption):
        print("No data option (--unit, --credit, --consumption) specified.")
        parser.print_help()
        sys.exit(0)

    try:
        if args.sync:
            account = initialize_usms_account(args.username, args.password)
        else:
            account = asyncio.run(
                initialize_usms_account(args.username, args.password, async_mode=True)
            )

        if args.list:
            print("Meters:")
            for meter in account.meters:
                print(f"- {meter.no} ({meter.type})")

        if args.meter:
            meter = account.get_meter(args.meter)
            if args.unit:
                print(f"Unit: {meter.remaining_unit} {meter.unit}")
            if args.credit:
                print(f"Credit: ${meter.remaining_credit}")
    except USMSLoginError as error:
        print(error)
        sys.exit(1)
    except USMSMeterNumberError as error:
        print(error)
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    run_cli()
