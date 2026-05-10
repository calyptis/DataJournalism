import argparse

from south_tyrol_weather.pipeline import run


def main() -> None:
    parser = argparse.ArgumentParser(description="South Tyrol weather data pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    dl = sub.add_parser("download", help="Fetch weather data and store in DuckDB")
    dl.add_argument(
        "--full",
        action="store_true",
        help="Re-fetch full history instead of only new records",
    )

    args = parser.parse_args()
    if args.command == "download":
        run(full=args.full)
