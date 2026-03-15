from __future__ import annotations

from dataclasses import dataclass, replace
import os
from typing import Optional

DEFAULT_OWNER = "dlt-hub"
DEFAULT_REPO = "dlt"
DEFAULT_STATE = "all"
DEFAULT_PER_PAGE = 100
DEFAULT_INITIAL_UPDATED_AT = "1970-01-01T00:00:00Z"
DEFAULT_PIPELINE_NAME = "dlthubsnow"
DEFAULT_DATASET_NAME = "github_issues_demo"
DEFAULT_GITHUB_API_BASE_URL = "https://api.github.com"


def _read_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return int(raw_value)


def _read_bool_env(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class DemoSettings:
    owner: str = DEFAULT_OWNER
    repo: str = DEFAULT_REPO
    github_token: Optional[str] = None
    github_api_base_url: str = DEFAULT_GITHUB_API_BASE_URL
    state: str = DEFAULT_STATE
    per_page: int = DEFAULT_PER_PAGE
    initial_updated_at: str = DEFAULT_INITIAL_UPDATED_AT
    pipeline_name: str = DEFAULT_PIPELINE_NAME
    dataset_name: str = DEFAULT_DATASET_NAME
    full_refresh: bool = False

    @property
    def repo_full_name(self) -> str:
        return f"{self.owner}/{self.repo}"

    @classmethod
    def from_env(cls) -> "DemoSettings":
        return cls(
            owner=os.getenv("DLTHUBSNOW_OWNER", os.getenv("GITHUB_OWNER", DEFAULT_OWNER)),
            repo=os.getenv("DLTHUBSNOW_REPO", os.getenv("GITHUB_REPO", DEFAULT_REPO)),
            github_token=os.getenv("DLTHUBSNOW_GITHUB_TOKEN", os.getenv("GITHUB_TOKEN")),
            github_api_base_url=os.getenv(
                "DLTHUBSNOW_GITHUB_API_BASE_URL", DEFAULT_GITHUB_API_BASE_URL
            ),
            state=os.getenv("DLTHUBSNOW_STATE", DEFAULT_STATE),
            per_page=_read_int_env("DLTHUBSNOW_PER_PAGE", DEFAULT_PER_PAGE),
            initial_updated_at=os.getenv(
                "DLTHUBSNOW_INITIAL_UPDATED_AT", DEFAULT_INITIAL_UPDATED_AT
            ),
            pipeline_name=os.getenv(
                "DLTHUBSNOW_PIPELINE_NAME", DEFAULT_PIPELINE_NAME
            ),
            dataset_name=os.getenv("DLTHUBSNOW_DATASET_NAME", DEFAULT_DATASET_NAME),
            full_refresh=_read_bool_env("DLTHUBSNOW_FULL_REFRESH"),
        )

    def with_overrides(self, **changes: object) -> "DemoSettings":
        return replace(
            self,
            **{key: value for key, value in changes.items() if value is not None},
        )
