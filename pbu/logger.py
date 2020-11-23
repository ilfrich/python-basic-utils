import os
import requests
import logging
import sys
import traceback
from logging import handlers

CONFIG_KEY_LOG_SERVER = "PBU_LOG_SERVER"
CONFIG_KEY_LOG_SERVER_AUTH = "PBU_LOG_SERVER_AUTH"
CONFIG_KEY_LOG_FOLDER = "PBU_LOG_FOLDER"


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
            trace = []
            for el in result["exc_info"]:
                if type(el).__name__ == "traceback":
                    # custom traceback logging, because we can't serialise this
                    stack = traceback.extract_stack()
                    for err_line in stack[:-9]:
                        trace.append("    {}:{} {}".format(err_line.filename, err_line.lineno, err_line.name))
                        trace.append("        {}".format(err_line.line))
                    for err_line in traceback.format_tb(el):
                        trace.append("    {}".format(err_line.strip()))
            del result["exc_info"]
            if len(trace) > 0:
                result["trace"] = trace
        if "msg" in result and not isinstance(result["msg"], str):
            result["msg"] = str(result["msg"])
        return result

    def emit(self, record):

        is_higher_than_error = self.level == logging.ERROR and record.levelno in [logging.CRITICAL, logging.FATAL]
        if record.levelno != self.level and not is_higher_than_error:
            return

        headers = {
            "Content-Type": "application/json",
        }
        if self.auth_token is not None:
            headers["Authorization"] = self.auth_token
        try:
            requests.post(url=self.url, json=_CustomHttpHandler._map_log_record(record), headers=headers)
        except BaseException as be:
            print("Error sending log message: {} ({})".format(_CustomHttpHandler._map_log_record(record), be),
                  file=sys.stderr)


class Logger(logging.Logger):
    """
    File logger for this application, logging into application.log in the configured LOG_FOLDER.
    Usage:

    >>> logger = Logger("some-name")
    >>> logger.info("My message")
    """

    def __init__(self, name, log_folder=None, enable_logger_name=True, enabled_log_levels=[logging.INFO, logging.ERROR],
                 message_format="%(asctime)s %(levelname)s:%(name)s %(message)s"):
        """
        Creates a new instance of this logger and will store it as a private field, which is exposed via the get()
        method.
        :param name: the name of the class / component, which will be added as a marker to each log.
        """
        name = name.replace(".log", "")
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        # decide if this logger sends messages to a log server
        self.log_server = os.getenv(CONFIG_KEY_LOG_SERVER)
        self.log_server_auth = os.getenv(CONFIG_KEY_LOG_SERVER_AUTH)

        self.is_worker = self.log_server is not None

        if log_folder is not None:
            if not os.path.isdir(log_folder):
                os.makedirs(log_folder)

        # check if other handlers are provided
        if not logger.handlers:
            if self.is_worker:
                # worker process
                self._configure_worker(logger, self.log_server, message_format, self.log_server_auth,
                                       enabled_log_levels)
            else:
                # listener process
                if os.getenv(CONFIG_KEY_LOG_FOLDER) is not None and log_folder is None:
                    log_folder = os.getenv(CONFIG_KEY_LOG_FOLDER)
                if log_folder is None:
                    self._configure_listener(logger, message_format, enable_logger_name=enable_logger_name,
                                             enabled_log_levels=enabled_log_levels)
                else:
                    self._configure_listener(logger, message_format, log_folder=log_folder,
                                             enable_logger_name=enable_logger_name,
                                             enabled_log_levels=enabled_log_levels)

        self._logger = logger

    def warn(self, msg, *args, **kwargs):
        self._logger.warning(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self._logger.error(msg, stack_info=True, exc_info=True, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self._logger.info(msg, *args, **kwargs)

    def exception(self, msg):
        self._logger.exception(msg, stack_info=True)

    def handle(self, record):
        self._logger.handle(record)

    @staticmethod
    def _configure_worker(logger, url, message_format, auth=None, enabled_log_levels=[logging.INFO, logging.ERROR]):
        for log_level in enabled_log_levels:
            handler = _CustomHttpHandler(log_level, url, auth)
            formatter = logging.Formatter(message_format)
            handler.setFormatter(formatter)
            logger.addHandler(handler)

    @staticmethod
    def _configure_listener(logger, message_format, log_folder="_logs", enable_logger_name=True,
                            enabled_log_levels=[logging.INFO, logging.ERROR]):
        formatter = logging.Formatter(message_format)
        if enable_logger_name is False:
            # remove logger name from message format
            message_format = message_format.replace("%(name)s", "")
            formatter = logging.Formatter(message_format)

        file_names = {
            logging.INFO: "info.log",
            logging.DEBUG: "debug.log",
            logging.ERROR: "error.log",
            logging.WARNING: "warning.log",
        }

        for log_level in enabled_log_levels:
            file_name = os.path.join(log_folder, file_names[log_level])
            if not os.path.isdir(log_folder):
                os.makedirs(log_folder)
            handler = handlers.TimedRotatingFileHandler(file_name, when="d", interval=1, backupCount=30)
            handler.setFormatter(formatter)
            handler.setLevel(log_level)
            logger.addHandler(handler)
