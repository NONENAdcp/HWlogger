import tomllib
from pathlib import Path

from hwlogger import __version__


def test_release_version_has_one_source_of_truth():
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["dynamic"] == ["version"]
    assert (
        project["tool"]["setuptools"]["dynamic"]["version"]["attr"]
        == "hwlogger.__version__"
    )
    assert __version__ == "0.1.6"
