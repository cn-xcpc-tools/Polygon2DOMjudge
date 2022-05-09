# Polygon2Domjudge

## 这是什么
这是一个简单的将 polygon 题目包转换成 domjudge (kattis) 题目包的 python 脚本。

## 命令行使用示例
```bash
# 首先把你的 polygon-package 解压到 /path/to/polygon-package 位置 
$ ./bin/p2d --code A --color FF0000 -o /path/to/domjudge-package /path/to/polygon-package
```
运行此命令可以从 `/path/to/polygon-package` 处的转换题目包为 `/path/to/domjudge-package.zip`，并设置  `probcode` 和 `color` 属性。

## 配置
在 [config.json](config.json) 文件中，你可以设置一些特殊的 checker 的输出校验器参数，并手动添加一些。

你可以在命令行中使用 `--default` 参数，并添加自定义的参数，来强制使用 DOMJudge 默认的输出校验器。

你可以在命令行中使用 `--auto` 参数来使用 DOMJudge 默认的输出校验器，如果 checker 在配置文件中被定义，能默认的输出校验器所替代。

## 环境变量
某些时候可能会有用。但如果你不知道你在干啥，请不要随便修改。

- `CONFIG_PATH`
- `TESTLIB_PATH`
- `EXTENTION_FOR_DESC`

## API 使用示例

```python
import tempfile

from p2d import Polygon2Domjudge

package_dir = '/path/to/polygon-package'
output_file = '/path/to/domjudge-package.zip'

with tempfile.TemporaryDirectory() as temp_dir:
    try:
        Polygon2Domjudge(package_dir, temp_dir, output_file).process()
    except Exception as e:
        # do something
        pass
```
