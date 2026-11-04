import shutil
import zipfile
from collections.abc import Callable
from pathlib import Path

from p2d import ConvertOptions, DomjudgeOptions, GlobalConfig, convert

NORMAL_PACKAGE = "little-h-reboot-7$linux.zip"
INTERACTIVE_PACKAGE = "guess-array-1$linux.zip"

type PackageFactory = Callable[[str, bool], Path]


def prepare_package(source: Path, destination: Path, *, zipped: bool) -> Path:
    if zipped:
        path = destination.with_suffix(".zip")
        shutil.copyfile(source, path)
        return path
    with zipfile.ZipFile(source) as archive:
        archive.extractall(destination)
    return destination


def read_archive(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        return {name: archive.read(name) for name in archive.namelist() if not name.endswith("/")}


def export(
    package: Path,
    output: Path,
    options: DomjudgeOptions | None = None,
    config: GlobalConfig | None = None,
    short_name: str = "A",
    *,
    testset_name: str | None = None,
) -> dict[str, bytes]:
    convert(
        package,
        short_name=short_name,
        options=ConvertOptions(
            output=output,
            options=DomjudgeOptions() if options is None else options,
            global_config=GlobalConfig() if config is None else config,
            testset_name=testset_name,
        ),
    )
    return read_archive(output)
