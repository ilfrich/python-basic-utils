from datetime import datetime, timedelta
from logging import Logger


class PerformanceLogger:
    def __init__(self):
        self.start_time = datetime.now()
        self.last_checkpoint = None

    def start(self):
        self.start_time = datetime.now()

    def checkpoint(self, message: str = None, logger: Logger = None):
        start_time = self.last_checkpoint if self.last_checkpoint is not None else self.start_time
        now = datetime.now()
        duration = now - start_time
        PerformanceLogger._log_message(duration, message, logger)
        self.last_checkpoint = now

    def finish(self, message: str = None, logger: Logger = None):
        duration = datetime.now() - self.start_time
        PerformanceLogger._log_message(duration, message, logger)

    @staticmethod
    def _log_message(duration: timedelta, message: str = None, logger: Logger = None):
        if message is None:
            return

        print_string = f"{message} took {duration}"
        if logger is not None:
            logger.info(print_string)
        else:
            print(print_string)
