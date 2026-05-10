import argparse

from south_tyrol_weather.pipeline import run, run_excel


def main() -> None:
    parser = argparse.ArgumentParser(description="South Tyrol weather data pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    dl = sub.add_parser("download", help="Fetch recent data from the REST API")
    dl.add_argument("--full", action="store_true", help="Re-fetch full history")

    hist = sub.add_parser(
        "download-historical",
        help="Ingest historical Excel files from the provincial website",
    )
    hist.add_argument("--full", action="store_true", help="Re-ingest all rows (overwrite)")

    args = parser.parse_args()
    if args.command == "download":
        run(full=args.full)
    elif args.command == "download-historical":
        run_excel(full=args.full)
