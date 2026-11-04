# Polygon2DOMjudge

[![Test][gh-test-badge]][gh-test]
[![GitHub release][gh-release-badge]][gh-release]

[中文](README.cn.md)

## What is this

It is a simple python script converting polygon package to DOMjudge (kattis) package.

## Install

Requires Python **3.12 or newer**.

### Run directly with uvx

```bash
# From PyPI (stable)
uvx p2d --help

# From GitHub (latest)
uvx --from git+https://github.com/cn-xcpc-tools/Polygon2DOMjudge p2d --help
```

### From PyPI (stable release, has been used in some contests)

```bash
# Using uv (recommended)
uv tool install p2d

# Or using pipx
pipx install p2d
```

### From source (latest version, under development with new features)

```bash
# Using uv (recommended)
uv tool install git+https://github.com/cn-xcpc-tools/Polygon2DOMjudge

# Or using pipx
pipx install git+https://github.com/cn-xcpc-tools/Polygon2DOMjudge
```

## CLI Example

First, you should build **full** package from Polygon and download the **Linux** package to your local.

> [!WARNING]
> If you download the standard package and then run `doall.sh` to build the full package by yourself, the linebreaks will be CRLF.
> Make sure you convert the linebreaks to LF before running the script because DOMjudge is running on Linux.

```bash
# Download the full package from Polygon to /path/to/polygon-package.zip
$ p2d --code A --color "#FF0000" -o /path/to/domjudge-package.zip /path/to/polygon-package.zip
```

Run this command to make a package from `/path/to/polygon-package.zip` to `/path/to/domjudge-package.zip` and set `code` and `color`.

You can omit the output path, and the default output path will be in the current working directory and named as `{{ code }}.zip`.

All available parameters are:

| Option | Description |
| --- | --- |
| `--code`, `--short-name` | Problem short name in DOMjudge; prompted for when omitted. |
| `--color` | Problem color, default `#000000`. |
| `-o`, `--output` | Output ZIP path or directory. |
| `-c`, `--config` | Path to a TOML configuration file. |
| `-y`, `--yes` | Skip confirmation. |
| `--default` | Force the default output validator. |
| `--validator-flags` | Flags for the default output validator; used with `--default`. |
| `--auto` | Replace recognized standard checkers with the default validator using configured flags. Mutually exclusive with `--default`. |
| `--memory-limit` | Override the memory limit in MB; otherwise use the Polygon limit. `-1` uses the DOMjudge default. |
| `--output-limit` | Override the output limit in MB; defaults to `-1`, the DOMjudge default. |
| `--hide-sample` | Hide sample input and output; always enabled for interactive problems. |
| `--keep`, `--keep-sample` | Preserve numbered sample outputs from the solution, e.g. `--keep 1 --keep 2`. |
| `--external-id` | Override the external ID, which otherwise comes from the Polygon problem short name. Consider overriding it if the original ID hints at the solution. |
| `--with-statement` | Include the PDF statement. |
| `--with-attachments` | Include attachments such as local interaction tools. |
| `--testset` | Select a testset; required when the problem has multiple testsets. |
| `-l`, `--log-level` | Logging level; default `info`. |
| `-v`, `--version` | Print version information. |

By default, visible sample outputs are replaced with outputs from the statement. Sample inputs remain those from the generated tests because DOMjudge does not support different downloaded sample inputs. Use `--keep` when a statement output is a placeholder. Hidden samples ignore `--keep`.

### Convert the whole contest

You can use `p2d-contest` to get a script to convert all problems in a contest.

```bash
# Download the contest.xml from Polygon first
$ p2d-contest /path/to/contest.xml > convert.sh
```

## Config

In [config.toml](./config.example.toml), you can change some special checker's validator's flags, which will be used to replace the checker with the default output validator when `--auto` is set.

> [!NOTE]
> You should create a new file named `config.toml` or something else and pass it to the script with `--config` parameter. The script will merge the default config with your config.

## Environment Variable

Don't change them unless you know what you are doing.

- `TESTLIB_PATH`

## API Example

> [!WARNING]
> The API is not stable and may change in the future.

This is an example to convert all problems in a contest defined in [`problems.yaml`](https://ccs-specs.icpc.io/draft/contest_package#problemsyaml) to DOMjudge package.

```python
from pathlib import Path

import yaml

from p2d import ConvertOptions, DomjudgeOptions, convert

polygon = Path("/path/to/polygon-packages")
domjudge = Path("/path/to/domjudge-packages")

with open(domjudge / "problems.yaml") as f:
    problems = yaml.safe_load(f)

for problem in problems:
    prob_id = problem["id"]
    convert(
        polygon / f"{prob_id}.zip",
        short_name=problem["label"],
        options=ConvertOptions(
            output=domjudge / f"{prob_id}.zip",
            options=DomjudgeOptions(color=problem["rgb"]),
        ),
    )
```

## Known Issues

- For interactive problems, you must validate the output in the interactors, because DOMjudge cannot handle `tout` stream like Polygon.
- For multi-pass problems
  - Some logic are different from Polygon, you may need to modify it to fit the DOMjudge environment, DOMjudge will use `-DDOMJUDGE` macro to distinguish whether it is in DOMjudge environment, so you can use it to adapt your code.
  - You may need to call `tout.open(make_new_file_in_a_dir(argv[3], "nextpass.in"), std::ios_base::out)` to create the next pass input file when there exists a next pass.

## Development

Development uses uv, Ruff and ty, with Python 3.15 selected by `.python-version`. CI tests Python 3.12–3.15.

```bash
# install
uv sync --locked

# format, lint and type check
uv run --locked ruff format --check .
uv run --locked ruff check .
uv run --locked ty check

# run unittest
uv run --locked pytest

# pre-commit hooks
uv run --locked pre-commit install
uv run --locked pre-commit run --all-files

# build
uv build
```

[gh-test-badge]: https://github.com/cn-xcpc-tools/Polygon2DOMjudge/actions/workflows/test.yml/badge.svg
[gh-test]: https://github.com/cn-xcpc-tools/Polygon2DOMjudge/actions/workflows/test.yml
[gh-release-badge]: https://img.shields.io/github/release/cn-xcpc-tools/Polygon2DOMjudge.svg
[gh-release]: https://GitHub.com/cn-xcpc-tools/Polygon2DOMjudge/releases/
