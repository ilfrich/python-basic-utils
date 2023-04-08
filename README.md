# Python Basic Utilities `pbu`

Available on [PyPi](https://pypi.org/project/pbu/)

**Table of Contents**

1. [Installation](#installation)
2. [Usage](#usage)
3. [Classes](#classes)
    1. [JSON](#json) - a JavaScript-like dictionary access helper
    2. [Logger](#logger) - a wrapper around the Python logging framework
    3. [TimeSeries](#timeseries) - powerful helper class to organise time series
    4. [BasicMonitor](#basicmonitor) - monitor class orchestrating regular operations
    5. [ConstantListing](#constantlisting) - a parent class allowing to fetch attribute values from a constant class
    6. [PerformanceLogger](#performancelogger) - a utility class to log runtime performance of processes
    7. [BasicConfig](#basicconfig) - application utility class managing access to environment variables
    8. [JsonDocument](#jsondocument) - a class that can serialise/deserialise a dictionary into a class instance
4. [Functions](#functions)
    1. [`list_to_json`](#list_to_json)
    2. [`json_to_list`](#json_to_list)
    3. [`default_options`](#default_options)
    4. [`default_value`](#default_options)
    5. [`list_find_one`](#list_find_one)
    6. [`list_map_filter`](#list_map_filter)
    7. [`list_join`](#list_join)
    8. [`not_none`](#not_none)
    9. [Datetime Functions](#datetime-functions)
    10. [`weighted_mean`](#weighted_mean)
    11. [`normalise`](#normalise)

## Installation

Install via pip:

```bash
pip install pbu
```

## Usage

***Optional***: If you have a requirement.txt file, you can add `pbu`:

```bash
pbu
```

Then, simply import the class / module you need:

```python
from pbu import JSON

# and start using it
obj = JSON({"my": {"obj": "content"}})
print(obj.my.obj)
```

## Classes

### JSON

This is an adaptation of the native `dict` class, providing Javascript-like dictionary access using the "dot-notation"
(e.g. `person.relations[0].address.street`) rather than the Python-native bracket notation (e.g.
`person["relations"][0]["address"]["street"]`). It overrides the basic `__getattr__` and `__setattr__` methods as a
shortcut to manage the dictionary content.

**Example**

```python
from pbu import JSON

my_obj = JSON({"initial": "content"})
print(my_obj.initial)
# prints out "content"

my_obj.initial = {"a": 5, "b": 3}
print(my_obj.initial.a + my_obj.initial.b)
# prints out 8
my_obj.initial.b = 13
print(my_obj.initial.a + my_obj.initial.b)
# prints out 18

my_obj.extension = 10
print(my_obj.extension)
# prints out 10
```

### Logger

This is a basic logger allowing to write log files, for `logger.info` it writes a debug.log and for `logger.error` or
`logger.exception` it writes an error.log file.

**Example**

```python
from pbu import Logger

logger = Logger(name="logger-name")
logger.debug("Some debug message goes here")
logger.error("Error executing something")

logger = Logger(name="logger-name", log_folder="./logs")
logger.debug("This will create the debug.log and error.log in the ./logs folder")
```

### TimeSeries

The time series class is a helper utility, that allows to compile complex time-series, offering functionality to add
time series, remove time series and most importantly align time series with timestamps to a previously defined
resolution by interpolating missing values and re-aligning measurements within the tolerance of the provided time
series.

It supports 2 different structures:

**List of Dictionary Items**

```python
from datetime import datetime, timedelta

list_of_dict = [
    {"date_time": datetime.now(), "measurement_1": 12, "measurement_2": 15},
    {"date_time": datetime.now() + timedelta(hours=1), "measurement_1": 10, "measurement_2": 16},
    {"date_time": datetime.now() + timedelta(hours=2), "measurement_1": 9, "measurement_2": 12},
]
```

**Dictionary of Lists**

```python
from datetime import datetime, timedelta

dict_of_list = {
    "date_time": [datetime.now(), datetime.now() + timedelta(hours=1), datetime + timedelta(hours=2)],
    "measurement_1": [12, 10, 16],
    "measurement_2": [15, 16, 12],
}
```

**Example**

```python
from pbu import TimeSeries
from datetime import datetime, timedelta

# initial time series base data (you can add measurements as well or provide as list of dictionaries
dict_of_list = {
    "date_time": TimeSeries.create_date_range(datetime.now(), datetime.now() + timedelta(days=1), timedelta(hours=3)),
}

# init time series
ts = TimeSeries(input_data=dict_of_list, date_time_key="date_time")
# add values (ensure same length as date_time series)
ts.add_values("measurement_1", [12, 10, 16, 10, 5, 8, 12, 9])

# you can translate into a list of dictionary items (keys are maintained)
list_of_dict = ts.translate_to_list_of_dicts()

# extract data series from the time series
measurement_1 = ts.get_values("measurement_1")

# create new series that provides same value for all timestamps
ts.fill_values("constant_series", 5)

# remove a series from the total data structure
ts.remove_series("constant_series")

# re-sample data to 5 minute resolution, interpolating values, also pre-pending another day in front of the time series 
ts.align_to_resolution(resolution=timedelta(minutes=5), start_date=datetime.now() - timedelta(days=1))
# this will result in "interpolated" values for the first day, using the first value (12) to fill missing values
print(len(ts.translate_to_list_of_dicts()))  # 12 an hour, 2 days, 48 * 12 = ~576 items

# the same can also be achieved by:
ts.set_resolution(timedelta(minutes=5))
# no need to provide resolution now
ts.align_to_resolution(start_date=datetime.now() - timedelta(days=1))
```

### BasicMonitor

An abstract class providing base-functionality for running monitors - threads that run a specific routine in a regular
interval. This can be an executor waiting for new tasks to be processed (and checking every 5 seconds) or a thread that
monitors some readout in a regular interval. The monitor is wrapped to re-start itself, in case of errors.

**Example**

```python
from pbu import BasicMonitor


class MyOwnMonitor(BasicMonitor):
    def __init__(self, data):
        super().__init__(monitor_id="my_id", wait_time=5)  # waits 5 seconds between each execution loop
        self.data = data

    def running(self):
        while self.active:
            # your code goes here (example):
            # result = fetch_data(self.data)
            # store_result(result)
            self.wait()
```

If you want to run in a regular interval, the `running` method needs to be slightly modified:

```python
from time import time
from pbu import BasicMonitor


class MyRegularOwnMonitor(BasicMonitor):
    def __init__(self, data):
        super().__init__(monitor_id="another_id", wait_time=60, run_interval=True)  # execute every 60 seconds
        self.data = data

    def running(self):
        while self.active:
            start_ts = time()  # capture start of loop
            # your code goes here (example):
            # result = do_something(self.data)
            # store_result(result)
            self.wait(exec_duration=round(time() - start_ts))  # include the execution duration
```

**Optional constructor parameters**

- You can also pass a custom logger as `custom_logger` argument to the constructor. By default it will use the
  `pbu.Logger` and log major events such as start/stop/restart and errors.
- Passing a `ping_interval` parameter allows you to check for overdue jobs more often than the wait time. For example
  you could have a `wait_time` of 1800s (30 min) and a `ping_interval` of 60s, which allows you to not miss out on an
  execution if your machine running the monitor should sleep (e.g. on a laptop when you put it on standby, the sleep
  timer stops). By default this is `60` seconds (or the `wait_time`, if the `wait_time` is lower than 60s)

**Manage and run monitor**

```python
import threading


def start_monitor_thread(monitor):
    """
    Thread function to be run by the new thread.
    :param monitor: BasicMonitor - an instance of sub-class of BasicMonitor 
    """
    # start the monitor
    monitor.start()


# create monitor instance of your own class that implements BasicMonitor
regular_monitor = MyRegularOwnMonitor(data={"some": "data"})

# create thread with start-up function and start it
t = threading.Thread(target=start_monitor_thread, args=(regular_monitor,), daemon=True)
t.start()

# in a separate piece of code (e.g. REST handler or timer) you can stop the monitor instance
regular_monitor.stop()
```

Stopping a monitor doesn't interrupt the current thread. If the monitor is for example in a wait period and you send the
`stop` signal, the thread will still run until the wait period passes.

> _In an API scenario, I recommend using a `dict` or `list` to cache monitors and retrieve them via the API using the
`to_json()` method for identification. This then allows you to signal starting / stopping of monitors by providing the
monitor ID and lookup the monitor instance in the monitor cache._

**`BasicMonitor` Methods**

- `start()` - starts the monitor
- `stop()` - stops the monitor
- `to_json()` - returns a dictionary with basic monitor technical information (id, state, wait behaviour, etc)
- `wait_till_midnight()` - waits till the next midnight in your machines time zone
- `wait(exec_duration=0)` - waits for the time specified in the constructor and in case of `run_interval=True` for the
  optional `exec_duration`, if provided.

### ConstantListing

Managing constants is good practice for avoiding typos. Imagine the following class:

```python
class Tags:
    GEO = "GEO"
    EQUIPMENT = "EQUIPMENT"
```

This allows you to just do: `Tags.GEO` allowing you to use your IDEs auto-complete, avoiding typos. But if you want to
programmatically get **all** possible values for `Tags`, you can use `pbu`'s `ConstantListing` class:

```python
from pbu import ConstantListing


class Tags(ConstantListing):
    GEO = "GEO"
    EQUIPMENT = "EQUIPMENT"


list_of_values = Tags().get_all()  # will return ['GEO', 'EQUIPMENT']
```

### PerformanceLogger

This utility class allows to print out or log runtime performance expressed as time delta between a start time and an
end time.

Basic usage:

```python
from pbu import PerformanceLogger

perf = PerformanceLogger()
perf.start()  # this is optional and will reset the start-time
# do something useful...
perf.checkpoint(message="Step 1")  # will print "Step 1 took <timedelta>
# some some more useful stuff...
perf.finish(message="Something useful")  # will print out the whole duration from start to finish
```

You can omit the message of a `checkpoint` call if you don't need an output for an operation, but want to print out the
duration of the step that follows.

You can also use a Python `Logger` object (or `pbu.Logger`) instead of the message being printed out onto the console.

```python
from pbu import Logger, PerformanceLogger

logger = Logger("my-logger-name")
perf = PerformanceLogger()
# do something...
perf.checkpoint()  # next output will print the duration between this point and the next checkpoint call
# do some more stuff...
perf.checkpoint(message="Some More Stuff", logger=logger)
# and even more ...
perf.finish(message="Total operation", logger=logger)
```

**Methods**

- `start()` - will reset the start time of the performance logger
- `checkpoint(message=None, logger=None)` - creates a new checkpoint and optionally logs a message
- `finish(message=None, logger=None)` - prints out the total runtime since `start()` was called or the class was
  initialised

### `BasicConfig`

This class can be used in applications to simplify access to environment variables. It is recommended to write your own
sub-class of this class, where you can provide even more convenient access. However, the class can also be used
standalone.

Basic usage:

```python
import os
from pbu import BasicConfig


class Config(BasicConfig):
    def __init__(self):
        super().__init__(default_values={
            "PORT": 5000,
            "IS_DEBUG": 1,
            "DATA_DIRECTORY": None,
        }, directory_keys=["DATA_DIRECTORY"], required=["DATA_DIRECTORY"])

    def get_port(self) -> int:
        return int(self.get_config_value("port"))

    def is_debug(self) -> bool:
        return int(self.get_config_value("is_debug")) == 1

    def get_data_directory(self) -> str:
        return self.get_config_value("DATA_DIRECTORY")


cfg = Config()
# BasicConfig will ensure the directory exists
result = os.path.exists(cfg.get_data_directory())
# result is True      
```

**Methods**

- `get_config_value(config_key, default_value=None)` - retrieves a config value, the default value override is optional
  as it should already be provided in the `default_values` of the constructor. If a `config_key` hasn't been provided by
  the `default_values` of the constructor, this will trigger reading the value fresh from the environment and storing it
  within this class.
- `__init__(default_values={}, directory_keys=[], required=[], env_file=".env")` - super constructor, which will be used
  to load the initial environment.
    - The `default_values` provide the keys that will be extracted from the OS environment.
    - The `directory_keys` are config keys that will be used to run a directory check. If the provided environment value
      refers to a directory that doesn't exist yet, the class will attempt to create it.
    - The `required` parameter provides environment keys that have to be provided by the OS environment. If they are not
      available in the environment, an `EnvironmentError` will be raised.

## `JsonDocument`

**Methods**

- `to_json()` - call this to return a dict representation of the instance. This will serialise the `id` and
  `data_model_version` attributes and any attributes provided in the `get_attribute_mapping()` method.
- `get_attribute_mapping()` - provides a dict mapping between class attributes and JSON keys that will be used in the
  `dict` representation.
- `extract_system_fields(json: dict)` - this will deserialise a `dict` and map the `_id` field to the `id` attribute,
  `dataModelVersion` field to `data_model_version` attribute and any field defined in the `get_attribute_mapping()`
  method.
- `apply_updates(update, attributes = [])` - overwrites attributes of the current instance with the `update`. The list
  of attributes has to be specified and is empty by default. The `update` must be of the same type as the current
  instance. If an `attribute` is listed that does not exist, a warning will be issued.

**Static Methods**

- `.from_json(json)` - this method has to be implemented by any sub-class and is responsible for
  deserialising a JSON document into an instance of your sub-class. The instance method `extract_system_fields(json)`
  can be used to map most simple attributes - i.e. any attributes provided in the `get_attribute_mapping()` method.

## Functions

### `list_to_json`

```python
from pbu import list_to_json

# assuming we have `my_store` as an instance of MongoDB store or MySQL store, you can:
list_of_dictionaries = list_to_json(item_list=my_store.get_all())  # output is a list of dictionaries
```

This function operates on lists of objects inheriting from `JsonDocument` and converts them into dictionaries using the
`to_json()` method of any object passed into the function. Objects passed into the function _require_ the `to_json()`
method and need to return the dictionary representation of the object. This function is just a mapping shortcut.

### `list_from_json`

```python
from pbu import list_from_json

# assuming we have a class `MyClass` that inherits from `JsonDocument` and implements the `from_json()` method
list_from_json(item_list=[{"a": 1, "b": 2}, {"a": 3, "b": 4}], class_type=MyClass)
```

### `default_options`

```python
from pbu import default_options

DEFAULTS = {
    "a": 1,
    "b": 2,
    "c": 3,
}

result = default_options(default=DEFAULTS, override={"b": 4, "d": 5})
# result is: {"a": 1, "b": 4, "c": 3, "d": 5}
```

If you want to avoid additional keys other than the keys in DEFAULTS, you can provide a third argument:

```python
from pbu import default_options

DEFAULTS = {
    "a": 1,
    "b": 2,
}

result = default_options(default=DEFAULTS, override={"b": 4, "d": 5}, allow_unknown_keys=False)
# result is: {"a": 1, "b": 4}
```

### `default_value`

```python
from pbu import default_value

result = default_value(value=None, fallback=5)  # None is by default disallowed
# result is 5

result = default_value(value=0, fallback=5, disallowed=[None, 0])  # either 0 or None would return the fallback
# result is 5

result = default_value(0, 5)  # value will be used, as it doesn't match None
# result is 0
```

### `list_find_one`

Finds the first item in a list that matches the filter function - this is a shortcut for running `filter(..)` on a list,
then checking its length and if the length is > 0 fetching the first item.

```python
from pbu import list_find_one

my_list = ["a", "b", "c"]

result = list_find_one(lambda x: x == "c", my_list)
# result is "c"

result = list_find_one(lambda x: x == "d", my_list)
# result is None
```

### `list_map_filter`

A shorthand for filtering and mapping a lsit of items. The function allows to pass both lambdas (`filter` and `map`)
into one function call. A boolean flag (`filter_first=True`) decides whether the filter or map operation is called
first.

```python
from pbu import list_map_filter

my_list = [
    {"name": "a", "count": 5},
    {"name": "b", "count": 100},
    {"name": "b", "count": 32},
]

result = list_map_filter(my_list, filter_func=lambda x: x["count"] % 5 == 0, map_func=lambda x: x["name"])
# result is ["a", "b"]

result = list_map_filter(my_list, filter_func=lambda x: x > 50, map_func=lambda x: x["count"], filter_first=False)
# result is [100]
```

### `list_join`

A helper function that joins a list with a given token. The Python default way for joining a list of items uses the join
token (e.g. ",") and then calls `.join` on that string, passing the list of items as parameter. However, unfortunately
this only accepts a list of strings and throws an error, if other types are passed (e.g. a list of numbers).

This helper casts all items to `str` before joining.

```python
from pbu import list_join

my_list = ["a", 0, 4.5, False]

result = list_join(my_list, "-")
# result is "a-0-4.5-False"

result = "-".join(my_list)
# throws Error because my_list contains items of type other than `str`
```

### `not_none`

A helper function to filter out `None` values from a list.

```python
from pbu import not_none

my_list = ["a", None, "b", None, "c"]
result = not_none(my_list)
# result is ["a", "b", "c"]
``` 

### Datetime Functions

PBU provides some utilities to help deal with timezones and datetime objects. All timezone specifications can be made
either as a string (i.e. the name of the timezone, like `"Australia/Melbourne"`) or as `pytz.timezone` object.

#### `combine_date_time(date, time, tz)`

Combines the provided date and time values.

```python
from datetime import date, time
from pbu import combine_date_time

result = combine_date_time(date(year=2021, month=12, day=25), time(hour=15, minute=12, second=6), "Australia/Perth")
```

#### `to_timezone(local_datetime, target_tz)`

Translates a datetime to the provided target timezone.

```python
from datetime import datetime
from pytz import utc
from pbu import to_timezone

utc_dt = datetime(year=2021, month=12, day=25, hour=3, minute=0, tzinfo=utc)  # 3:00am @ 2021-12-25
perth_dt = to_timezone(utc_dt, "Australia/Perth")
# > Result: 11:00am @ 2021-12-25 (+0800)
```

#### `to_utc(local_datetime)`

Shorthand for `to_timezone(dt, pytz.utc)`

#### `set_timezone(datetime, target_timezone)`

Simply replaces the timezone information without changing any of the time values of the datetime.

```python
from datetime import datetime
from pytz import utc, timezone
from pbu import set_timezone

utc_dt = datetime(year=2021, month=12, day=25, hour=3, minute=0, tzinfo=utc)  # 3:00am @ 2021-12-25
perth_dt = set_timezone(utc_dt, timezone("Australia/Perth"))
# > Result: 3:00am @ 2021-12-25 (+0800)
```

### `weighted_mean`

Provides the mean (average) of a list of values, where the values are weighted by the provided weights (in the same
order as the value are provided). For missing weights, the default weight is 1

```python
from pbu import weighted_mean

weights = [5, 3, 1]
values = [10, 5, 5, 4, 3]

# ((10 * 5) + (3 * 5) + (1 * 5) + 4 + 3) / (5 + 3 + 1) = 7.0
wm = weighted_mean(values, weights)  # 7.0
```

### `normalise`

Normalises a numeric value between a lower and an upper boundary. The result is a value between 0.0 and 1.0. If the
provided value exceeds any of the boundaries, the boundary value will automatically be chosen (defaults to 1.0 or 0.0).

It is possible to provide a smaller upper bound than lower bound, which will invert the function and provide the negated
value. As an example, if we normalise 4 between 0 and 10, we get 0.4. If we invert the boundaries to normalise 4 between
10 and 0, we get 0.6 (`1.0 - 0.4`).

Any invalid input (`None`) will result in 0.0 being returned.

```python
from pbu import normalise

# the "standard" case
norm1 = normalise(value=4, min_val=0, max_val=10)  # 0.4
# inverted normalisation
norm2 = normalise(value=4, min_val=10, max_val=0)  # 0.6
# exceeding the boundaries
norm3 = normalise(value=11, min_val=5, max_val=10)  # 1.0
# float works as well as integer
norm4 = normalise(value=-5.0, min_val=2.3, max_val=199.0)  # 0.0
# inverted exceeding boundaries
norm5 = normalise(value=-5, min_val=100, max_val=0.5)  # 1.0
# invalid inputs will return 0.0
norm6 = normalise(value=None, min_val=0, max_val=10)  # 0.0
norm7 = normalise(value=5, min_val=0, max_val=None)  # 0.0
```

Since version 1.0.1 a new parameter can be passed to the function that normalises the value, but can exceed the
boundaries provided by `min_val` and `max_val`.

```python
from pbu import normalise

norm1 = normalise(value=12, min_val=0, max_val=10, limit=False)  # 1.2
```

### `discretise`

Discretises a numeric value into a number of buckets determined by the provided precision and boolean flag indicating
whether to use the lower, upper or middle value of the bucket as the value for the bucket.

```python
from pbu import discretise

disc1 = discretise(value=4.5, precision=1.0, floor=True)  # 4.0
disc2 = discretise(value=4.5, precision=0.4, ceil=True)  # 4.8
disc3 = discretise(value=4.5, precision=0.4)  # 4.6 (assumes mid-point if neither floor nor ceil is set)
```
