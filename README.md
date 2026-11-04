# Polygon2DOMjudge

[![Test][gh-test-badge]][gh-test]
[![GitHub release][gh-release-badge]][gh-release]

[中文](README.cn.md)

Convert Polygon problem packages to DOMjudge packages. Exports use the [2025-09 format](https://icpc.io/problem-package-format/spec/2025-09.html) with DOMjudge-specific conventions. Older DOMjudge installations can use `--legacy`; legacy support is deprecated and may be removed at any time.

## Installation

Requires Python **3.12 or newer**.

```bash
uv tool install p2d
# Latest source:
uv tool install git+https://github.com/cn-xcpc-tools/Polygon2DOMjudge
```

You can also use `pipx install p2d`, or run directly with `uvx p2d --help`.

## Usage

Download a **full Linux package** from Polygon, then convert the ZIP or its extracted directory:

```bash
p2d polygon-package.zip --code A --color '#FF0000' -o domjudge-package.zip
```

The default output is `<code>.zip`. Ensure source files and test data use UTF-8 and LF line endings, especially when building the package yourself with `doall.sh`.

| Option | Description |
| --- | --- |
| `--code`, `--short-name` | Problem short name; prompted for when omitted. |
| `--color` | Problem color, default `#000000`. |
| `--legacy` | Export the deprecated legacy format. |
| `-o`, `--output` | Output ZIP path or directory; existing archives are not overwritten. |
| `-c`, `--config` | TOML configuration file; a local `config.toml` takes precedence. |
| `-y`, `--yes` | Skip confirmation. |
| `--default` | Force the default output validator. |
| `--validator-flags` | Default-validator arguments; used with `--default`. |
| `--auto` | Replace recognized standard checkers with the default validator; mutually exclusive with `--default`. |
| `--memory-limit` | Memory limit in MiB; defaults to the Polygon limit. `-1` uses the DOMjudge default. |
| `--output-limit` | Output limit in MiB; defaults to `-1`, the DOMjudge default. |
| `--hide-sample` | Hide samples; always enabled for problems with an interactor. |
| `--keep`, `--keep-sample` | Preserve solution outputs for selected samples, e.g. `--keep 1 --keep 2`. |
| `--external-id` | Override the external ID, which defaults to the Polygon short name. |
| `--with-statement` | Include the PDF statement. |
| `--with-attachments` | Include attachments such as local interaction tools. |
| `--testset` | Select a testset; required when there are multiple testsets. |
| `-l`, `--log-level` | Logging level, default `info`. |
| `-v`, `--version` | Print version information. |

Samples provided for contestants to download use the statement's outputs when available. Use `--keep` for placeholders; it has no effect on hidden samples.

`p2d-contest contest.xml` lists the problem indices and names from Polygon contest metadata.

## Configuration

See [config.example.toml](config.example.toml) for language preferences, standard-checker arguments and solution tags. Use `TESTLIB_PATH` to supply a directory containing an alternative `testlib.h`.

Solution tags use `permitted` and `required` verdict lists:

```toml
[tag]
main = { permitted = ["AC"] }
wrong-answer = { permitted = ["AC", "WA"], required = ["WA"] }
time-limit-exceeded-or-accepted = { permitted = ["AC", "TLE"] }
rejected = { required = ["RTE", "TLE", "WA"] }
```

`permitted` lists the allowed results for each test. `required` requires at least one test with any of its listed results. Each omitted field defaults to `["AC", "WA", "TLE", "RTE"]`.

A custom `tag` table replaces the default mapping, so include all tags you need. Migrate old list-valued entries to this syntax, including when using `--legacy`. Legacy export rejects rules it cannot represent.

## Compatibility

- Default export requires DOMjudge with [2025-09 submission metadata support](https://github.com/DOMjudge/domjudge/pull/3833). It requires a Polygon problem URL.
- Custom validators go into `output_validator/`. Submission rules use standard directories or `submissions/submissions.yaml`; solution sources are preserved. Existing `@EXPECTED_RESULTS@` and `@EXPECTED_SCORE@` annotations still affect judging.
- Interactors must validate contestant output themselves; DOMjudge does not run a separate checker over `tout`.
- Multi-pass conversion is experimental and supports two passes. C++ interactors are built with `-DDOMJUDGE`. To request another pass, write `nextpass.in` in the feedback directory and exit with code 42:

  ```cpp
  #include <filesystem>
  #include <fstream>

  // Inside the interactor, after preparing next_input_data:
  std::ofstream next_input(std::filesystem::path(argv[3]) / "nextpass.in");
  next_input << next_input_data;
  next_input.close();
  if (!next_input)
      quitf(_fail, "Cannot write next-pass input");
  quitf(_ok, "Continue to next pass");
  ```

## Python API

```python
from p2d import ConvertOptions, DomjudgeOptions, convert

convert(
    "polygon-package.zip",
    short_name="A",
    options=ConvertOptions(
        output="domjudge-package.zip",
        options=DomjudgeOptions(color="#FF0000", with_statement=True),
    ),
)
```

Use `DomjudgeOptions(legacy=True)` for legacy output. The API may change.

## Development

```bash
uv sync --locked
uv run --locked pre-commit install
uv run --locked pre-commit run --all-files
uv run --locked pytest
uv build
```

[gh-test-badge]: https://github.com/cn-xcpc-tools/Polygon2DOMjudge/actions/workflows/test.yml/badge.svg
[gh-test]: https://github.com/cn-xcpc-tools/Polygon2DOMjudge/actions/workflows/test.yml
[gh-release-badge]: https://img.shields.io/github/release/cn-xcpc-tools/Polygon2DOMjudge.svg
[gh-release]: https://GitHub.com/cn-xcpc-tools/Polygon2DOMjudge/releases/
