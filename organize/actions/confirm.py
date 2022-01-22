import logging

from rich.prompt import Prompt
from ..tui import console
from .action import Action

logger = logging.getLogger(__name__)


class Confirm(Action):
    def __init__(self, msg, default):
        self.msg = msg
        self.default = default
        self.prompt = Prompt(console=console)

    def pipeline(self, args: dict, simulate: bool):
        self.print("asd")
        chosen = self.prompt.ask("", default=self.default)
        self.print(chosen)

    def __str__(self) -> str:
        return 'Echo(msg="%s")' % self.msg

    name = "confirm"
