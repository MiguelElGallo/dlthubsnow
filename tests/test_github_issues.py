from dlthubsnow.config import DemoSettings
from dlthubsnow.github_issues import (
    RESOURCE_COLUMNS,
    RESOURCE_CURSOR_FIELD,
    RESOURCE_MERGE_KEY,
    RESOURCE_PRIMARY_KEY,
    RESOURCE_WRITE_DISPOSITION,
    build_issue_query_params,
    collapse_issue_snapshots,
    transform_issue_page,
)



def test_transform_issue_page_filters_pull_requests_and_shapes_issue() -> None:
    page = [
        {
            "id": 101,
            "number": 7,
            "title": "Regular issue",
            "state": "open",
            "state_reason": None,
            "body": "Something is wrong",
            "html_url": "https://github.com/dlt-hub/dlt/issues/7",
            "comments": 3,
            "locked": False,
            "user": {"login": "alice", "type": "User"},
            "assignee": {"login": "bob"},
            "assignees": [{"login": "bob"}],
            "labels": [{"name": "bug"}, {"name": "snowflake"}],
            "milestone": {"title": "v1"},
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
            "closed_at": None,
        },
        {
            "id": 202,
            "number": 8,
            "title": "Actually a PR",
            "pull_request": {"url": "https://api.github.com/repos/dlt-hub/dlt/pulls/8"},
            "updated_at": "2024-01-03T00:00:00Z",
        },
    ]

    shaped = transform_issue_page(page, owner="dlt-hub", repo="dlt")

    assert shaped == [
        {
            "id": 101,
            "number": 7,
            "title": "Regular issue",
            "state": "open",
            "state_reason": None,
            "body": "Something is wrong",
            "html_url": "https://github.com/dlt-hub/dlt/issues/7",
            "comments": 3,
            "locked": False,
            "author_login": "alice",
            "author_type": "User",
            "assignee_login": "bob",
            "assignee_logins": ["bob"],
            "label_names": ["bug", "snowflake"],
            "milestone_title": "v1",
            "repository_owner": "dlt-hub",
            "repository_name": "dlt",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
            "closed_at": None,
        }
    ]



def test_collapse_issue_snapshots_keeps_latest_updated_at_per_issue_id() -> None:
    issues = [
        {"id": 101, "title": "old", "updated_at": "2024-01-01T00:00:00Z"},
        {"id": 101, "title": "new", "updated_at": "2024-01-02T00:00:00Z"},
        {"id": 202, "title": "first", "updated_at": "2024-01-05T00:00:00Z"},
        {"id": 202, "title": "same-time-second", "updated_at": "2024-01-05T00:00:00Z"},
    ]

    collapsed = collapse_issue_snapshots(issues)

    assert collapsed == [
        {"id": 101, "title": "new", "updated_at": "2024-01-02T00:00:00Z"},
        {"id": 202, "title": "first", "updated_at": "2024-01-05T00:00:00Z"},
    ]



def test_build_issue_query_params_uses_incremental_since_and_caps_page_size() -> None:
    params = build_issue_query_params(
        since="2024-01-01T00:00:00Z",
        per_page=250,
        state="open",
    )

    assert params == {
        "state": "open",
        "sort": "updated",
        "direction": "asc",
        "per_page": 100,
        "since": "2024-01-01T00:00:00Z",
    }



def test_demo_settings_reads_repo_defaults_from_env(monkeypatch) -> None:
    monkeypatch.setenv("DLTHUBSNOW_OWNER", "meltano")
    monkeypatch.setenv("DLTHUBSNOW_REPO", "meltano")
    monkeypatch.setenv("DLTHUBSNOW_STATE", "closed")
    monkeypatch.setenv("DLTHUBSNOW_PER_PAGE", "50")
    monkeypatch.setenv("DLTHUBSNOW_INITIAL_UPDATED_AT", "2024-02-01T00:00:00Z")

    settings = DemoSettings.from_env()

    assert settings.repo_full_name == "meltano/meltano"
    assert settings.state == "closed"
    assert settings.per_page == 50
    assert settings.initial_updated_at == "2024-02-01T00:00:00Z"



def test_demo_settings_falls_back_to_standard_github_token_env(monkeypatch) -> None:
    monkeypatch.delenv("DLTHUBSNOW_GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "token-from-standard-env")

    settings = DemoSettings.from_env()

    assert settings.github_token == "token-from-standard-env"



def test_demo_settings_reads_full_refresh_flag_from_env(monkeypatch) -> None:
    monkeypatch.setenv("DLTHUBSNOW_FULL_REFRESH", "true")

    settings = DemoSettings.from_env()

    assert settings.full_refresh is True



def test_resource_contract_documents_incremental_merge_behavior() -> None:
    assert RESOURCE_CURSOR_FIELD == "updated_at"
    assert RESOURCE_PRIMARY_KEY == "id"
    assert RESOURCE_MERGE_KEY == "id"
    assert RESOURCE_WRITE_DISPOSITION == {"disposition": "merge", "strategy": "upsert"}
    assert RESOURCE_COLUMNS["updated_at"]["dedup_sort"] == "desc"
