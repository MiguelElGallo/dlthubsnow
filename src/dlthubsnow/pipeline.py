from __future__ import annotations

import dlt

from dlthubsnow.config import DemoSettings
from dlthubsnow.github_issues import (
    RESOURCE_CURSOR_FIELD,
    github_issues_resource,
)



def build_pipeline(settings: DemoSettings) -> dlt.Pipeline:
    return dlt.pipeline(
        pipeline_name=settings.pipeline_name,
        destination="snowflake",
        dataset_name=settings.dataset_name,
        progress="log",
    )



def run_pipeline(settings: DemoSettings):
    pipeline = build_pipeline(settings)
    resource = github_issues_resource(
        owner=settings.owner,
        repo=settings.repo,
        token=settings.github_token,
        base_url=settings.github_api_base_url,
        per_page=settings.per_page,
        state=settings.state,
        updated_at=dlt.sources.incremental(
            RESOURCE_CURSOR_FIELD,
            initial_value=settings.initial_updated_at,
            row_order="asc",
        ),
    )
    run_kwargs = {"write_disposition": "replace"} if settings.full_refresh else {}
    return pipeline.run(resource, **run_kwargs)
