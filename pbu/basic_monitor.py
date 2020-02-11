import time
from datetime import datetime
from abc import ABC, abstractmethod
from pbu import Logger


class BasicMonitor(ABC):
    """
    Abstract base class (ABC) for all monitors containing base functionality for lifecycle and meta information.
    """

    def __init__(self, monitor_id, wait_time, run_interval=False, custom_logger=None):
        """
        Super constructor invoked from implementing sub-classes of this class
        providing interfaces start, track_success and track_error
        """
        # set meta flags
        self.active = False
        self.finished = False
        self.started = False

        # store parameters
        self.monitor_id = monitor_id
        self.wait_time = wait_time
        self.run_interval = run_interval

        # init logger
        if custom_logger is not None:
            self.logger = custom_logger
        else:
            self.logger = Logger(self.__class__.__name__)

    @abstractmethod
    def running(self):
        """
        Abstract main method of each inverter. `running` needs to be implemented by every non-abstract sub-class of this
        class.
        """
        pass

    def to_json(self):
        """
        Creates a dictionary with some base meta attributes about this monitor. Sub classes should invoke this method
        when serialising to json and then add any additional parameters as necessary to the result of this methods
        invoke.
        :return: a dictionary with basic information, such as site_id and overall active status
        """
        return {
            "active": self.active,
            "started": self.started,
            "finished": self.finished,
            "id": self.monitor_id,
            "waitTime": self.wait_time,
            "runInterval": self.run_interval,
        }

    def wait(self, exec_duration=0):
        """
        Executes a wait for a certain amount of time depending on the configuration of the monitor. Additionally, it
        takes into account the execution time of the last loop, if run_interval is True.
        :param exec_duration: the execution time of the last execution loop (only relevant for run_interval=True)
        """
        if self.run_interval:
            time.sleep(max(1, self.wait_time - exec_duration))
        else:
            time.sleep(self.wait_time)

    def wait_till_midnight(self):
        """
        This method will just wait until the next midnight event. If the monitor is started at 6:30pm, this method will
        simply wait for 5h and 30min.
        """
        # localise current date
        local_date = datetime.now()
        # extract time
        local_time = local_date.time()
        # compute wait time until midnight
        wait_time = ((23 - local_time.hour) * 60 * 60) + ((59 - local_time.minute) * 60) + (60 - local_time.second)
        # wait till midnight
        self.logger.info("Waiting {} seconds for monitor {} until midnight".format(wait_time, self.monitor_id))
        time.sleep(wait_time)

    def start(self):
        """
        Starts the monitor, updating a flag and triggering `running()`
        """
        if self.active:
            # already started
            return
        # start monitor
        self.active = True
        try:
            if self.started:
                # only restart if the previous thread has finished or after error
                self.logger.info("Restarting monitor for {}".format(self.monitor_id))
                self.running()
            else:
                # first time start
                self.started = True
                self.logger.info("Starting monitor for {}".format(self.monitor_id))
                self.running()
            self.finished = True
        except BaseException as ex:
            self.logger.exception("Exception during monitor execution for monitor {}: {}".format(self.monitor_id,
                                                                                                 str(ex)))
            # is currently not active due to error
            self.active = False
            # wait for one execution loop to avoid error spamming
            time.sleep(self.wait_time)
            self.start()

    def stop(self):
        """
        Sets the active flag to false, which will terminate the `running()` loop.
        """
        # set a flag, let the monitor handle this
        self.logger.info("Stopping {} for {}".format(self.__class__.__name__, self.monitor_id))
        self.active = False
