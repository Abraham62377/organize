import logging
import os
from collections import Counter
from datetime import datetime
from typing import Iterable, NamedTuple

import fs
from fs.base import FS
from fs.walk import Walker
from schema import SchemaError

from . import output
from .actions import ACTIONS
from .actions.action import Action
from .config import CONFIG_SCHEMA, load_from_file
from .filters import FILTERS
from .filters.filter import Filter
from .output import console
from .utils import Template, deep_merge_inplace, ensure_list

logger = logging.getLogger(__name__)


class Location(NamedTuple):
    walker: Walker
    base_fs: FS
    path: str


DEFAULT_SYSTEM_EXCLUDE_FILES = [
    "thumbs.db",
    "desktop.ini",
    "~$*",
    ".DS_Store",
    ".localized",
]

DEFAULT_SYSTEM_EXCLUDE_DIRS = [
    ".git",
    ".svn",
]


def walker_args_from_location_options(options):
    # combine system_exclude and exclude into a single list
    excludes = options.get("system_exlude_files", DEFAULT_SYSTEM_EXCLUDE_FILES)
    excludes.extend(options.get("exclude_files", []))
    exclude_dirs = options.get("system_exclude_dirs", DEFAULT_SYSTEM_EXCLUDE_DIRS)
    exclude_dirs.extend(options.get("exclude_dirs", []))
    # return all the default options
    return {
        "ignore_errors": options.get("ignore_errors", False),
        "on_error": options.get("on_error", None),
        "search": options.get("search", "depth"),
        "exclude": excludes,
        "exclude_dirs": exclude_dirs,
        "max_depth": options.get("max_depth", None),
        "filter": None,
        "filter_dirs": None,
    }


def instantiate_location(loc) -> Location:
    if isinstance(loc, str):
        loc = {"path": loc}

    if "walker" not in loc:
        args = walker_args_from_location_options(loc)
        walker = Walker(**args)
    else:
        walker = loc["walker"]

    if "filesystem" in loc:
        base_fs = loc["filesystem"]
        path = loc.get("path", "/")
    else:
        base_fs = loc["path"]
        path = "/"

    return Location(
        walker=walker,
        base_fs=fs.open_fs(Template.from_string(base_fs).render(env=os.environ)),
        path=Template.from_string(path).render(env=os.environ),
    )


def instantiate_by_name(d, classes):
    if isinstance(d, str):
        return classes[d]()
    key, value = list(d.items())[0]
    if isinstance(key, str):
        Class = classes[key]
        if isinstance(value, dict):
            return Class(**value)
        return Class(value)
    return d


def replace_with_instances(config):
    warnings = []

    for rule in config["rules"]:
        locations = []

        for loc in ensure_list(rule["locations"]):
            try:
                instance = instantiate_location(loc)
                locations.append(instance)
            except Exception as e:
                if loc.get("ignore_errors", False):
                    warnings.append(str(e))
                else:
                    raise e

        rule["locations"] = locations

        # filters are optional
        rule["filters"] = [
            instantiate_by_name(x, FILTERS)
            for x in ensure_list(rule.get("filters", []))
        ]
        rule["actions"] = [
            instantiate_by_name(x, ACTIONS) for x in ensure_list(rule["actions"])
        ]

    return warnings


def filter_pipeline(filters: Iterable[Filter], args: dict) -> bool:
    """
    run the filter pipeline.
    Returns True on a match, False otherwise and updates `args` in the process.
    """
    for filter_ in filters:
        try:
            match, updates = filter_.pipeline(args)
            if not match:
                return False
            deep_merge_inplace(args, updates)
        except Exception as e:  # pylint: disable=broad-except
            logger.exception(e)
            # console.print_exception()
            filter_.print_error(e)
            return False
    return True


def action_pipeline(actions: Iterable[Action], args: dict, simulate: bool) -> bool:
    for action in actions:
        try:
            updates = action.pipeline(args, simulate=simulate)
            # jobs may return a dict with updates that should be merged into args
            if updates is not None:
                deep_merge_inplace(args, updates)
        except Exception as e:  # pylint: disable=broad-except
            logger.exception(e)
            action.print_error(e)
            return False
    return True


def run(config, simulate: bool = True):
    count = Counter(done=0, fail=0)

    if simulate:
        output.simulation_banner()

    for rule in config["rules"]:
        target = rule.get("targets", "files")
        output.rule(rule["name"])

        with output.spinner(simulate=simulate):
            for walker, base_fs, base_path in rule["locations"]:
                output.location(base_fs, base_path)
                walk = walker.files if target == "files" else walker.dirs
                for path in walk(fs=base_fs, path=base_path):
                    output.path(base_fs, path)
                    relative_path = fs.path.relativefrom(base_path, path)
                    args = {
                        "fs": base_fs,
                        "fs_path": path,
                        "relative_path": relative_path,
                        "env": os.environ,
                        "now": datetime.now(),
                        "utcnow": datetime.utcnow(),
                        "path": lambda: base_fs.getsyspath(path),
                    }
                    match = filter_pipeline(
                        filters=rule["filters"],
                        args=args,
                    )
                    if match:
                        is_success = action_pipeline(
                            actions=rule["actions"],
                            args=args,
                            simulate=simulate,
                        )
                        if is_success:
                            count["done"] += 1
                        else:
                            count["fail"] += 1

    if simulate:
        output.simulation_banner()

    return count


def run_file(config_file: str, working_dir: str, simulate: bool):
    output.info(config_file, working_dir)
    try:
        rules = load_from_file(config_file)
        CONFIG_SCHEMA.validate(rules)
        warnings = replace_with_instances(rules)
        for msg in warnings:
            output.print_warning(msg)
        os.chdir(working_dir)
        count = run(rules, simulate=simulate)
        output.summary(count)
    except SchemaError as e:
        console.print("Invalid config file")
        console.print(e.autos[-1])
    except Exception as e:
        console.print_exception()
