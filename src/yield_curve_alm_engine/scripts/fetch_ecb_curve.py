"""Fetch ECB yield-curve spot rates and write a normalized local CSV."""

from __future__ import annotations

import argparse

from yield_curve_alm_engine.data.ecb import fetch_ecb_curve, write_ecb_curve_csv


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch a normalized ECB spot yield curve CSV.")
    parser.add_argument(
        "--curve-type",
        choices=["aaa", "all"],
        default="aaa",
        help="ECB curve universe: aaa for AAA issuers, all for all ratings.",
    )
    parser.add_argument(
        "--date",
        default="latest",
        help="Use 'latest' or an exact YYYY-MM-DD observation date.",
    )
    parser.add_argument("--start", default=None, help="Optional start date YYYY-MM-DD.")
    parser.add_argument("--end", default=None, help="Optional end date YYYY-MM-DD.")
    parser.add_argument(
        "--output",
        required=True,
        help="Output CSV path, e.g. data/market_curves/ecb/ecb_aaa_spot_latest.csv.",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    curve = fetch_ecb_curve(
        curve_type=args.curve_type,
        date=args.date,
        start=args.start,
        end=args.end,
    )
    output_path = write_ecb_curve_csv(curve, args.output)

    curve_dates = ", ".join(sorted(curve["curve_date"].unique()))
    print(f"Fetched {len(curve)} ECB curve points for date(s): {curve_dates}")
    print(f"Saved normalized curve CSV to: {output_path}")


if __name__ == "__main__":
    main()
