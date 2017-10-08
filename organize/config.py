import logging
from typing import List
from collections import namedtuple
from organize import actions, filters

logger = logging.getLogger(__name__)
Rule = namedtuple('Rule', 'filters actions folders')


def first_key(d):
    return list(d.keys())[0]


def flatten(arr):
    if arr == []:
        return []
    if not isinstance(arr, list):
        return [arr]
    return flatten(arr[0]) + flatten(arr[1:])


class Config:

    def __init__(self, config: dict):
        self.config = config

    @classmethod
    def from_string(cls, config: str):
        import yaml
        return cls(yaml.load(config))

    @classmethod
    def from_file(cls, path):
        with open(path, 'r') as f:
            return cls.from_string(f.read())

    @staticmethod
    def parse_folders(rule_item):
        # the folder list is flattened so we can use encapsulated list
        # definitions in the config file.
        yield from flatten(rule_item['folders'])

    def _get_filter_class_by_name(self, name):
        try:
            return getattr(filters, name)
        except AttributeError as e:
            raise self.Error('%s is no valid filter' % name) from e

    def _get_action_class_by_name(self, name):
        try:
            return getattr(actions, name)
        except AttributeError as e:
            raise self.Error('%s is no valid filter' % name) from e

    @staticmethod
    def _class_instance_with_args(Cls, args):
        if args is None:
            return Cls()
        elif isinstance(args, list):
            return Cls(*args)
        elif isinstance(args, dict):
            return Cls(**args)
        return Cls(args)

    def instantiate_filters(self, rule_item):
        for filter_item in rule_item['filters']:
            # filter with arguments
            if isinstance(filter_item, dict):
                name = first_key(filter_item)
                args = filter_item[name]
                filter_class = self._get_filter_class_by_name(name)
                yield self._class_instance_with_args(filter_class, args)
            # only given filter name without args
            elif isinstance(filter_item, str):
                name = filter_item
                filter_class = self._get_filter_class_by_name(name)
                yield filter_class()
            else:
                raise self.Error('Unknown filter type: %s' % filter_item)

    def instantiate_actions(self, rule_item):
        for action_item in rule_item['actions']:
            if isinstance(action_item, dict):
                name = first_key(action_item)
                args = action_item[name]
                action_class = self._get_action_class_by_name(name)
                yield self._class_instance_with_args(action_class, args)
            elif isinstance(action_item, str):
                name = action_item
                action_class = self._get_action_class_by_name(name)
                yield action_class()
            else:
                raise self.Error('Unknown action type: %s' % action_item)

    @property
    def rules(self) -> List[Rule]:
        """:returns: A list of instantiated Rules
        """
        result = []
        for i, rule_item in enumerate(self.config['rules']):
            rule_folders = list(self.parse_folders(rule_item))
            rule_filters = list(self.instantiate_filters(rule_item))
            rule_actions = list(self.instantiate_actions(rule_item))

            if not rule_folders:
                logger.warning('No folders given for rule %s!', i + 1)
            if not rule_filters:
                logger.warning('No filters given for rule %s!', i + 1)
            if not rule_actions:
                logger.warning('No actions given for rule %s!', i + 1)

            rule = Rule(
                folders=rule_folders,
                filters=rule_filters,
                actions=rule_actions)
            result.append(rule)
        return result

    class Error(Exception):
        pass
