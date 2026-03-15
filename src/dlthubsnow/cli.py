from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from dlthubsnow.config import DemoSettings
from dlthubsnow.pipeline import run_pipeline



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Load GitHub repository issues into Snowflake with dlt."
    )
    parser.add_argument(
        "--owner",
        help="GitHub repository owner. Defaults to DLTHUBSNOW_OWNER, GITHUB_OWNER, then dlt-hub.",
    )
    parser.add_argument(
        "--repo",
        help="GitHub repository name. Defaults to DLTHUBSNOW_REPO, GITHUB_REPO, then dlt.",
    )
    parser.add_argument(
        "--github-token",
        help="Optional GitHub token to increase API rate limits for public repos.",
    )
    parser.add_argument(
        "--github-api-base-url",
        help="Optional GitHub API base URL override.",
    )
    parser.add_argument(
        "--state",
        choices=("open", "closed", "all"),
        help="Issue state filter sent to the GitHub issues API.",
    )
    parser.add_argument(
        "--per-page",
        type=int,
        help="Page size for GitHub issue requests (1-100).",
    )
    parser.add_argument(
        "--initial-updated-at",
        help="Initial updated_at cursor value for the first run or a reset run.",
    )
    parser.add_argument(
        "--pipeline-name",
        help="dlt pipeline name used for local state and load packages.",
    )
    parser.add_argument(
        "--dataset-name",
        help="Snowflake schema/dataset name used by dlt.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Replace destination data instead of using the default incremental merge run.",
    )
    return parser



def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    settings = DemoSettings.from_env().with_overrides(
        owner=args.owner,
        repo=args.repo,
        github_token=args.github_token,
        github_api_base_url=args.github_api_base_url,
        state=args.state,
        per_page=args.per_page,
        initial_updated_at=args.initial_updated_at,
        pipeline_name=args.pipeline_name,
        dataset_name=args.dataset_name,
        full_refresh=True if args.refresh else None,
    )

    print(
        f"Loading issues for {settings.repo_full_name} into Snowflake dataset "
        f"{settings.dataset_name} via pipeline {settings.pipeline_name}."
    )
    load_info = run_pipeline(settings)
    print(load_info)
    if load_info.has_failed_jobs:
        print("dlt run reported failed jobs.", file=sys.stderr)
        return 1
    return 0
