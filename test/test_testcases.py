from collections.abc import Callable
from pathlib import Path

import pytest

from p2d.models import DomjudgeOptions
from p2d.p2d import Polygon2DOMjudge
from p2d.pipeline import ProcessPipeline, ProcessStep
from p2d.steps.testcases import add_testcases


@pytest.mark.parametrize("prepare_package", [True], ids=["dir"], indirect=True)
@pytest.mark.parametrize("legacy", [False, True], ids=["2025-09", "legacy"])
@pytest.mark.parametrize(
    ("keep_sample", "hide_sample", "statement_output", "expected_output"),
    [
        pytest.param(None, False, b"statement\n", b"statement\n", id="default"),
        pytest.param((), False, b"statement\n", b"statement\n", id="empty-keep"),
        pytest.param((1,), False, b"statement\n", b"original\n", id="keep-selected"),
        pytest.param((2,), False, b"statement\n", b"statement\n", id="keep-other"),
        pytest.param(None, False, None, b"original\n", id="no-statement-output"),
        pytest.param(None, False, b"original\n", b"original\n", id="identical-output"),
        pytest.param(None, True, b"statement\n", b"original\n", id="hidden-sample"),
        pytest.param((1,), True, b"statement\n", b"original\n", id="hidden-keep-ignored"),
    ],
)
def test_sample_output_selection(
    temp_dir: Path,
    prepare_package: Callable[[str], Path],
    caplog: pytest.LogCaptureFixture,
    legacy: bool,
    keep_sample: tuple[int, ...] | None,
    hide_sample: bool,
    statement_output: bytes | None,
    expected_output: bytes,
) -> None:
    package_dir = prepare_package("little-h-reboot-7$linux.zip")
    output_dir = temp_dir / "domjudge"
    (package_dir / "tests" / "01.a").write_bytes(b"original\n")
    sample_output = package_dir / "statements" / "english" / "example.01.a"
    if statement_output is None:
        sample_output.unlink()
    else:
        sample_output.write_bytes(statement_output)

    converter = Polygon2DOMjudge(
        package_dir,
        output_dir,
        temp_dir / "result",
        "A",
        options=DomjudgeOptions(legacy=legacy, keep_sample=keep_sample, hide_sample=hide_sample),
        process_pipeline=ProcessPipeline((ProcessStep("add_testcases", add_testcases),)),
    )
    converter.process()

    data_dir = output_dir / "data" / ("secret" if hide_sample else "sample")
    assert (data_dir / "01.ans").read_bytes() == expected_output
    assert (data_dir / "01.in").read_bytes() == (package_dir / "tests" / "01").read_bytes()
    if hide_sample:
        assert not any((output_dir / "data" / "sample").iterdir())
    if not hide_sample and statement_output == b"statement\n":
        action = "keep the original output" if expected_output == b"original\n" else "use the sample output"
        assert f"Output file 01.a is different from the sample output file, {action}." in caplog.text
