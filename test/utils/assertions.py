from pathlib import Path
import yaml
from typing import Any, Optional, Tuple


def assert_data_dir(package_dir: Path) -> None:
    assert (package_dir / "data").is_dir()


def assert_submissions_dir(package_dir: Path) -> None:
    assert (package_dir / "submissions").is_dir()


def assert_domjudge_problem_ini(package_dir: Path, expect: str) -> None:
    assert (package_dir / "domjudge-problem.ini").is_file()
    with open(package_dir / "domjudge-problem.ini", "r") as f:
        actual = f.read()
        assert actual == expect, f"actual: {actual}, expect: {expect}"


def assert_problem_yaml(package_dir: Path, expect: dict[str, Any]) -> None:
    assert (package_dir / "problem.yaml").is_file()
    with open(package_dir / "problem.yaml", "r", encoding="utf-8") as f:
        actual = yaml.safe_load(f.read())
        assert actual == expect, f"actual: {actual}, expect: {expect}"


def assert_file(package_dir: Path, file: str, expect: Optional[str] = None) -> None:
    assert (package_dir / file).is_file()
    if expect is None:
        return
    with open(package_dir / file, "r") as f:
        actual = f.read()
        assert actual == expect, f"actual: {actual}, expect: {expect}"


def assert_no_file(package_dir: Path, file: str) -> None:
    assert not (package_dir / file).is_file()


def assert_sample_data(package_dir: Path, expect: Tuple[str, str] = ("01.in", "01.ans")) -> None:
    assert (package_dir / "data" / "sample").is_dir()
    for file in expect:
        assert (package_dir / "data" / "sample" / file).is_file()


def assert_no_sample_data(package_dir: Path) -> None:
    assert not any((package_dir / "data" / "sample").iterdir())


def assert_secret_data(package_dir: Path) -> None:
    assert any((package_dir / "data" / "secret").iterdir())


def assert_submission(package_dir: Path, result: str, name: str) -> None:
    assert (package_dir / "submissions" / result / name).is_file()


def assert_no_testlib(package_dir: Path, dir: str = "checker", name: str = "check.cpp") -> None:
    assert not (package_dir / "output_validators" / dir / "testlib.h").is_file()
    assert not (package_dir / "output_validators" / dir / name).is_file()


def assert_testlib(package_dir: Path, dir: str = "checker", name: str = "check.cpp") -> None:
    assert (package_dir / "output_validators" / dir / "testlib.h").is_file()
    assert (package_dir / "output_validators" / dir / name).is_file()


def assert_magic_string(package_dir: Path, result: str, name: str, magic_string: str) -> None:
    assert_submission(package_dir, result, name)
    with open(package_dir / "submissions" / result / name, "r") as f:
        assert magic_string in f.read()
