# Polygon2DOMjudge

[![Test][gh-test-badge]][gh-test]
[![GitHub release][gh-release-badge]][gh-release]

[English](README.md)

将 Polygon 题目包转换为 DOMjudge 题目包。默认采用 [2025-09 格式](https://icpc.io/problem-package-format/spec/2025-09.html)，并适配 DOMjudge 的约定。旧版 DOMjudge 可使用 `--legacy`；旧格式支持已弃用，随时可能移除。

## 安装

需要 **Python 3.12 或更新版本**。

```bash
uv tool install p2d
# 最新源码：
uv tool install git+https://github.com/cn-xcpc-tools/Polygon2DOMjudge
```

也可以使用 `pipx install p2d`，或通过 `uvx p2d --help` 直接运行。

## 使用

从 Polygon 下载 **完整的 Linux 题目包**，然后转换 ZIP 或解压后的目录：

```bash
p2d polygon-package.zip --code A --color '#FF0000' -o domjudge-package.zip
```

默认输出为 `<code>.zip`。源码和测试数据应使用 UTF-8 和 LF 换行，自行运行 `doall.sh` 构建题包时尤其需要注意。

| 选项 | 说明 |
| --- | --- |
| `--code`, `--short-name` | 题目简称；省略时提示输入。 |
| `--color` | 题目颜色，默认为 `#000000`。 |
| `--legacy` | 导出已弃用的旧格式。 |
| `-o`, `--output` | 输出 ZIP 路径或目录；不覆盖已有压缩包。 |
| `-c`, `--config` | TOML 配置文件；当前目录的 `config.toml` 优先。 |
| `-y`, `--yes` | 跳过确认。 |
| `--default` | 强制使用默认输出校验器。 |
| `--validator-flags` | 默认输出校验器参数，与 `--default` 配合使用。 |
| `--auto` | 将已识别的标准 checker 替换为默认输出校验器，与 `--default` 互斥。 |
| `--memory-limit` | 内存限制，单位 MiB，默认使用 Polygon 限制；`-1` 表示 DOMjudge 默认值。 |
| `--output-limit` | 输出限制，单位 MiB，默认为 `-1`，表示 DOMjudge 默认值。 |
| `--hide-sample` | 隐藏样例；有 interactor 的题目始终启用。 |
| `--keep`, `--keep-sample` | 保留指定样例的标程输出，例如 `--keep 1 --keep 2`。 |
| `--external-id` | 覆盖 external ID，默认使用 Polygon 题目简称。 |
| `--with-statement` | 包含 PDF 题面。 |
| `--with-attachments` | 包含附件，例如交互题本地测试工具。 |
| `--testset` | 选择测试集；存在多个测试集时必填。 |
| `-l`, `--log-level` | 日志级别，默认为 `info`。 |
| `-v`, `--version` | 输出版本信息。 |

提供给选手下载的样例优先使用题面中的输出。题面输出为占位符时可用 `--keep` 保留标程输出；该选项对隐藏样例无效。

`p2d-contest contest.xml` 列出 Polygon 比赛元数据中的题目编号和名称。

## 配置

语言偏好、标准 checker 参数和题解标签见 [config.example.toml](config.example.toml)。可以通过 `TESTLIB_PATH` 指定另一个包含 `testlib.h` 的目录。

题解标签使用 `permitted` 和 `required` 配置预期结果：

```toml
[tag]
main = { permitted = ["AC"] }
wrong-answer = { permitted = ["AC", "WA"], required = ["WA"] }
time-limit-exceeded-or-accepted = { permitted = ["AC", "TLE"] }
rejected = { required = ["RTE", "TLE", "WA"] }
```

`permitted` 指定每个测试允许的结果；`required` 要求至少一个测试出现列表中的任意一种结果。省略任意字段时，其默认值为 `["AC", "WA", "TLE", "RTE"]`。

自定义 `tag` 表会替换默认映射，请包含所需的全部标签。旧的列表式配置需要改为上述格式，`--legacy` 也一样；旧格式无法表达的规则会报错。

## 兼容性

- 默认导出需要 DOMjudge 支持 [2025-09 题解元数据](https://github.com/DOMjudge/domjudge/pull/3833)，要求 Polygon 题目包含 URL。
- 自定义校验器放入 `output_validator/`。题解规则使用标准目录或 `submissions/submissions.yaml`，保留源码原文；已有的 `@EXPECTED_RESULTS@` 和 `@EXPECTED_SCORE@` 注释仍会影响判题。
- 交互器必须自行验证选手输出；DOMjudge 不会额外运行 checker 检查 `tout`。
- multi-pass 转换为实验功能，支持两轮。C++ 交互器使用 `-DDOMJUDGE` 编译；需要下一轮时，在反馈目录写入 `nextpass.in`，并以 42 退出：

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

使用 `DomjudgeOptions(legacy=True)` 导出旧格式。API 可能变化。

## 开发

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
