# Polygon2Domjudge
## What is this
It is a simple python script converting polygon package to domjudge(kattis) package.

## How to use it
```bash
$ ./p2d.py --code A --num-samples 2 --color FF0000 -o /path/to/domjudge-package /path/to/polygon-package
```
Run this command to make a package from `/path/to/polygon-package` to `/path/to/domjudge-package.zip` and set `probcode`, `num-samples` and `color`.

## Config
In [config.json](config.json), you can change some special checker's validator's flag or add some checker configs manually.

Also you can use `--default` to force use the default output validator, and add some flags by command line.

## Environment Variable
Don't change them unless you know what you are doing.
- `CONFIG_PATH` : `config.json`
- `TESTLIB_PATH`: `../testlib.h`
- `TMP_DIR`: `tmp`
- `EXTENTION_FOR_OUTPUT`: `.out`
- `EXTENTION_FOR_DESC`: `desc`
