# Polygon2DOMjudge

[![Test][gh-test-badge]][gh-test]
[![GitHub release][gh-release-badge]][gh-release]

## 这是什么

这是一个简单的将 polygon 题目包转换成 DOMjudge (kattis) 题目包的 python 脚本。

## 安装

需要 **Python 3.12 或更新版本**。

### 使用 uvx 直接运行

```bash
# 从 PyPI（稳定版）
uvx p2d --help

# 从 GitHub（最新版）
uvx --from git+https://github.com/cn-xcpc-tools/Polygon2DOMjudge p2d --help
```

### 从 PyPI（稳定版本, 已经在一些比赛中使用过）

```bash
# 使用 uv（推荐）
uv tool install p2d

# 或使用 pipx
pipx install p2d
```

### 从源码（最新版本，正在开发中，有新的特性）

```bash
# 使用 uv（推荐）
uv tool install git+https://github.com/cn-xcpc-tools/Polygon2DOMjudge

# 或使用 pipx
pipx install git+https://github.com/cn-xcpc-tools/Polygon2DOMjudge
```

## 命令行使用示例

首先，你需要从 Polygon 构建 **完整的** 题目包并将 **Linux** 题目包下载到本地。

> [!WARNING]
> 如果你下载了标准的题目包并且运行 `doall.sh` 来构建完整的题目包，那么换行符将会是 CRLF。
> 在运行脚本之前，请确保将换行符转换为 LF，因为 DOMjudge 是在 Linux 上运行的。

```bash
# 首先从 Polygon 下载完整的 Linux 题目包到本地
$ p2d --code A --color "#FF0000" -o /path/to/domjudge-package.zip /path/to/polygon-package.zip
```

运行此命令可以从 `/path/to/polygon-package.zip` 处题目包转换为 `/path/to/domjudge-package.zip`，并设置  `code` 和 `color` 属性。

你可以省略输出路径，输出路径将会在当前工作目录中，并命名为 `{{ code }}.zip`。

所有可用的命令行参数如下：

| 选项 | 说明 |
| --- | --- |
| `--code`, `--short-name` | DOMjudge 中的题目简称；省略时会提示输入。 |
| `--color` | 题目颜色，默认为 `#000000`。 |
| `-o`, `--output` | 输出 ZIP 路径或目录。 |
| `-c`, `--config` | TOML 配置文件路径。 |
| `-y`, `--yes` | 跳过确认。 |
| `--default` | 强制使用默认输出校验器。 |
| `--validator-flags` | 默认输出校验器的参数，与 `--default` 配合使用。 |
| `--auto` | 按配置将已识别的标准 checker 替换为默认输出校验器；与 `--default` 互斥。 |
| `--memory-limit` | 覆盖内存限制，单位 MB；省略时使用 Polygon 的限制，`-1` 表示 DOMjudge 默认值。 |
| `--output-limit` | 覆盖输出限制，单位 MB；默认为 `-1`，表示 DOMjudge 默认值。 |
| `--hide-sample` | 隐藏样例输入输出；交互题强制启用。 |
| `--keep`, `--keep-sample` | 保留指定编号样例的标程输出，例如 `--keep 1 --keep 2`。 |
| `--external-id` | 覆盖 external ID；默认使用 Polygon 中的题目简称。如果原 ID 暗示了题目解法，建议用此参数覆盖。 |
| `--with-statement` | 包含 PDF 题面。 |
| `--with-attachments` | 包含附件，例如交互题的本地测试工具。 |
| `--testset` | 选择测试集；题目包含多个测试集时必填。 |
| `-l`, `--log-level` | 日志级别，默认为 `info`。 |
| `-v`, `--version` | 输出版本信息。 |

默认情况下，公开样例的输出会替换为题面中的输出。样例输入仍使用生成的测试数据，因为 DOMjudge 不支持不同的下载样例输入。题面输出为占位符时，可以用 `--keep` 保留对应标程输出。隐藏样例时，`--keep` 会被忽略。

### 转换整个比赛

你可以使用 `p2d-contest` 来获取一个脚本来转换整个比赛中的题目。

```bash
# 首先从 Polygon 下载 contest.xml
$ p2d-contest /path/to/contest.xml > convert.sh
```

## 配置

在 [config.toml](./config.example.toml) 文件中，你可以设置一些特殊的 checker 的输出校验器参数，这会在 `--auto` 参数被设置时用来将 checker 替换为默认的输出校验器。

> [!NOTE]
> 你应该创建一个新的文件，命名为 `config.toml` 或其他名称，并使用 `--config` 参数将其传递给脚本。脚本将会合并默认配置和你的配置。

## 环境变量

某些时候可能会有用。但如果你不知道你在干啥，请不要随便修改。

- `TESTLIB_PATH`

## API 使用示例

> [!WARNING]
> API 不是稳定的，可能会在未来的版本中发生变化。

这是一个将 [`problems.yaml`](https://ccs-specs.icpc.io/draft/contest_package#problemsyaml) 中定义的比赛中的所有题目转换为 DOMjudge 题目包的示例。

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

## 已知Issues

- 对于交互题，您必须在交互器中完成对输出的验证（即，在交互器中直接返回最终的结果，略去使用checker对`tout`文件内容进行验证的步骤），因为 DOMjudge 无法像 Polygon 那样处理 `tout` 流。
- 对于 multi-pass 问题
  - 部分逻辑可能与 Polygon 不同，您可能需要调整一些逻辑来适应 DOMjudge 的要求。DOMjudge 会使用 `-DDOMJUDGE` 宏定义来区分是否为 DOMjudge 环境，您可以使用这个宏定义来调整您的代码。
  - 当选手程序还需要运行时，您可能需要调用 `tout.open(make_new_file_in_a_dir(argv[3], "nextpass.in"), std::ios_base::out)` 来创建下一次运行的输入文件。

## 开发

开发使用 uv、Ruff 和 ty，`.python-version` 默认选择 Python 3.15。CI 测试 Python 3.12–3.15。

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
