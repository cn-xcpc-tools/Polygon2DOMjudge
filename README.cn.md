# Polygon2DOMjudge

[![Test][gh-test-badge]][gh-test]
[![GitHub release][gh-release-badge]][gh-release]

## 这是什么

这是一个简单的将 polygon 题目包转换成 DOMjudge (kattis) 题目包的 python 脚本。

## 安装

```bash
pip install p2d -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

## 命令行使用示例

```bash
# 首先把你的 polygon-package 解压到 /path/to/polygon-package 位置
$ ./bin/p2d --code A --color FF0000 -o /path/to/domjudge-package /path/to/polygon-package
```

运行此命令可以从 `/path/to/polygon-package` 处的转换题目包为 `/path/to/domjudge-package.zip`，并设置  `code` 和 `color` 属性。

所有可用的命令行参数如下：

- `--code`: 题目在 DOMjudge 中的 short name。
- `--color`: 题目在 DOMjudge 中的颜色。
- `--default`: 强制使用 DOMjudge 默认的输出校验器。
- `--validator-flags`: 为输出校验器添加一些命令行参数，仅在 `--default` 被设置时生效。
- `--auto`: 自动使用 DOMjudge 默认的输出校验器，即如果 checker 在配置文件中被定义，则使用默认的输出校验器与合适的命令行参数替代。
- `--memory-limit`: 覆盖 DOMjudge 题目包的内存限制，如果不设置，则使用 Polygon 题目包中的内存限制。
- `--output-limit`: 覆盖 DOMjudge 题目包的输出限制，如果不设置，则使用 DOMjudge 设置中默认的输出限制。
- `--replace-sample`: 替换样例输入输出，如果样例输入输出与题面中的样例输入输出不同，则使用题面中的样例输入输出替换（例如防止样例输出与正确解答的输出不同）。
- `--hide-sample`: 隐藏题面中的样例输入输出，不会为选手提供样例数据（如果是交互题，则此参数强制为 True）。

## 配置

在 [config.toml](./p2d/asset/config.toml) 文件中，你可以设置一些特殊的 checker 的输出校验器参数，这会在 `--auto` 参数被设置时用来将 checker 替换为默认的输出校验器。

> [!NOTE]  
> 你不应该直接编辑这个文件，而是应该创建一个新的文件，命名为 `config.toml` 或其他名称，并使用 `--config` 参数将其传递给脚本。脚本将会合并默认配置和你的配置。

## 环境变量

某些时候可能会有用。但如果你不知道你在干啥，请不要随便修改。

- `CONFIG_PATH`
- `TESTLIB_PATH`
- `EXTENSION_FOR_DESC`

## API 使用示例

```python
import tempfile

from p2d import Polygon2DOMjudge

package_dir = '/path/to/polygon-package'
output_file = '/path/to/domjudge-package' # without '.zip' suffix

with tempfile.TemporaryDirectory() as temp_dir:
    try:
        Polygon2DOMjudge(package_dir, temp_dir, output_file).process()
    except Exception as e:
        # do something
        pass
```

## 开发

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
