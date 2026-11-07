"""Run the checked-in impact-explanation safety evaluation."""

import argparse
from pathlib import Path

from app.services.impact_evaluation import (
    evaluate_impact_suite,
    load_impact_evaluation_suite,
    render_impact_evaluation_report,
    report_as_json,
)

DEFAULT_FIXTURES = Path(__file__).resolve().parents[1] / "data" / "impact_explanation_eval_v1.json"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Replay fictional impact outputs through schema and citation safeguards."
    )
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    suite, fixture_sha256 = load_impact_evaluation_suite(args.fixtures)
    report = evaluate_impact_suite(suite, fixture_sha256)
    rendered = (
        render_impact_evaluation_report(report)
        if args.format == "markdown"
        else report_as_json(report)
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
