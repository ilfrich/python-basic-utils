# Python Basic Utilities `pbu`

Available on [PyPi](https://pypi.org/project/pbu/)

**Table of Contents**

1. [Installation](#installation)
2. [Usage](#usage)
3. [Classes](#classes)
    1. [JSON](#json) - a JavaScript-like dictionary access helper
    2. [Logger](#logger) - a wrapper around the Python logging framework
    3. [TimeSeries](#timeseries) - powerful helper class to organise time series
    4. [AbstractMongoStore](#abstractmongostore) - helper and wrapper class for MongoDB access
    5. [AbstractMysqlStore](#abstractmysqlstore) - helper and wrapper class for MySQL access
    6. [BasicMonitor](#basicmonitor) - monitor class orchestrating regular operations
4. [Functions](#functions)
    1. [`list_to_json`](#list_to_json)
    2. [`default_options`](#default_options)
    

## Installation

Install via pip:

```bash
pip install pbu
```

## Usage

If you have a requirement.txt file, you can add `pbu` (replace 0.4.0 with latest available version or omit entirely to 
get the latest):

```bash
pbu==0.4.0
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
    { "date_time": datetime.now(), "measurement_1": 12, "measurement_2": 15 },
    { "date_time": datetime.now() + timedelta(hours=1), "measurement_1": 10, "measurement_2": 16 },
    { "date_time": datetime.now() + timedelta(hours=2), "measurement_1": 9, "measurement_2": 12 },
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

### AbstractMongoStore

Database store with helper functions for accessing MongoDB. Each store instance represents a single collection. This 
comes with an `AbstractMongoDocument` class, which can be used to model the document types you store within a MongoDB 
collection.

**Example**

```python
from pbu import AbstractMongoStore, AbstractMongoDocument

# this is the object type stored in the mongo store
class MyObjectType(AbstractMongoDocument):
    def __init__(self, val1, val2):
        # optional: provide id and data model version 
        super().__init__()
        self.attribute = val1
        self.attribute2 = val2,
    def to_json(self):
        # init with version and id
        result = super().to_json()
        # add attributes to dictionary and return
        result["attribute"] = self.attribute
        result["attribute2"] = self.attribute2
        return result
        
    @staticmethod
    def from_json(json):
        result = MyObjectType(json["attribute1"], json["attribute2"])
        # get _id and version attributes
        result.extract_system_fields(json)
        return result
        

class MyObjectStore(AbstractMongoStore):
    def __init__(self, mongo_url, db_name, collection_name, data_model_version):
        # provide object type class as de-serialisation class (providing from_json and to_json)
        super.__init__(mongo_url, db_name, collection_name, MyObjectType, data_model_version)


# create instance of store
store = MyObjectStore("mongodb://localhost:27017", "mydb", "colName", 5)

# create document using a dictionary
store.create({
    "version": 5,
    "attribute1": "a",
    "attribute2": 16,
})

# or use the type
doc = MyObjectType("a", 16)
doc.version = 5
doc_id = store.create(doc)

# update single document using helper functions
store.update(AbstractMongoStore.id_query(doc_id), 
             AbstractMongoStore.set_update(["attribute1", "attribute2"], ["b", 12]))


# returns a list of MyObjectType objects matching the version
list_of_results = store.query({ "version": 5 })
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

You can also pass a custom logger as `custom_logger` argument to the constructor. By default it will use the 
`pbu.Logger` and log major events such as start/stop/restart and errors.

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
t = threading.Thread(target=start_monitor_thread, args=(regular_monitor, ), daemon=True)
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

## Functions

### `list_to_json`

```python
from pbu import list_to_json

# assuming we have `my_store` as an instance of MongoDB store or MySQL store, you can:
list_of_dictionaries = list_to_json(item_list=my_store.get_all())  # output is a list of dictionaries
```

This function operates on lists of objects inheriting from `AbstractMongoDocument` or `AbstractMysqlDocument` and 
converts them into dictionaries using the `to_json()` method of any object passed into the function. Objects passed into
the function _require_ the `to_json()` method and need to return the dictionary representation of the object. This 
function is just a mapping shortcut.

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
