from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal, Optional, Union

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm as RichConfirm
from rich.status import Status
from rich.theme import Theme

from organize.utils import ChangeDetector

if TYPE_CHECKING:
    from organize.action import Action
    from organize.filter import Filter
    from organize.resource import Resource

    SenderType = Union[Filter, Action, str]


def _highlight_path(path: Path, base_style: str, main_style: str) -> str:
    base = str(f"{path.parent}/")
    main = str(path.name)
    return f"[{base_style}]{base}[/][{main_style}]{main}[/]"


def _pipeline_source(source: SenderType) -> str:
    if hasattr(source, "filter_config"):
        src = source.filter_config.name
    elif hasattr(source, "action_config"):
        src = source.action_config.name
    else:
        src = str(source)
    return f"    - ([pipeline.source]{src}[/]) "


def pipeline_message(source: SenderType, msg: str) -> str:
    pre = _pipeline_source(source)
    return f"{pre}[pipeline.msg]{msg}[/]"


def pipeline_error(source: SenderType, msg: str) -> str:
    src = _pipeline_source(source)
    return f"{src}[pipeline.error]ERROR! {msg}[/]"


class Confirm(RichConfirm):
    @classmethod
    def set_source(cls, source: SenderType) -> None:
        src = _pipeline_source(source)
        err_msg = f"{src}[prompt.invalid]Please enter Y or N[/]"
        cls.validate_error_message = err_msg


class Default:
    def __init__(self, theme: Optional[Theme] = None):
        if theme is None:
            theme = Theme(
                {
                    "info": "dim cyan",
                    "warning": "yellow",
                    "error": "bold red",
                    "simulation": "bold green",
                    "status": "bold green",
                    "rule": "bold cyan",
                    "location.base": "green",
                    "location.main": "bold green",
                    "path.base": "dim green",
                    "path.main": "green",
                    "pipeline.source": "cyan",
                    "pipeline.msg": "",
                    "pipeline.error": "bold red",
                    "pipeline.prompt": "bold yellow",
                    "summary.done": "bold green",
                    "summary.fail": "red",
                }
            )
        self.console = Console(theme=theme, highlight=False)

        self.status = Status("", console=self.console)
        self.det_rule = ChangeDetector()
        self.det_location = ChangeDetector()
        self.det_path = ChangeDetector()
        self.simulate = False

    def show_resource(self, res: Resource):
        # rule changed
        if self.det_rule.changed(res.rule):
            self.det_location.reset()
            self.det_path.reset()
            self.console.print()
            rule_name = f"Rule #{res.rule_nr}"
            if res.rule is not None and res.rule.name is not None:
                rule_name += f": {res.rule.name}"
            self.console.rule(f"[rule]:gear: {rule_name}", align="left", style="rule")

        # location changed
        if self.det_location.changed(res.basedir):
            self.det_path.reset()
            if res.basedir:
                path_str = _highlight_path(
                    Path(res.basedir),
                    "location.base",
                    "location.main",
                )
                self.console.print(path_str)
            else:
                self.console.print("* standalone *")

        # path changed
        if self.det_path.changed(res.path):
            if res.path:
                path_str = _highlight_path(
                    Path(res.relative_path()),
                    "path.base",
                    "path.main",
                )
                self.console.print(f"  {path_str}")
            else:
                self.console.print("  * standalone *")

    def start(self, simulate: bool, config_path: Optional[Path] = None):
        self.det_rule.reset()
        self.det_location.reset()
        self.det_path.reset()

        self.simulate = simulate
        if self.simulate:
            self.console.print(Panel("SIMULATION", style="simulation"))

        if config_path:
            self.console.print(f'Config: "{config_path}"')
        # if working_dir != Path("."):  # TODO
        #     console.print('Working dir: "{}"'.format(working_dir))

        status_verb = "simulating" if simulate else "organizing"
        self.status.update(f"[status]{status_verb}[/]")
        self.status.start()

    def msg(
        self,
        res: Resource,
        msg: str,
        level: Literal["info", "warn", "error"] = "info",
        sender: SenderType = "",
    ):
        self.show_resource(res)
        self.console.print(pipeline_message(source=sender, msg=msg))

    def confirm(
        self,
        res: Resource,
        msg: str,
        default: bool,
        sender: SenderType = "",
    ) -> bool:
        self.status.stop()
        self.show_resource(res)
        src = _pipeline_source(sender)
        Confirm.set_source(sender)
        result = Confirm.ask(
            prompt=f"{src}[pipeline.prompt]{msg}[/]",
            console=self.console,
            default=default,
        )
        self.status.start()
        return result

    def end(self, success_count: int, error_count: int):
        self.status.stop()
        if self.simulate:
            self.console.print(Panel("SIMULATION", style="simulation"))
