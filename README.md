# Polygon2DOMjudge

[![Test][gh-test-badge]][gh-test]
[![GitHub release][gh-release-badge]][gh-release]

[中文](README.cn.md)

## What is this

It is a simple python script converting polygon package to DOMjudge (kattis) package.

## Install

### From PyPI (stable release, has been used in some contests)

```bash
pipx install p2d
```

### From source (latest version, under development with new features)

```bash
pipx install git+https://github.com/cn-xcpc-tools/Polygon2DOMjudge
```

## CLI Example

```bash
# Unzip your polygon-package to /path/to/polygon-package first
$ p2d --code A --color "#FF0000" -o /path/to/domjudge-package /path/to/polygon-package
# Or you can use /path/to/polygon-package.zip directly
$ p2d --code A --color "#FF0000" -o /path/to/domjudge-package /path/to/polygon-package.zip
```

Run this command to make a package from `/path/to/polygon-package` to `/path/to/domjudge-package.zip` and set `code` and `color`.

All available parameters are:

- `--code`: problem short name in DOMjudge.
- `--color`: problem color in DOMjudge.
- `--default`: force use the default output validator.
- `--validator-flags`: add some flags to the output validator, only works when `--default` is set.
- `--auto`: use the default output validator if the checker is defined in config and can be replaced by the default one.
- `--memory-limit`: override the memory limit for DOMjudge package (in MB), default is using the memory limit defined in polygon package.
- `--output-limit`: override the output limit for DOMjudge package (in MB), default is using the default output limit in DOMjudge setting.
- `--hide-sample`: hide the sample input and output from the problem statement, no sample data will be available for the contestants (force True if this is an interactive problem).
    When this is not set to True and the sample output is different from the main and correct solution, the sample output will be replaced with the one shipped with problem statement.
- `--testset`: specify the testset to convert, must specify the testset name if the problem has multiple testsets.

## Config

In [config.toml](./p2d/asset/config.toml), you can change some special checker's validator's flags, which will be used to replace the checker with the default output validator when `--auto` is set.

> [!NOTE]
> You should not edit this file directly, instead, you should create a new file named `config.toml` or something else and pass it to the script with `--config` parameter. The script will merge the default config with your config.

## Environment Variable

Don't change them unless you know what you are doing.

- `CONFIG_PATH`
- `TESTLIB_PATH`

## API Example

> [!WARNING]
> The API is not stable and may change in the future.

This is an example to convert all problems in a contest defined in [`problems.yaml`](https://ccs-specs.icpc.io/draft/contest_package#problemsyaml) to DOMjudge package.

```python
import yaml
from pathlib import Path

from p2d import convert

polygon = Path('/path/to/polygon-packages')
domjudge = Path('/path/to/domjudge-packages')

with open(domjudge / 'problems.yaml') as f:
    problems = yaml.safe_load(f)

for problem in problems:
    prob_id = problem['id']
    convert(
        polygon / f'{prob_id}.zip',
        domjudge / f'{prob_id}.zip',
        code=problem['label'],
        color=problem['rgb'],
    )
```

## Development

```bash
# install
poetry install

# build
poetry build

# run unittest
poetry run pytest

# release
./release.sh ${your version}
```

[gh-test-badge]: https://github.com/cn-xcpc-tools/Polygon2DOMjudge/actions/workflows/test.yml/badge.svg
[gh-test]: https://github.com/cn-xcpc-tools/Polygon2DOMjudge/actions/workflows/test.yml
[gh-release-badge]: https://img.shields.io/github/release/cn-xcpc-tools/Polygon2DOMjudge.svg
[gh-release]: https://GitHub.com/cn-xcpc-tools/Polygon2DOMjudge/releases/
