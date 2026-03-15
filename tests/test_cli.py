from dlthubsnow import cli
from dlthubsnow.config import DemoSettings


class DummyLoadInfo:
    def __init__(self, has_failed_jobs: bool) -> None:
        self.has_failed_jobs = has_failed_jobs

    def __str__(self) -> str:
        return f"DummyLoadInfo(has_failed_jobs={self.has_failed_jobs})"


def test_main_returns_zero_when_load_completes_without_failed_jobs(
    monkeypatch, capsys
) -> None:
    settings = DemoSettings()
    monkeypatch.setattr(cli.DemoSettings, "from_env", classmethod(lambda cls: settings))
    monkeypatch.setattr(cli, "run_pipeline", lambda actual_settings: DummyLoadInfo(False))

    exit_code = cli.main([])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert settings.repo_full_name in captured.out
    assert "DummyLoadInfo(has_failed_jobs=False)" in captured.out
    assert captured.err == ""


def test_main_returns_non_zero_when_dlt_reports_failed_jobs(
    monkeypatch, capsys
) -> None:
    monkeypatch.setattr(
        cli.DemoSettings, "from_env", classmethod(lambda cls: DemoSettings())
    )
    monkeypatch.setattr(cli, "run_pipeline", lambda actual_settings: DummyLoadInfo(True))

    exit_code = cli.main([])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "DummyLoadInfo(has_failed_jobs=True)" in captured.out
    assert "dlt run reported failed jobs." in captured.err
