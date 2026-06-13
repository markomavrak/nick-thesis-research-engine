import argparse
from pathlib import Path
from typing import Optional, Sequence

from .analyzer import analyze_thesis
from .providers import FixtureResearchProvider
from .reporting import write_reports


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate an evidence-backed watchlist from an investment thesis."
    )
    parser.add_argument("--thesis", required=True, help="Investment thesis to research.")
    parser.add_argument(
        "--max-market-cap-b",
        type=float,
        default=None,
        help="Optional approximate seed market-cap ceiling in billions of dollars.",
    )
    parser.add_argument(
        "--sector",
        action="append",
        default=[],
        help="Optional sector or theme hint. Repeat for multiple hints.",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory for JSON and Markdown reports. Default: output",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    arguments = build_parser().parse_args(argv)
    provider = FixtureResearchProvider()
    report = analyze_thesis(
        arguments.thesis,
        provider.companies(),
        provider.rotation_signals(),
        max_market_cap_b=arguments.max_market_cap_b,
        sector_hints=arguments.sector,
    )
    json_path, markdown_path = write_reports(report, Path(arguments.output_dir))
    print(f"Generated Aurex watchlist from seed snapshot {provider.as_of()}.")
    print(f"Candidates: {', '.join(item.company.ticker for item in report.candidates) or 'none'}")
    print(f"JSON: {json_path}")
    print(f"Markdown: {markdown_path}")
    print("Seed snapshot only: verify live market data and sector rotation before acting.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
