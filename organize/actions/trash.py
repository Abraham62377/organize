import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class Trash:

    """
    Move a file into the trash.

    Example:
        - Move all JPGs and PNGs on the desktop which are older than one year
          into the trash:

          .. code-block:: yaml

              rules:
              - folders: '~/Desktop'
              - filters:
                  - OlderThan: {years: 1}
                  - FileExtension:
                      - png
                      - jpg
              - actions:
                  - Trash
    """

    def run(self, path: Path, file_attributes: dict, simulate: bool):
        from send2trash import send2trash
        logger.info('Trashing "%s"', path)
        if not simulate:
            send2trash(path)
