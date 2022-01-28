import os
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any, Hashable, List, NamedTuple, Sequence, Union

from fs.base import FS
from fs.osfs import OSFS
import jinja2
from jinja2 import nativetypes

Template = jinja2.Environment(
    variable_start_string="{",
    variable_end_string="}",
    finalize=lambda x: x() if callable(x) else x,
    autoescape=False,
)

NativeTemplate = nativetypes.NativeEnvironment(
    variable_start_string="{",
    variable_end_string="}",
    finalize=lambda x: x() if callable(x) else x,
    autoescape=False,
)


def is_same_resource(fs1, path1, fs2, path2):
    from fs.zipfs import WriteZipFS, ReadZipFS
    from fs.tarfs import WriteTarFS, ReadTarFS
    from fs.errors import NoSysPath, NoURL

    try:
        return fs1.getsyspath(path1) == fs2.getsyspath(path2)
    except NoSysPath:
        pass
    if isinstance(fs1, fs2.__class__):
        try:
            return fs1.geturl(path1) == fs2.geturl(path2)
        except NoURL:
            pass
        if isinstance(fs1, (WriteZipFS, ReadZipFS, WriteTarFS, ReadTarFS)):
            return path1 == path2 and fs1._file == fs2._file
    return False


def resource_description(fs, path):
    if isinstance(fs, OSFS):
        return fs.getsyspath(path)
    elif path == "/":
        return str(fs)
    return "{} on {}".format(path, fs)


def fullpath(path: Union[str, Path]) -> Path:
    """Expand '~' and resolve the given path. Path can be a string or a Path obj."""
    return Path(os.path.expandvars(str(path))).expanduser().resolve(strict=False)


def ensure_list(inp):
    if not isinstance(inp, list):
        return [inp]
    return inp


def flatten(arr: List[Any]) -> List[Any]:
    if arr == []:
        return []
    if not isinstance(arr, list):
        return [arr]
    return flatten(arr[0]) + flatten(arr[1:])


def flattened_string_list(x, case_sensitive=True) -> Sequence[str]:
    x = [str(x) for x in flatten(x)]
    if not case_sensitive:
        x = [x.lower() for x in x]
    return x


def first_key(dic: Mapping) -> Hashable:
    return list(dic.keys())[0]


def deep_merge(a: dict, b: dict) -> dict:
    result = deepcopy(a)
    for bk, bv in b.items():
        av = result.get(bk)
        if isinstance(av, dict) and isinstance(bv, dict):
            result[bk] = deep_merge(av, bv)
        else:
            result[bk] = deepcopy(bv)
    return result


def deep_merge_inplace(base: dict, updates: dict) -> None:
    for bk, bv in updates.items():
        av = base.get(bk)
        if isinstance(av, dict) and isinstance(bv, dict):
            deep_merge_inplace(av, bv)
        else:
            base[bk] = bv


def next_free_name(fs: FS, template: jinja2.Template, name: str, extension: str) -> str:
    """
    Increments {counter} in the template until the given resource does not exist.

    Args:
        fs (FS): the filesystem to work on
        template (jinja2.Template):
            A jinja2 template with placeholders for {name}, {extension} and {counter}
        name (str): The wanted filename
        extension (str): the wanted extension

    Raises:
        ValueError if no free name can be found with the given template.

    Returns:
        (str) A filename according to the given template that does not exist on **fs**.
    """
    counter = 1
    prev_candidate = ""
    while True:
        candidate = template.render(name=name, extension=extension, counter=counter)
        if not fs.exists(candidate):
            return candidate
        if prev_candidate == candidate:
            raise ValueError(
                "Could not find a free filename for the given template. "
                'Maybe you forgot the "{counter}" placeholder?'
            )
        prev_candidate = candidate
        counter += 1
