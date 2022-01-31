import logging
import os
from collections import Counter, defaultdict
from datetime import datetime
from typing import Iterable, NamedTuple

import fs
from fs.errors import NoSysPath
from fs.base import FS
from fs.walk import Walker
from rich.console import Console
from schema import SchemaError

from . import console
from .actions import ACTIONS
from .actions.action import Action
from .config import CONFIG_SCHEMA, load_from_file
from .filters import FILTERS
from .filters.filter import Filter
from .utils import (
    Template,
    deep_merge_inplace,
    ensure_list,
    ensure_dict,
    to_args,
    flatten_all_lists_in_dict,
)

logger = logging.getLogger(__name__)
highlighted_console = Console()


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


def config_cleanup(rules):
    result = defaultdict(list)

    # delete every root key except "rules"
    for rule in rules.get("rules", []):
        # delete disabled rules
        if rule.get("enabled", True):
            result["rules"].append(rule)

    # flatten all lists everywhere
    return flatten_all_lists_in_dict(dict(result))


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


def instantiate_location(loc, default_max_depth=0) -> Location:
    if isinstance(loc, str):
        loc = {"path": loc}

    # set default max depth from rule
    if not "max_depth" in loc:
        loc["max_depth"] = default_max_depth

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


def instantiate_filter(filter_config):
    spec = ensure_dict(filter_config)
    name, value = next(iter(spec.items()))
    parts = name.split(maxsplit=1)
    invert = False
    if len(parts) == 2 and parts[0] == "not":
        name = parts[1]
        invert = True
    args, kwargs = to_args(value)
    instance = FILTERS[name](*args, **kwargs)
    instance.set_logic(inverted=invert)
    return instance


def instantiate_action(action_config):
    spec = ensure_dict(action_config)
    name, value = next(iter(spec.items()))
    args, kwargs = to_args(value)
    return ACTIONS[name](*args, **kwargs)


def syspath_or_exception(fs, path):
    try:
        return fs.getsyspath(path)
    except NoSysPath as e:
        return e


def replace_with_instances(config):
    warnings = []

    for rule in config["rules"]:
        _locations = []
        default_depth = None if rule.get("subfolders", False) else 0

        for loc in ensure_list(rule["locations"]):
            try:
                instance = instantiate_location(loc, default_max_depth=default_depth)
                _locations.append(instance)
            except Exception as e:
                if isinstance(loc, dict) and loc.get("ignore_errors", False):
                    warnings.append(str(e))
                else:
                    raise ValueError("Invalid location %s" % loc) from e

        # filters are optional
        _filters = []
        for x in ensure_list(rule.get("filters", [])):
            try:
                _filters.append(instantiate_filter(x))
            except Exception as e:
                raise ValueError("Invalid filter %s (%s)" % (x, e)) from e

        # actions
        _actions = []
        for x in ensure_list(rule["actions"]):
            try:
                _actions.append(instantiate_action(x))
            except Exception as e:
                raise ValueError("Invalid action %s (%s)" % (x, e)) from e

        rule["locations"] = _locations
        rule["filters"] = _filters
        rule["actions"] = _actions

    return warnings


def filter_pipeline(filters: Iterable[Filter], args: dict, filter_mode: str) -> bool:
    """
    run the filter pipeline.
    Returns True on a match, False otherwise and updates `args` in the process.
    """
    results = []
    for filter_ in filters:
        try:
            match, updates = filter_.pipeline(args)
            result = match ^ filter_.inverted
            # we cannot exit early on "any".
            if (filter_mode == "none" and result) or (
                filter_mode == "all" and not result
            ):
                return False
            results.append(result)
            deep_merge_inplace(args, updates)
        except Exception as e:  # pylint: disable=broad-except
            logger.exception(e)
            # console.print_exception()
            filter_.print_error(str(e))
            return False

    if filter_mode == "any":
        return any(results)
    return True


def action_pipeline(actions: Iterable[Action], args: dict, simulate: bool) -> bool:
    for action in actions:
        try:
            # update path
            args["path"] = syspath_or_exception(args["fs"], args["fs_path"])
            updates = action.pipeline(args, simulate=simulate)
            # jobs may return a dict with updates that should be merged into args
            if updates is not None:
                deep_merge_inplace(args, updates)
        except Exception as e:  # pylint: disable=broad-except
            # logger.exception(e)
            action.print_error(str(e))
            return False
    return True


def run(config, simulate: bool = True):
    count = Counter(done=0, fail=0)  # type: Counter

    if simulate:
        console.simulation_banner()

    console.spinner(simulate=simulate)
    for rule_nr, rule in enumerate(config["rules"], start=1):
        target = rule.get("targets", "files")
        console.rule(rule.get("name", "Rule %s" % rule_nr))
        filter_mode = rule.get("filter_mode", "all")

        for walker, base_fs, base_path in rule["locations"]:
            console.location(base_fs, base_path)
            walk = walker.files if target == "files" else walker.dirs
            for path in walk(fs=base_fs, path=base_path):
                console.path(base_fs, path)
                relative_path = fs.path.relativefrom(base_path, path)
                args = {
                    "fs": base_fs,
                    "fs_path": path,
                    "relative_path": relative_path,
                    "env": os.environ,
                    "now": datetime.now(),
                    "utcnow": datetime.utcnow(),
                    "path": syspath_or_exception(base_fs, path),
                }
                match = filter_pipeline(
                    filters=rule["filters"],
                    args=args,
                    filter_mode=filter_mode,
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
        console.simulation_banner()

    return count


def run_file(config_file: str, working_dir: str, simulate: bool):
    console.info(config_file, working_dir)
    try:
        rules = load_from_file(config_file)
        rules = config_cleanup(rules)
        CONFIG_SCHEMA.validate(rules)
        warnings = replace_with_instances(rules)
        for msg in warnings:
            console.warn(msg)
        os.chdir(working_dir)
        count = run(rules, simulate=simulate)
        console.summary(count)
    except SchemaError as e:
        console.error("Invalid config file!")
        for err in e.autos:
            if err:
                highlighted_console.print(err)
    except Exception as e:
        highlighted_console.print_exception()
