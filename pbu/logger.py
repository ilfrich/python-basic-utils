import os
import logging
from logging import handlers


class Logger(object):
    """
    File logger for this application, logging into application.log in the configured LOG_FOLDER.
    Usage:

    >>> logger = Logger("some-name").get()
    >>> logger.info("My message")
    """
    def __init__(self, name, log_folder="_logs"):
        """
        Creates a new instance of this logger and will store it as a private field, which is exposed via the get()
        method.
        :param name: the name of the class / component, which will be added as a marker to each log.
        """
        name = name.replace(".log", "")
        logger = logging.getLogger("precooling.%s" % name)
        logger.setLevel(logging.DEBUG)
        # check if other handlers are provided
        if not logger.handlers:
            # message formatter
            formatter = logging.Formatter("%(asctime)s %(levelname)s:%(name)s %(message)s")
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

            logger.addHandler(handler_debug)
            logger.addHandler(handler_error)
        self._logger = logger

    def get(self):
        """
        Retrieves a private field with the actual logger instance, which offers methods for logging exceptions and
        messages of different levels (debug, info, warn, error)
        :return: the actual Python logging logger instance.
        """
        return self._logger
