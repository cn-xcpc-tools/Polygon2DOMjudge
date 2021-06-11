# Polygon2Domjudge
## What is this
It is a simple python script converting polygon package to domjudge(kattis) package.

## How to use it
```bash
# Unzip your polygon-package to /path/to/polygon-package first
$ ./bin/p2d --code A --num-samples 2 --color FF0000 -o /path/to/domjudge-package /path/to/polygon-package
```
Run this command to make a package from `/path/to/polygon-package` to `/path/to/domjudge-package.zip` and set `probcode` and `color`.

## Config
In [config.json](config.json), you can change some special checker's validator's flag or add some checker configs manually.

You can use `--default` to force use the default output validator, and add some flags by command line.

You can use `--custom` to force use the custom output validator even if it can be replaced by the default one. 

## Environment Variable
Don't change them unless you know what you are doing.
- `CONFIG_PATH`
- `TESTLIB_PATH`
- `EXTENTION_FOR_DESC`
