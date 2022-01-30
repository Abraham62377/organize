import logging
import os
from typing import Callable

from fs import path
from fs.base import FS
from fs.move import move_dir, move_file
from schema import Optional, Or

from organize.utils import Template, resource_description

from .action import Action
from .utils import CONFLICT_OPTIONS, resolve_overwrite_conflict

logger = logging.getLogger(__name__)


class Rename(Action):

    """Renames a file.

    Args:
        name (str):
            The new name for the file / dir.

        on_conflict (str):
            What should happen in case **dest** already exists.
            One of `skip`, `overwrite`, `trash`, `rename_new` and `rename_existing`.
            Defaults to `rename_new`.

        rename_template (str):
            A template for renaming the file / dir in case of a conflict.
            Defaults to `{name} {counter}{extension}`.

        dest_filesystem (str):
            (Optional) A pyfilesystem opener url of the filesystem you want to copy to.
            If this is not given, the local filesystem is used.

    The next action will work with the renamed file / dir.
    """

    name = "rename"
    arg_schema = Or(
        str,
        {
            "name": str,
            Optional("on_conflict"): Or(*CONFLICT_OPTIONS),
            Optional("rename_template"): str,
        },
    )

    def __init__(
        self,
        name: str,
        on_conflict="rename_new",
        rename_template="{name} {counter}{extension}",
    ) -> None:
        if on_conflict not in CONFLICT_OPTIONS:
            raise ValueError(
                "on_conflict must be one of %s" % ", ".join(CONFLICT_OPTIONS)
            )

        self.new_name = Template.from_string(name)
        self.conflict_mode = on_conflict
        self.rename_template = Template.from_string(rename_template)

    def pipeline(self, args: dict, simulate: bool):
        fs = args["fs"]  # type: FS
        src_path = args["fs_path"]

        new_name = self.new_name.render(**args)
        if os.path.sep in new_name:
            ValueError(
                "Rename only takes a name as argument. "
                "To move files or folders use the move action."
            )

        parents, full_name = path.split(src_path)
        name, ext = path.splitext(full_name)
        dst_path = path.join(parents, new_name)

        if dst_path == src_path:
            self.print("Name did not change")
        else:
            move_action: Callable[[FS, str, FS, str], None]
            if fs.isdir(src_path):
                move_action = move_dir
            elif fs.isfile(src_path):
                move_action = move_file

            skip = False
            if fs.exists(dst_path):
                self.print(
                    '%s already exists (conflict mode is "%s").'
                    % (resource_description(fs, dst_path), self.conflict_mode)
                )
                fs, dst_path, skip = resolve_overwrite_conflict(
                    dst_fs=fs,
                    dst_path=dst_path,
                    conflict_mode=self.conflict_mode,
                    rename_template=self.rename_template,
                    simulate=simulate,
                    print=self.print,
                )
            if not skip:
                if not simulate:
                    move_action(fs, src_path, fs, dst_path)
                self.print("Renamed to %s" % resource_description(fs, dst_path))

        # the next action should work with the newly created copy
        return {
            "fs": fs,
            "fs_path": dst_path,
        }

    def __str__(self) -> str:
        return "Rename(new_name=%s, conflict_mode=%s)" % (
            self.new_name,
            self.conflict_mode,
        )
