import argparse
import json
from pathlib import Path

from api_log_explorer.analyze import markdown_report, read_requests, summarize


def main():
    parser = argparse.ArgumentParser(
        description="Summarize a sanitized API-log CSV offline"
    )
    parser.add_argument("--input", type=Path, default=Path("data/sample_requests.csv"))
    parser.add_argument("--output", type=Path, default=Path("output"))
    args = parser.parse_args()
    if args.input.resolve() in {
        (args.output / name).resolve() for name in ["summary.json", "report.md"]
    }:
        parser.error("output must not overwrite the input file")
    try:
        result = summarize(read_requests(args.input))
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "summary.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        (args.output / "report.md").write_text(
            markdown_report(result), encoding="utf-8"
        )
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Analysis failed: {exc}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
