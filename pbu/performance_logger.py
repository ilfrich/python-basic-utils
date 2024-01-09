import uuid
from statistics import mean
from time import time
from datetime import datetime, timedelta
from logging import Logger


class PerformanceLogger:
    def __init__(self, logger=None):
        self.start_time = datetime.now()
        self.last_checkpoint = None
        self.logger = logger

    def start(self):
        self.start_time = datetime.now()

    def checkpoint(self, message: str = None, logger: Logger = None):
        start_time = self.last_checkpoint if self.last_checkpoint is not None else self.start_time
        now = datetime.now()
        duration = now - start_time
        PerformanceLogger._log_message(duration, message, logger if self.logger is None else self.logger)
        self.last_checkpoint = now

    def finish(self, message: str = None, logger: Logger = None):
        duration = datetime.now() - self.start_time
        PerformanceLogger._log_message(duration, message, logger if self.logger is None else self.logger)

    @staticmethod
    def _log_message(duration: timedelta, message: str = None, logger: Logger = None):
        if message is None:
            return

        print_string = f"{message} took {duration}"
        if logger is not None:
            logger.info(print_string)
        else:
            print(print_string)

    def get_total_runtime(self) -> timedelta:
        return datetime.now() - self.start_time

    def get_runtime(self) -> timedelta:
        return datetime.now() - self.last_checkpoint if self.last_checkpoint is not None else self.start_time


class PerformanceTracker:
    def __init__(self, operation_name: str, print_interval=60, logger=None):
        self.operation_name = operation_name
        self.print_interval = print_interval
        self.logger = logger
        self.performance_stats = []
        self.start_times = {}

    def _generate_unique_key(self):
        key = str(uuid.uuid4())
        if key in self.start_times:
            return self._generate_unique_key()
        return key

    def start_operation(self) -> str:
        key = self._generate_unique_key()
        start_time = time()
        self.start_times[key] = start_time
        return key

    def end_operation(self, key: str = None):
        if key is None:
            raise ValueError("'key' parameter cannot be none")
        if key not in self.start_times:
            raise ValueError(f"Unknown key: '{key}'")

        duration = time() - self.start_times[key]
        self.performance_stats.append(duration)
        if len(self.performance_stats) % self.print_interval == 0:
            self.print_stats()

    def print_stats(self):
        if len(self.performance_stats) == 0:
            return

        message = f"Performance for operation '{self.operation_name}' ({len(self.performance_stats)}): " \
                  f"Avg: {mean(self.performance_stats)} | " \
                  f"Min: {min(self.performance_stats)} | " \
                  f"Max: {max(self.performance_stats)}"
        if self.logger is not None:
            self.logger.info(message)
        else:
            print(message)
