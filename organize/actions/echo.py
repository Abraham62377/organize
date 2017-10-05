import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class Echo:

    """
    Prints the given (formatted) message. This can be useful to test your rules,
    especially if you use formatted messages.

    :param str msg: The message to print (can be formatted)

    Example:
        - This will print something like ``Found a PNG: "test.png"`` for each
          file on your desktop:

        .. code-block:: yaml

            rules:
              - folders:
                  - '~/Desktop'
                filters:
                  - FileExtension
                actions:
                  - Echo: {msg: 'Found a {extension.upper}: "{path.name}"'}
    """

    def __init__(self, msg):
        self.msg = msg

    def run(self, path: Path, file_attributes: dict, simulate: bool):
        full_msg = self.msg.format(path=path, **file_attributes)
        print(full_msg)

    def __str__(self):
        return 'Echo(msg="%s")' % self.msg

    def __repr__(self):
        return '<' + str(self) + '>'
