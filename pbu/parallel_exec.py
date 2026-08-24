import os
import sys
from abc import ABC, abstractmethod
from math import ceil
from random import randint
from time import sleep
from typing import Any, List, Optional

from pbu.debug_object import DebugObject, get_coverage_string
from pbu.files import read_json, write_json
from pbu.logger import Logger
from pbu.performance_logger import PerformanceLogger


class ParallelExecutor(ABC, DebugObject):
    def __init__(
        self,
        num_threads: int,
        argv_idx: int = -1,
        debug: bool = True,
        debug_logger: Optional[Logger] = None,
        lock_path: str = ".lock",  # local relative path to execution
    ):
        super().__init__(debug, debug_logger)
        self.num_threads = num_threads
        self.argv_idx = argv_idx
        self.perf = PerformanceLogger()
        self.lock_path = lock_path
        self.thread_id = None

    @abstractmethod
    def aggregate(self) -> None:
        pass  # for the user to implement

    @abstractmethod
    def extract(self, item: Any) -> None:
        pass  # for the user to implement

    def debug_log(self, *kwargs):
        if self.thread_id is None:
            super().debug_log(*kwargs)  # just use regular logging during aggregation
            return
        # prepend [0] for thread 0 to every message
        super().debug_log(f"[{self.thread_id}]", *kwargs)

    def sequential_extract(self, exec_items: List[Any]):
        """
        Processes a list of items in sequence and handles some basic logging and performance measurements
        :param exec_items: the items to extract. These will be passed into the .extract(..) call.
        """
        self.debug_log(f"Executing {len(exec_items)} item(s)")
        self.start_perf_log()
        for i, item in enumerate(exec_items):
            self.extract(item)
            self.perf_log(f"Processing item {get_coverage_string(i + 1, len(exec_items))}")
        self.perf_log("Extraction finished", finish=True)

    def parallel_extract(self, items: List[Any], consecutive: bool = False) -> None:
        """
        Simple orchestration function that splits the provided items up into execution buckets and selects its bucket.
        :param items: the items to process, can be anything your implementation gets as parameter in the .extract(..)
        :param consecutive: sometimes it is of value to have buckets contain consecutive values, if your extractor is
        like that, then this changes the behaviour. If False, we will assign items alternating to the available thread
        ids.
        """
        self.thread_id = self.get_thread_id()  # will raise Error if no thread id can be determined
        exec_items = self.get_execution_bucket(items, consecutive)
        if len(exec_items) == 0:
            self.debug_log(f"Nothing to execute from {len(items)} total items")
            return

        # call the sequential execution for these items
        self.sequential_extract(exec_items)

    # bucketing functions

    def get_execution_bucket(self, item_list: List[Any], consecutive: bool = False) -> List[Any]:
        """
        Will create a list of items to execute from a total list of available items. This is used to prepare the
        execution for any thread.
        :param item_list: a list of anything. This will be grouped into buckets
        :param consecutive: how the grouping is performed, if True, consecutive items from the item_list will be choosen
        if False, buckets will be assigned alternating as we iterate through the item list
        :returns: a list of items to process for the current thread (can be empty list)
        """
        buckets = {}
        current_bucket = 0
        if consecutive is True:
            # create a copy of the item list to work with
            remaining_items = item_list[:]
            current_bucket = 0
            # we will reduce the list by slicing off the first num_items each time we increase the bucket index
            while len(remaining_items) > 0 and current_bucket < self.num_threads:
                remaining = self.num_threads - current_bucket
                num_items = ceil(len(remaining_items) / remaining)
                buckets[current_bucket] = remaining_items[0:num_items]
                remaining_items = remaining_items[num_items:]
                current_bucket += 1
        else:
            # alternating
            for i, item in enumerate(item_list):
                thread_id = i % self.num_threads
                buckets[thread_id] = buckets.get(thread_id, []) + [item]

        return buckets.get(self.get_thread_id(), [])

    def get_thread_id(self) -> int:
        """
        Will extract the current thread id from the program call and convert it to an integer between 0 and num_threads
        :returns: an integer between 0 and num_threads (modulo)
        """
        if len(sys.argv) <= 1 if self.argv_idx <= 0 else self.argv_idx:
            raise ValueError("Not enough parameters provided")
        param = sys.argv[self.argv_idx]
        if param == sys.argv[0]:
            raise ValueError(f"Provided argv index '{self.argv_idx}' contains the script file index of your call")
        try:
            thread_id = int(param)  # cast to int
            return thread_id % self.num_threads  # return the modulo
        except ValueError:
            raise ValueError(f"Cannot parse provided thread id '{param}' into an integer")

    # thread/locking for parallel write to result files

    def _acquire_lock(self) -> bool:
        if self.thread_id is None:
            return True  # no need for acquiring a lock

        new_lock = {"lock": self.thread_id}
        while True:
            lock = self._read_lock_file()
            if lock is None:
                # no lock file exists, lets write ours
                if not self._write_lock_file(new_lock):
                    sleep(0.1)  # wait for 100ms to see if another thread was writing at the same time
                # we have written the log or waited for a bit, see next loop, when lock is read fresh
                continue

            if lock["lock"] == self.thread_id:
                return True  # we have the lock

            # lock belongs to a different thread id
            sleep(2)  # try again in a few seconds (this is not an expensive operation)

    def _write_lock_file(self, new_lock: dict) -> bool:
        try:
            write_json(new_lock, self.lock_path)
            return True  # no error during write
        except BaseException:
            return False

    def _read_lock_file(self) -> Optional[dict]:
        if not os.path.exists(self.lock_path):
            return None
        lock = None
        # to avoid issues when reading while another thread is writing the file, we have to while this
        while os.path.exists(self.lock_path) and lock is None:
            # attempt to read the lock file
            try:
                lock = read_json(self.lock_path)  # could have been deleted by now or being written
            except BaseException:  # these exceptions can come in all sorts of shapes, depending on scenario
                # when the file is being written, this can happen
                wait_ms = randint(30, 1000)  # between 30ms and 1s
                sleep(wait_ms / 1000)

        # can still be None and the file was deleted
        return lock

    def _release_lock(self) -> bool:
        if self.thread_id is None:
            return True  # no need to release a lock

        lock = self._read_lock_file()
        if lock["lock"] != self.thread_id:
            self.debug_log(f"Some other thread holds lock for '{self.thread_id}': {lock['lock']}")
            return True

        # delete the lock file
        os.unlink(self.lock_path)
        return True
