import time
from threading import Event
from datetime import datetime
from typing import Optional
from abc import ABC, abstractmethod
from pbu.logger import Logger
from pbu.constant_listing import ConstantListing
from pbu.debug_object import DebugObject


class JobStatus(ConstantListing):
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    STALLED = "STALLED"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    PAUSED = "PAUSED"
    RESUMED = "RESUMED"
    RERUN = "RERUN"


class BasicMonitor(ABC, DebugObject):
    """
    Abstract base class (ABC) for all monitors containing base functionality for lifecycle and meta information.
    """

    def __init__(self, monitor_id: str, wait_time: int, run_interval: bool = False,
                 custom_logger: Optional[Logger] = None, ping_interval: int = 60, debug: bool = False,
                 debug_logger: Optional[Logger] = None):
        """
        Super constructor invoked from implementing sub-classes of this class
        providing interfaces start, track_success and track_error
        """
        super().__init__(debug, debug_logger)
        # set meta flags
        self.active = False
        self.finished = False
        self.started = False

        # store parameters
        self.monitor_id = monitor_id
        self.wait_time = wait_time
        self.ping_interval = ping_interval
        self.run_interval = run_interval

        # init logger
        if custom_logger is not None:
            self.logger = custom_logger
        else:
            self.logger = Logger(self.__class__.__name__)
        # handle ping interval issues
        if wait_time < ping_interval:
            self.logger.info(f"WARNING, monitor wait time {ping_interval} is longer than {wait_time} - overriding")
            self.ping_interval = wait_time
        
        # runtime variables
        self._next_execution = 0
        self._wait_event: Event = Event()
        self.is_interrupted: bool = False

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
        # reset interrupted flag
        if self._wait_event.is_set():
            self._wait_event = Event()
            self.is_interrupted = False

        now = time.time()
        # set next execution
        if self.run_interval:
            gap_next = max(1, self.wait_time - exec_duration)
            if gap_next < self.ping_interval:
                # special handling if next execution is sooner than ping interval
                self._wait_event.wait(gap_next)
                return  # exit after wait
            self._next_execution = now + gap_next
        else:
            self._next_execution = now + self.wait_time

        # check every ping interval if we're close to next execution
        while time.time() + self.ping_interval < self._next_execution:
            self._wait_event.wait(self.ping_interval)
            if self._wait_event.is_set():
                return

        # wait remaining time
        remaining = round(self._next_execution - time.time())
        if remaining > 0:
            self._wait_event.wait(remaining)
        if remaining < 0:
            self.logger.info(f"Overdue execution by {-round(remaining)}s")

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

    def interrupt(self):
        if self._wait_event is not None and not self._wait_event.is_set():
            self._wait_event.set()
            self.is_interrupted = True

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
