# Polygon2Domjudge

[中文](README.cn.md)

## What is this
It is a simple python script converting polygon package to domjudge(kattis) package.

## CLI Example
```bash
# Unzip your polygon-package to /path/to/polygon-package first
$ ./bin/p2d --code A --color FF0000 -o /path/to/domjudge-package /path/to/polygon-package
```
Run this command to make a package from `/path/to/polygon-package` to `/path/to/domjudge-package.zip` and set `probcode` and `color`.

## Config
In [config.json](config.json), you can change some special checker's validator's flag or add some checker configs manually.

You can use `--default` to force use the default output validator, and add some flags by command line.

You can use `--auto` to use the default output validator if the checker is defined in config and can be replaced by the default one. 

## Environment Variable
Don't change them unless you know what you are doing.

- `CONFIG_PATH`
- `TESTLIB_PATH`
- `EXTENTION_FOR_DESC`

## API Example

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
