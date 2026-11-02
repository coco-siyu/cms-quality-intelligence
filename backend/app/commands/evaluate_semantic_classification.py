"""Run the checked-in semantic classification evaluation suite."""

import argparse
from pathlib import Path

from app.config import get_settings
from app.services.ai_semantic_classification import provider_from_settings
from app.services.semantic_evaluation import (
    evaluate_semantic_suite,
    load_evaluation_suite,
    render_semantic_evaluation_report,
    report_as_json,
)

DEFAULT_FIXTURES = (
    Path(__file__).resolve().parents[1] / "data" / "semantic_classification_eval_v1.json"
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate semantic labels and evidence-validation behavior."
    )
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    parser.add_argument("--provider", choices=("replay", "openai"), default="replay")
    parser.add_argument(
        "--confirm-live-model-call",
        action="store_true",
        help="Required with --provider openai because the run may incur API cost.",
    )
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    provider = None
    if args.provider == "openai":
        if not args.confirm_live_model_call:
            parser.error("--provider openai requires --confirm-live-model-call")
        provider = provider_from_settings(get_settings())

    suite, fixture_sha256 = load_evaluation_suite(args.fixtures)
    report = evaluate_semantic_suite(
        suite,
        fixture_sha256,
        provider=provider,
    )
    rendered = (
        render_semantic_evaluation_report(report)
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
