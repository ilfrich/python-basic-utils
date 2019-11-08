import os
import traceback
import requests
import logging
import sys
from logging import handlers
from pbu import JSON

CONFIG_KEY_LOG_SERVER = "PBU_LOG_SERVER"
CONFIG_KEY_LOG_SERVER_AUTH = "PBU_LOG_SERVER_AUTH"
CONFIG_KEY_LOG_FOLDER = "PBU_LOG_FOLDER"

LOG_LEVELS = JSON({
    "ERROR": "ERROR",
    "WARN": "WARN",
    "INFO": "INFO",
    "DEBUG": "DEBUG",
})


class _CustomHttpHandler(logging.Handler):
    def __init__(self, level, url, auth_token=None):
        logging.Handler.__init__(self, level)
        self.url = "{}/api/log".format(url)
        self.auth_token = auth_token

    @staticmethod
    def _map_log_record(record):
        """
        Default implementation of mapping the log record into a dict
        that is sent as the CGI data. Overwrite in your class.
        Contributed by Franz Glasner.
        """
        result = record.__dict__
        if "exc_info" in result and result["exc_info"] is not None:
            for el in result["exc_info"]:
                if isinstance(el, traceback):
                    # print it in the current process, need to serialise the traceback (TODO)
                    el.print_tb()
            # remove this, in case of exception logging, to avoid JSON serialisation issues
            del result["exc_info"]
        return result

    def emit(self, record):
        headers = {
            "Content-Type": "application/json",
        }
        if self.auth_token is not None:
            headers["Authorization"] = self.auth_token
        try:
            requests.post(url=self.url, json=_CustomHttpHandler._map_log_record(record), headers=headers)
        except BaseException as be:
            print("Error sending log message: {}".format(_CustomHttpHandler._map_log_record(record)), file=sys.stderr)


class Logger(logging.Logger):
    """
    File logger for this application, logging into application.log in the configured LOG_FOLDER.
    Usage:

    >>> logger = Logger("some-name")
    >>> logger.info("My message")
    """
    def __init__(self, name, log_folder=None, enable_logger_name=True):
        """
        Creates a new instance of this logger and will store it as a private field, which is exposed via the get()
        method.
        :param name: the name of the class / component, which will be added as a marker to each log.
        """
        name = name.replace(".log", "")
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        # decide if this logger sends messages to a log server
        # load_dotenv()
        self.log_server = os.getenv(CONFIG_KEY_LOG_SERVER)
        self.log_server_auth = os.getenv(CONFIG_KEY_LOG_SERVER_AUTH)

        self.is_worker = self.log_server is not None

        # check if other handlers are provided
        if not logger.handlers:
            if self.is_worker:
                # worker process
                self._configure_worker(logger, self.log_server, self.log_server_auth)
            else:
                # listener process
                if os.getenv(CONFIG_KEY_LOG_FOLDER) is not None and log_folder is None:
                    log_folder = os.getenv(CONFIG_KEY_LOG_FOLDER)
                if log_folder is None:
                    self._configure_listener(logger, enable_logger_name=enable_logger_name)
                else:
                    self._configure_listener(logger, log_folder, enable_logger_name)

        self._logger = logger

    def warn(self, msg, *args, **kwargs):
        self._logger.warning(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self._logger.error(msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self._logger.info(msg, *args, **kwargs)

    def exception(self, msg):
        self._logger.exception(msg)

    @staticmethod
    def _configure_worker(logger, url, auth=None):
        handler_debug = _CustomHttpHandler(logging.INFO, url, auth)
        handler_error = _CustomHttpHandler(logging.ERROR, url, auth)

        # message formatter
        formatter = logging.Formatter("%(asctime)s %(levelname)s:%(name)s %(message)s")
        handler_debug.setFormatter(formatter)
        handler_error.setFormatter(formatter)

        logger.addHandler(handler_debug)
        logger.addHandler(handler_error)

    @staticmethod
    def _configure_listener(logger, log_folder="_logs", enable_logger_name=True):

        # message formatter
        formatter = logging.Formatter("%(asctime)s %(levelname)s:%(name)s %(message)s")
        if enable_logger_name is False:
            formatter = logging.Formatter("%(asctime)s %(levelname)s:%(message)s")
        # file name for the log
        file_name_debug = os.path.join(log_folder, "debug.log")
        file_name_error = os.path.join(log_folder, "error.log")
        # add a rotating file handler, starting a new file every(1) (d)ay
        handler_debug = handlers.TimedRotatingFileHandler(file_name_debug, when="d", interval=1, backupCount=30)
        handler_error = handlers.TimedRotatingFileHandler(file_name_error, when="d", interval=1, backupCount=30)

        # configure handler and logger
        handler_debug.setFormatter(formatter)
        handler_debug.setLevel(logging.INFO)
        # yes, it is a debug logger, but Python considers info higher severity than debug

        handler_error.setFormatter(formatter)
        handler_error.setLevel(logging.ERROR)

        logger.addHandler(handler_error)
        logger.addHandler(handler_debug)
