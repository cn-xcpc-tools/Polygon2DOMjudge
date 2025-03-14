# Polygon2DOMjudge

[![Test][gh-test-badge]][gh-test]
[![GitHub release][gh-release-badge]][gh-release]

## 这是什么

这是一个简单的将 polygon 题目包转换成 DOMjudge (kattis) 题目包的 python 脚本。

## 安装

### 从 PyPI（稳定版本, 已经在一些比赛中使用过）

```bash
pipx install p2d
```

### 从源码（最新版本，正在开发中，有新的特性）

```bash
pipx install git+https://github.com/cn-xcpc-tools/Polygon2DOMjudge
```

## 命令行使用示例

首先，你需要从 Polygon 构建 **完整的** 题目包并将 **Linux** 题目包下载到本地。

> [!WARNING]
> 如果你下载了标准的题目包并且运行 `doall.sh` 来构建完整的题目包，那么换行符将会是 CRLF。
> 在运行脚本之前，请确保将换行符转换为 LF，因为 DOMjudge 是在 Linux 上运行的。

```bash
# 首先从 Polygon 下载完整的 Linux 题目包到本地
$ ./bin/p2d --code A --color "#FF0000" -o /path/to/domjudge-package.zip /path/to/polygon-package.zip
```

运行此命令可以从 `/path/to/polygon-package.zip` 处题目包转换为 `/path/to/domjudge-package.zip`，并设置  `code` 和 `color` 属性。

你可以省略输出路径，输出路径将会在当前工作目录中，并命名为 `{{ code }}.zip`。

所有可用的命令行参数如下：

- `--code`: 题目在 DOMjudge 比赛中的 short name。
- `--color`: 题目在 DOMjudge 中的颜色。
- `--default`: 强制使用 DOMjudge 默认的输出校验器。
- `--validator-flags`: 为输出校验器添加一些命令行参数，仅在 `--default` 被设置时生效。
- `--auto`: 自动使用 DOMjudge 默认的输出校验器，即如果 checker 在配置文件中被定义，则使用默认的输出校验器与合适的命令行参数替代。
- `--memory-limit`: 覆盖 DOMjudge 题目包的内存限制，如果不设置，则使用 Polygon 题目包中的内存限制。
- `--output-limit`: 覆盖 DOMjudge 题目包的输出限制，如果不设置，则使用 DOMjudge 设置中默认的输出限制。
- `--hide-sample`: 隐藏题面中的样例输入输出，不会为选手提供样例数据（如果是交互题，则此参数强制为 True）。
    当此参数不设置为 True 且样例输出与标程的输出不同时 （通常两者都是符合要求的答案），
    样例输出将会被替换为题面中提供的样例输出。但是样例输入不会被替换，因为 DOMjudge 不支持下载的样例输入与实际使用的不同。
- `--keep-sample`: 保持样例输出与标程的输出一致，当题面中的样例输出是一个占位符时，这个参数很有用。（默认情况下，所有的样例输出将会被替换为题面中提供的样例输出）
- `--external-id`: 指定题目在 DOMjudge 中的 external id，如果不设置，则使用 Polygon 中的题目 short-name。
- `--with-statement`: 在 DOMjudge 题目包中包含 pdf 题面。
- `--with-attachments`: 在 DOMjudge 题目包中包含附件（例如交互题的本地测试工具）。
- `--testset`: 指定要转换的测试点集，如果题目有多个测试点集，则必须指定测试点集的名称。

### 转换整个比赛

你可以使用 `p2d-contest` 来获取一个脚本来转换整个比赛中的题目。

```bash
# 首先从 Polygon 下载 contest.xml
$ ./bin/p2d-contest /path/to/contest.xml > convert.sh
```

## 配置

在 [config.toml](./p2d/asset/config.toml) 文件中，你可以设置一些特殊的 checker 的输出校验器参数，这会在 `--auto` 参数被设置时用来将 checker 替换为默认的输出校验器。

> [!NOTE]
> 你不应该直接编辑这个文件，而是应该创建一个新的文件，命名为 `config.toml` 或其他名称，并使用 `--config` 参数将其传递给脚本。脚本将会合并默认配置和你的配置。

## 环境变量

某些时候可能会有用。但如果你不知道你在干啥，请不要随便修改。

- `CONFIG_PATH`
- `TESTLIB_PATH`

## API 使用示例

> [!WARNING]
> API 不是稳定的，可能会在未来的版本中发生变化。

这是一个将 [`problems.yaml`](https://ccs-specs.icpc.io/draft/contest_package#problemsyaml) 中定义的比赛中的所有题目转换为 DOMjudge 题目包的示例。

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
        short_name=problem['label'],
        color=problem['rgb'],
    )
```

## 已知Issues

- 对于交互题，您必须在交互器中完成对输出的验证（即，在交互器中直接返回最终的结果，略去使用checker对`tout`文件内容进行验证的步骤），因为 DOMjudge 无法像 Polygon 那样处理 `tout` 流。
- 对于 multi-pass 问题
  - 部分逻辑可能与 Polygon 不同，您可能需要调整一些逻辑来适应 DOMjudge 的要求。DOMjudge 会使用 `-DDOMJUDGE` 宏定义来区分是否为 DOMjudge 环境，您可以使用这个宏定义来调整您的代码。
  - 您可能需要调用 `tout.open(make_new_file_in_a_dir(argv[3], "nextpass.in"))` 来获取下一次传递的输入文件。

## 开发

```bash
# install
uv sync

# build
uv build

# run unittest
uv run pytest
```

[gh-test-badge]: https://github.com/cn-xcpc-tools/Polygon2DOMjudge/actions/workflows/test.yml/badge.svg
[gh-test]: https://github.com/cn-xcpc-tools/Polygon2DOMjudge/actions/workflows/test.yml
[gh-release-badge]: https://img.shields.io/github/release/cn-xcpc-tools/Polygon2DOMjudge.svg
[gh-release]: https://GitHub.com/cn-xcpc-tools/Polygon2DOMjudge/releases/
