from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Iterator, List, Optional
from urllib.parse import quote

import dlt
import requests

JSONDict = Dict[str, Any]

RESOURCE_NAME = "github_issues"
RESOURCE_CURSOR_FIELD = "updated_at"
RESOURCE_PRIMARY_KEY = "id"
RESOURCE_MERGE_KEY = "id"
RESOURCE_WRITE_DISPOSITION: Dict[str, str] = {"disposition": "merge", "strategy": "upsert"}
RESOURCE_COLUMNS: Dict[str, Dict[str, Any]] = {
    "created_at": {"data_type": "timestamp", "timezone": True},
    "updated_at": {"data_type": "timestamp", "timezone": True, "dedup_sort": "desc"},
    "closed_at": {"data_type": "timestamp", "timezone": True},
    "assignee_logins": {"data_type": "json"},
    "label_names": {"data_type": "json"},
}
DEFAULT_GITHUB_API_BASE_URL = "https://api.github.com"
DEFAULT_INITIAL_UPDATED_AT = "1970-01-01T00:00:00Z"
DEFAULT_PER_PAGE = 100
DEFAULT_STATE = "all"


class GitHubIssuesClient:
    def __init__(
        self,
        token: Optional[str] = None,
        *,
        base_url: str = DEFAULT_GITHUB_API_BASE_URL,
        timeout: int = 30,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "dlthubsnow-mvp",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if hasattr(self.session, "headers"):
            self.session.headers.update(headers)
            if token:
                self.session.headers["Authorization"] = f"Bearer {token}"

    def iter_issue_pages(
        self,
        *,
        owner: str,
        repo: str,
        since: Optional[str],
        per_page: int,
        state: str,
    ) -> Iterator[List[JSONDict]]:
        next_url = (
            f"{self.base_url}/repos/{quote(owner, safe='')}/{quote(repo, safe='')}/issues"
        )
        params: Optional[Dict[str, Any]] = build_issue_query_params(
            since=since,
            per_page=per_page,
            state=state,
        )

        while next_url:
            response = self.session.get(next_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list):
                raise ValueError("Expected GitHub issues endpoint to return a list")
            if not payload:
                return
            yield payload
            next_url = response.links.get("next", {}).get("url")
            params = None


def build_issue_query_params(*, since: Optional[str], per_page: int, state: str) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "state": state,
        "sort": "updated",
        "direction": "asc",
        "per_page": max(1, min(per_page, 100)),
    }
    if since:
        params["since"] = since
    return params



def is_pull_request_issue(issue: JSONDict) -> bool:
    return issue.get("pull_request") is not None



def shape_issue(issue: JSONDict, *, owner: str, repo: str) -> JSONDict:
    author = issue.get("user") or {}
    assignee = issue.get("assignee") or {}
    assignees = issue.get("assignees") or []
    labels = issue.get("labels") or []
    milestone = issue.get("milestone") or {}

    return {
        "id": issue["id"],
        "number": issue["number"],
        "title": issue.get("title"),
        "state": issue.get("state"),
        "state_reason": issue.get("state_reason"),
        "body": issue.get("body"),
        "html_url": issue.get("html_url"),
        "comments": issue.get("comments", 0),
        "locked": issue.get("locked", False),
        "author_login": author.get("login"),
        "author_type": author.get("type"),
        "assignee_login": assignee.get("login"),
        "assignee_logins": [
            candidate.get("login") for candidate in assignees if candidate.get("login")
        ],
        "label_names": [
            label.get("name") if isinstance(label, dict) else str(label)
            for label in labels
            if (label.get("name") if isinstance(label, dict) else str(label))
        ],
        "milestone_title": milestone.get("title"),
        "repository_owner": owner,
        "repository_name": repo,
        "created_at": issue.get("created_at"),
        "updated_at": issue.get("updated_at"),
        "closed_at": issue.get("closed_at"),
    }



def transform_issue_page(
    page: Iterable[JSONDict], *, owner: str, repo: str
) -> List[JSONDict]:
    return [
        shape_issue(issue, owner=owner, repo=repo)
        for issue in page
        if not is_pull_request_issue(issue)
    ]



def collapse_issue_snapshots(issues: Iterable[JSONDict]) -> List[JSONDict]:
    latest_by_id: Dict[int, JSONDict] = {}
    issue_order: List[int] = []

    for issue in issues:
        issue_id = issue["id"]
        existing = latest_by_id.get(issue_id)
        if existing is None:
            latest_by_id[issue_id] = issue
            issue_order.append(issue_id)
            continue
        if is_newer_issue_snapshot(issue, existing):
            latest_by_id[issue_id] = issue

    return [latest_by_id[issue_id] for issue_id in issue_order]



def is_newer_issue_snapshot(candidate: JSONDict, current: JSONDict) -> bool:
    candidate_updated_at = parse_github_datetime(candidate.get("updated_at"))
    current_updated_at = parse_github_datetime(current.get("updated_at"))
    if candidate_updated_at is None:
        return False
    if current_updated_at is None:
        return True
    return candidate_updated_at > current_updated_at



def parse_github_datetime(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


@dlt.resource(
    name=RESOURCE_NAME,
    table_name=RESOURCE_NAME,
    write_disposition=RESOURCE_WRITE_DISPOSITION,
    merge_key=RESOURCE_MERGE_KEY,
    primary_key=RESOURCE_PRIMARY_KEY,
    columns=RESOURCE_COLUMNS,
)
def github_issues_resource(
    owner: str,
    repo: str,
    token: Optional[str] = None,
    *,
    base_url: str = DEFAULT_GITHUB_API_BASE_URL,
    per_page: int = DEFAULT_PER_PAGE,
    state: str = DEFAULT_STATE,
    session: Optional[requests.Session] = None,
    updated_at=dlt.sources.incremental(
        RESOURCE_CURSOR_FIELD,
        initial_value=DEFAULT_INITIAL_UPDATED_AT,
        row_order="asc",
    ),
):
    client = GitHubIssuesClient(token=token, base_url=base_url, session=session)

    for page in client.iter_issue_pages(
        owner=owner,
        repo=repo,
        since=updated_at.start_value,
        per_page=per_page,
        state=state,
    ):
        shaped_page = collapse_issue_snapshots(
            transform_issue_page(page, owner=owner, repo=repo)
        )
        if shaped_page:
            yield shaped_page
