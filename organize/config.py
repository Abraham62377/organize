import textwrap

import yaml
from rich.console import Console
from schema import And, Optional, Or, Schema, SchemaError

from organize.actions import ALL as ACTIONS
from organize.filters import ALL as FILTERS

console = Console()

CONFIG_SCHEMA = Schema(
    {
        Optional("version"): int,
        "rules": [
            {
                "name": And(str, len),
                "targets": Or("dirs", "files"),
                "locations": [
                    Or(
                        str,
                        {
                            "path": And(str, len),
                            Optional("filesystem"): str,
                            Optional("max_depth"): Or(int, None),
                            Optional("search"): Or("depth", "breadth"),
                            Optional("exclude_files"): [str],
                            Optional("exclude_dirs"): [str],
                            Optional("system_exlude_files"): [str],
                            Optional("system_exclude_dirs"): [str],
                            Optional("ignore_errors"): bool,
                            Optional("filter"): [str],
                            Optional("filter_dirs"): [str],
                        },
                    ),
                ],
                Optional("filters"): [FILTER.schema() for FILTER in FILTERS.values()],
                "actions": [ACTION.schema() for ACTION in ACTIONS.values()],
            }
        ],
    }
)

# disable yaml constructors for strings starting with exclamation marks
# https://stackoverflow.com/a/13281292/300783
def default_yaml_cnst(loader, tag_suffix, node):
    return str(node.tag)


yaml.add_multi_constructor("", default_yaml_cnst, Loader=yaml.SafeLoader)


def load_from_string(config):
    dedented_config = textwrap.dedent(config)
    return yaml.load(dedented_config, Loader=yaml.SafeLoader)


def load_from_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return load_from_string(f.read())


conf = load_from_file(
    "/Users/thomasfeldmann/Library/Application Support/organize/config.yaml"
)
try:
    CONFIG_SCHEMA.validate(conf)
except SchemaError as e:
    console.print(str(e.autos[-1]))
