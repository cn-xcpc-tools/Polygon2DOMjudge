import collections
import shutil

import tomli

from pathlib import Path
from typing import Union


def ensure_dir(s: Path):
    if not s.exists():
        s.mkdir(parents=True)


def ensure_no_dir(s: Path):
    if s.exists():
        shutil.rmtree(s)


def load_config(config_file: Union[str, Path]):
    try:
        with open(config_file, 'r') as f:
            return tomli.loads(f.read())
    except FileNotFoundError:
        raise ImportError('\'config.toml\' not found!')
    except tomli.TOMLDecodeError:
        raise ImportError('\'config.toml\' is not a valid TOML file!')


def update_dict(orig, update, add_keys=True):
    """Deep update of a dictionary

    For each entry (k, v) in update such that both orig[k] and v are
    dictionaries, orig[k] is recurisvely updated to v.

    For all other entries (k, v), orig[k] is set to v.
    """
    for (key, value) in update.items():
        if key in orig and \
                isinstance(value, collections.abc.Mapping) and \
                isinstance(orig[key], collections.abc.Mapping):
            update_dict(orig[key], value)
        elif add_keys or key in orig:
            orig[key] = value
