from pbu.default_options import list_join


class DebugObject:
    def __init__(self, debug=False, logger=None):
        self._debug = debug
        self._logger = logger

    def debug(self, *kwargs):
        if self._debug:
            if self._logger is not None:
                self._logger.info(list_join(kwargs, " "))
            else:
                print(*kwargs)
