import argparse
import logging
import sys

from core.runner import PipelineRunner
from reports import REGISTRY, get_generator

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Unified report pipeline — runs any registered report type end-to-end.",
    )
    parser.add_argument(
        "--report-type",
        required=True,
        help=f"Report type to run. Available: {list(REGISTRY.keys())}",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Run download + analyze + render without sending email or uploading to Drive.",
    )
    parser.add_argument(
        "--test-email",
        default=None,
        metavar="ADDRESS",
        help="Redirect all outgoing email to this address (Drive upload suppressed).",
    )
    args = parser.parse_args()

    logger.info(
        f"Starting pipeline: report_type={args.report_type} "
        f"dry_run={args.dry_run} test_email={args.test_email}"
    )

    # Validate report type early — get_generator raises KeyError if unknown.
    # Must happen before PipelineRunner construction so the descriptive
    # error message below is reachable. (get_generator is called inside
    # runner.run(), not in PipelineRunner.__init__.)
    try:
        get_generator(args.report_type)
    except KeyError:
        logger.error(
            f"Unknown report type '{args.report_type}'. "
            f"Available types: {list(REGISTRY.keys())}"
        )
        sys.exit(1)

    runner = PipelineRunner(
        report_type=args.report_type,
        dry_run=args.dry_run,
        test_email=args.test_email,
    )

    try:
        result = runner.run()
    except Exception as exc:
        logger.exception(f"Pipeline crashed: {exc}")
        sys.exit(1)

    logger.info(f"Pipeline complete: {result}")
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
