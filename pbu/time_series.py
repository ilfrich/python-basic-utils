import math
import pandas as pd
from copy import copy
from pbu import JSON
from datetime import datetime, timedelta

DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class TimeSeries:
    """
    Helper class to manage time series with multiple data points. It offers the ability to align dates of different time
    series, force a fixed resolution and interpolate missing values, add another time series to an existing one or
    simply fill columns with defaults or remove columns.
    """

    # different types (auto-detect) for this time series
    TYPE_DICT_OF_LISTS = "dict_list"
    TYPE_LIST_OF_DICTS = "list_dict"

    # initial resolution (auto-detect)
    resolution = None

    def __init__(self, input_data, date_time_key="date_time", date_format=None,
                 time_zone=None):
        """
        Creates a new time series instance.
        :param input_data: the input data, which should be either a list of dictionaries, containing at least a date
        time key with values OR a map of lists, where the map contains at least a date time key with a list of values
        underneath.
        :param date_time_key: the key under which to find the date time information
        :param date_format: optional date format to parse dates if they're provided as string.
        :param time_zone: optional time zone for the date time column. Will default to the current time zone of the
        machine the code is running on.
        """
        # fallback for timezone internally, because Python older than 3.6 causes issues when importing pbu
        self.time_zone = time_zone
        if self.time_zone is None:
            self.time_zone = datetime.utcnow().astimezone().tzinfo

        # store fields
        self.data = input_data
        self.date_time_key = date_time_key
        self.date_format = date_format
        self.time_zone = time_zone

        # analyse input data
        self.type, self.keys = self._check_input_data()
        # parse dates if necessary
        self._parse_dates()
        # extract resolution if possible as well
        if self.type is not None:
            self.set_resolution()

    def set_resolution(self, custom_resolution=None):
        """
        Sets the resolution for the time series. If not resolution is provided, it will be detected automatically. The
        method doesn't return anything, but rather updates the resolution attribute of this instance.
        :param custom_resolution: a timedelta instance specifiying the gap between 2 date time values.
        """
        if custom_resolution is None:
            self.resolution = self.get_resolution()
        else:
            self.resolution = custom_resolution

    def get_resolution(self):
        """
        Auto-detects the resolution of the current date time column series. The method will iterate through all values
        of the date time column and measure the difference between timestamps, create a statistic for each difference
        and returns the most prominent result in the time series.
        :return: the most common timedelta between date time column values in the data.
        """
        last_dt = datetime.now().astimezone(self.time_zone)
        # collect stats
        stats = {}
        # determine datetime series from input data
        dt_series = self.get_dates()
        for dt in dt_series:
            if isinstance(dt, str):
                # string dates, need to be parsed
                if self.date_format is None:
                    raise AttributeError("Attempted to determine resolution, but didn't provide a date format for "
                                         "the date time column values, which are strings like: {}".format(dt))
                dt = datetime.strptime(dt, self.date_format).astimezone(self.time_zone)

            # check the diff from last datetime and collect diff in stats
            diff = dt - last_dt
            if diff not in stats:
                stats[diff] = 0
            stats[diff] += 1
            last_dt = dt

        # evaluate collected stats and find most common resolution
        res_max = 0
        current_max = None
        for resolution in stats:
            if stats[resolution] > res_max:
                res_max = stats[resolution]
                current_max = resolution

        if current_max is None:
            raise ValueError("Resolution could not be determined. This is most likely due to missing data.")
        return current_max

    def add_values(self, new_key, new_values):
        """
        Adds a new series to the existing one. We assume that the new series is already aligned to the date time column
        of this time series. The new values will simply be added to the existing data.
        :param new_key: the key under which the new data series will be available
        :param new_values: a list of all the values for the this key over the whole data series.
        """
        # don't add duplicate keys
        if new_key in self.keys:
            raise AttributeError("Can't add key '{}' to given time series, because it already contains that "
                                 "key".format(new_key))

        # check length of new data
        existing_data_length = len(self.data)
        if self.type == TimeSeries.TYPE_DICT_OF_LISTS:
            existing_data_length = len(self.data[self.date_time_key])

        # make sure the value series align in length, if not fill new series with values (max +2)
        new_values = TimeSeries._align_value_series_length(new_values, existing_data_length)
        if len(new_values) != existing_data_length:
            # difference in size is more than 2
            raise ValueError(
                "Failed to add new data series with length {} to existing data series with length {}".format(
                    len(new_values), existing_data_length))

        # add data
        if self.type == TimeSeries.TYPE_DICT_OF_LISTS:
            self.data[new_key] = new_values

        elif self.type == TimeSeries.TYPE_LIST_OF_DICTS:
            # translate to dictionary, add values and then translate back
            output = self.translate_to_dict_of_lists()
            output[new_key] = new_values
            self.data = TimeSeries(output, self.date_time_key, time_zone=self.time_zone).translate_to_list_of_dicts()

        self.keys.append(new_key)

    def fill_values(self, new_key, constant_value):
        """
        Adds a new data series to the existing data by filling it up completely with a constant value. The method does
        not return any results, but instead updates the instance's data directly.
        :param new_key: the key under which to store the new series
        :param constant_value: the constant value to add for each entry in the new series
        """
        # check for duplicates
        if new_key in self.keys:
            raise AttributeError(
                "Can't add key '{}' to given time series as constant, because it already exists.".format(new_key))

        # add data
        if self.type == TimeSeries.TYPE_DICT_OF_LISTS:
            self.data[new_key] = [constant_value] * len(self.data[self.date_time_key])
        else:
            output = self.translate_to_dict_of_lists()
            output[new_key] = [constant_value] * len(self.data)
            self.data = TimeSeries(output, self.date_time_key, time_zone=self.time_zone).translate_to_list_of_dicts()

    def get_values(self, selected_key):
        """
        Extracts the values of a given column as list from the current time series.
        :param selected_key: the key to retrieve
        :return: a list of values representing this series
        """
        if self.type == TimeSeries.TYPE_DICT_OF_LISTS:
            # check if the key is available
            if selected_key not in self.data:
                raise ValueError("Requested key {} could not be found in input data".format(selected_key))
            # return the series
            dt_series = self.data[selected_key]
            return dt_series
        elif self.type == TimeSeries.TYPE_LIST_OF_DICTS:
            # check if the key exists in the first item
            if selected_key not in self.data[0]:
                raise ValueError("Requested key {} could not be found in first item of input data".format(selected_key))
            # return the extracted column
            dt_series = list(map(lambda x: x[selected_key], self.data))
            return dt_series

        raise AttributeError("Data series doesn't have a valid type. Extraction of value series not possible.")

    def get_dates(self):
        """
        Extracts the values of the date time column as list from the current time series.
        :return: a list of datetime objects
        """
        if self.type == TimeSeries.TYPE_DICT_OF_LISTS:
            return self.data[self.date_time_key]
        elif self.type == TimeSeries.TYPE_LIST_OF_DICTS:
            return list(map(lambda x: x[self.date_time_key], self.data))

        raise AttributeError("Data series doesn't have a valid type. Extraction of date time series not possible.")

    def get_start_date(self):
        """
        Extracts the first date in the date time series.
        :return: a datetime object representing the first entry in the time series.
        """
        return self._get_date_value(0)

    def get_end_date(self):
        """
        Extracts the last date in the date time series.
        :return: a datetime object representing the last entry in the time series
        """
        return self._get_date_value(-1)

    def add_series(self, time_series, keys_to_add=None):
        """
        Adds a new time series to this existing one. The first step is to align the new time series with this instance's
        date time. Then the columns of the argument will be added one by one to this instance. The method doesn't return
        anything, but directly updates the existing data.
        :param time_series: a time series instance to add
        :param keys_to_add: optional a list of keys to add that exist in the new series. If omitted, the method will add
        all columns it finds (except the date time column).
        """
        # check type
        if not isinstance(time_series, TimeSeries):
            raise ValueError("Provided time series is not of type TimeSeries, but {}".format(type(time_series)))
        # prepare keys
        if keys_to_add is None:
            # fallback to all keys of the series
            keys_to_add = time_series.keys

        # check for duplicate keys
        for key in keys_to_add:
            if key in self.keys:
                raise ValueError("Attempting to add key {} to existing data series, which already has "
                                 "such a key".format(key))

        # first align current data set (ensure it is aligned)
        resolution = self.get_resolution()  # resolution of existing series
        self.align_to_resolution(resolution)

        # also align the new time series to the given resolution and time frame
        time_series.align_to_resolution(resolution=resolution, start_date=self.get_start_date(),
                                        end_date=self.get_end_date())
        for key in time_series.keys:
            self.add_values(key, time_series.get_values(key))
        _, self.keys = self._check_input_data()

    def remove_series(self, keys_to_remove):
        """
        Removes a column from the time series. The method will not return anything, but directly modify the data of this
        instance.
        :param keys_to_remove: the key to remove
        """
        if isinstance(keys_to_remove, str):
            keys_to_remove = [keys_to_remove]

        if self.date_time_key in keys_to_remove:
            raise AttributeError("Can't remove date time key {}".format(self.date_time_key))

        if self.type == TimeSeries.TYPE_DICT_OF_LISTS:
            for key in keys_to_remove:
                del self.data[key]
        else:
            # translate
            output = self.translate_to_dict_of_lists()
            for key in keys_to_remove:
                del output[key]
            self.data = TimeSeries(output, self.date_time_key, time_zone=self.time_zone).translate_to_list_of_dicts()
        _, self.keys = self._check_input_data()

    def align_to_resolution(self, resolution=None, start_date=None, end_date=None):
        """
        Aligns the current input data to the most dominant resolution. This will keep the first date of the datetime
        column and then interpolate values in between and use existing values to fill the data series with a fixed
        interval between each data point. This will update the original data of this time series. The method doesn't
        return anything, but directly modifies the instance's data.
        :param resolution: optional, if provided will force a specific resolution and interpolate/skip values to match
        that resolution
        :param start_date: an optional start date, in case you want to prepend or cut the existing data series to a
        specific time frame. If not provided the first date from the time series will be used.
        :param end_date: an optional end date, in case you want to append or cut the existing data series to a specific
        time frame. If not provided, the last date from the time series will be used.
        """
        # fetch resolution and tolerance
        if resolution is None:
            resolution = self.get_resolution()
        tolerance = resolution / 2

        # start date (use start date minus resolution to match the first entry perfectly)
        current_date = self.get_start_date()
        if start_date is not None:
            current_date = start_date
        if end_date is None:
            end_date = self.get_end_date()

        # standardise initial data
        main_data = self.data
        if self.type == TimeSeries.TYPE_DICT_OF_LISTS:
            main_data = self.translate_to_list_of_dicts()

        # runtime variables for the alignment operation below
        prev_value = None
        current_original_data_index = 0
        result = []
        # as long as we haven't reached the end date, keep adding values
        while current_date <= end_date:
            is_last = False
            if current_original_data_index >= len(main_data) - 1:
                is_last = True

            # ensure we don't run into index errors (repeat last element until end-date in worst-case scenario)
            if current_original_data_index >= len(main_data):
                current_original_data_index = len(main_data) - 1  # might cause endless loop in skip branch

            # extract date information and time delta
            original_date = main_data[current_original_data_index][self.date_time_key]
            diff_seconds = (current_date - original_date).total_seconds()

            # close enough
            if current_date == original_date or abs(diff_seconds) < tolerance.total_seconds():
                # fetch the value from the original data
                prev_value = main_data[current_original_data_index]
                # update date of this entry to current date
                prev_value[self.date_time_key] = current_date
                # add to result
                result.append(prev_value)
                # remember to increment the key for next item and add resolution to current date
                current_original_data_index += 1
                current_date += resolution

            # implies the data point is no where close, skip this entry
            elif current_date > original_date:
                prev_value = main_data[current_original_data_index]

                if is_last:
                    # we've already reached the end of the data series, fill with last value
                    if current_date < end_date:
                        missing_entries = math.floor((end_date - current_date) / resolution) + 1
                        for index in range(0, missing_entries):
                            # copy last item
                            new_item = copy(prev_value)
                            # update timestamp
                            new_item[self.date_time_key] = current_date + resolution
                            # add to result
                            result.append(new_item)
                            # remember for next loop
                            prev_value = new_item
                            # increment timestamp
                            current_date += resolution
                    if current_date == end_date:
                        # breaks the while loop

                        current_date += resolution
                else:
                    current_original_data_index += 1

            # implies that the next data point is in the future and we need to interpolate missing values
            elif current_date < original_date:
                # compute gaps
                gaps = {}
                next_value = main_data[current_original_data_index]

                if prev_value is None:
                    prev_value = next_value
                    # special handling for initial result to prefill with first value
                    if len(result) == 0:
                        prev_value[self.date_time_key] = current_date
                for key in self.keys:
                    gaps[key] = next_value[key] - prev_value[key]
                missing_entries = math.floor((original_date - current_date) / resolution)
                # interpolate entries starting from prev_value
                for index in range(0, missing_entries):
                    new_item = {
                        self.date_time_key: prev_value[self.date_time_key] + resolution
                    }
                    for key in self.keys:
                        new_item[key] = prev_value[key] + (gaps[key] / missing_entries)

                    prev_value = new_item
                    result.append(new_item)
                    # update current date with latest added value
                    current_date = new_item[self.date_time_key]
                # increment resolution and index
                current_date += resolution
                current_original_data_index += 1

        # store aligned data
        if self.type == TimeSeries.TYPE_DICT_OF_LISTS:
            # convert if necessary
            self.data = TimeSeries(input_data=result,
                                   date_time_key=self.date_time_key,
                                   time_zone=self.time_zone).translate_to_dict_of_lists()
        else:
            # already in correct format
            self.data = result

    def translate_to_list_of_dicts(self, date_format=None):
        """
        Returns the data of this instance as a list containing dictionary items with all keys and the datetime key
        being contained in each item of the list.
        :param date_format: optional date format to render date_time columns as strings rather than native datetime
        :return: a list of dictionaries
        """
        if self.type == TimeSeries.TYPE_LIST_OF_DICTS:
            # already in correct format
            result = copy(self.data)
            # format date_time column if necessary
            if date_format is not None:
                result = list(map(lambda x: TimeSeries._format_date_list_of_dict(x, self.date_time_key, date_format),
                                  result))
            return result
        else:
            # need translation
            result = []
            # iterate through all values
            for index in range(0, len(self.data[self.date_time_key]), 1):
                # iterate through all keys for current index and add to result
                item = {}
                for key in self.data:
                    value = self.data[key][index]
                    if key == self.date_time_key and date_format is not None:
                        # handle datetime rendering
                        value = value.strftime(date_format)
                    # add key to current item
                    item[key] = value
                # append finished item to list of dicts
                result.append(item)
            # return list of dicts
            return result

    def translate_to_dict_of_lists(self, date_format=None):
        """
        Returns the data of this instance as a dictionary with keys for each data series, including the date time key.
        Underneath each key, all values (sorted by date time) are stored in a simple list containing the values as
        primitive types.
        :param date_format: optional date format to render date_time columns as strings rather than native datetime
        objects
        :return: a dictionary containing lists
        """
        if self.type == TimeSeries.TYPE_DICT_OF_LISTS:
            # already in correct format
            result = copy(self.data)
            # format date_time column if necessary
            if date_format is not None:
                result[self.date_time_key] = list(map(lambda x: x.strftime(date_format), result[self.date_time_key]))
            return result
        else:
            # need translation
            result = {}
            # init keys
            for key in self.data[0]:
                result[key] = []

            # map to lists
            for item in self.data:
                for key in item:
                    value = item[key]
                    if key == self.date_time_key and date_format is not None:
                        # handle datetime rendering
                        value = value.strftime(date_format)
                    result[key].append(value)
            # return dict of lists
            return result

    def to_pd_data_frame(self):
        """
        Converts the time series into a pandas DataFrame with a given time index
        :return: a pandas DataFrame with the date_time column set as the index
        """
        df = pd.DataFrame(self.translate_to_dict_of_lists(date_format=None)).set_index(self.date_time_key)
        for col in df:
            if col != self.date_time_key:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df

    @staticmethod
    def create_date_range(from_date, to_date=None, num_points=None, resolution=timedelta(minutes=5),
                          include_start_date=False, time_zone=None):
        """
        Creates a list of datetime instances in a given resolution an a given time frame.
        :param from_date: the start date for the time series
        :param to_date: the end date for the time series (default: None)
        :param num_points: optional: the number of points to add (use only num_points or to_date)
        :param resolution: the resolution for the time series (default 5 minutes)
        :param include_start_date: boolean flag to indicate whether to add the from date or not (default: False)
        :param time_zone: optional the timezone for which to create the date range (default UTC)
        :return: a list of datetime objects matching the provided resolution and from/to date.
        """
        if num_points is not None and to_date is not None:
            raise AttributeError("Cannot provide to_date and num_points at the same time")

        # internal fallback to default, to avoid import issues with old python versions
        effective_time_zone = time_zone
        if effective_time_zone is None:
            effective_time_zone = datetime.utcnow().astimezone().tzinfo

        # localize dates
        from_date = from_date.astimezone(effective_time_zone)
        if to_date is not None:
            to_date = to_date.astimezone(effective_time_zone)

        # optionally offset start date
        if not include_start_date:
            from_date += resolution

        # if num_points are provided, compute end date
        if num_points is not None:
            num_points -= 1
            to_date = from_date + (num_points * resolution)

        if from_date > to_date:
            return [from_date]

        result = []
        current_date = from_date - resolution
        while current_date < to_date:
            current_date += resolution
            result.append(current_date)

        return result

    @staticmethod
    def _format_date_list_of_dict(item, date_time_key, date_format):
        item[date_time_key] = item[date_time_key].strftime(date_format)
        return item

    @staticmethod
    def _align_value_series_length(new_values, length):
        if len(new_values) + 1 == length:
            # missing one value, append last value again
            new_values.append(new_values[-1])
        elif len(new_values) + 2 == length:
            # missing two values, prepend first, append last
            new_values = [new_values[0]] + new_values + [new_values[-1]]
        elif len(new_values) - 1 == length:
            # remove last item
            new_values = new_values[0:len(new_values) - 1]
        elif len(new_values) - 2 == length:
            # remove first and last
            new_values = new_values[1:len(new_values) - 1]
        return new_values

    def _get_date_value(self, index):
        """
        Extracts a given date from the date time series.
        :param index: the index to retrieve (can be any valid Python list accessor)
        :return: the date time at the given index
        :raise IndexError, if the index provided doesn't exist.
        """
        if self.date_time_key is None:
            raise AttributeError("Current time series doesn't provide a date_time_key")

        if self.type == TimeSeries.TYPE_LIST_OF_DICTS:
            return self.data[index][self.date_time_key]
        elif self.type == TimeSeries.TYPE_DICT_OF_LISTS:
            return self.data[self.date_time_key][index]

    def _check_input_data(self):
        """
        Helper method to determine the type of the input data and the extract the keys.
        :return: a tuple containing (1) the type of the input data and (2) the keys contained in the input data.
        """
        if self.data is None or self.date_time_key is None:
            # no association between input data and date_time
            return None, []

        if isinstance(self.data, (dict, JSON)) and self.date_time_key in self.data:
            # dictionary of data series, including other keys
            result = []
            for key in self.data:
                if key != self.date_time_key:
                    result.append(key)
            return TimeSeries.TYPE_DICT_OF_LISTS, result

        if isinstance(self.data, list) and len(self.data) > 0 and isinstance(self.data[0], (dict, JSON)):
            # list of dictionaries
            result = []
            for key in self.data[0]:
                if key != self.date_time_key:
                    result.append(key)
            return TimeSeries.TYPE_LIST_OF_DICTS, result

        if isinstance(self.data, list) and len(self.data) == 0:
            return TimeSeries.TYPE_LIST_OF_DICTS, []

        raise ValueError("Provided input data structure is not supported. Only a dictionary of lists or a list of "
                         "dictionaries is allowed. Found type of input_data: {}".format(type(self.data)))

    def _parse_dates(self):
        """
        Helper method to parse dates in the date column. If the dates are already dates, no change is performed. It
        can detect unix timestamps (float or int) and string representation of dates (using the date_format provided in
        the constructor).
        The method does not return any result, but rather modifies the data stored in this instance.
        """
        if len(self.get_dates()) == 0:
            if self.type == TimeSeries.TYPE_DICT_OF_LISTS:
                self.data[self.date_time_key] = []
            return
        dates = self.get_dates()
        if isinstance(dates[0], datetime):
            # already in correct format
            return

        converted_dates = []
        if isinstance(dates[0], (float, int)):
            # timestamp
            for dt in dates:
                converted_dates.append(datetime.fromtimestamp(dt, tz=self.time_zone))
        elif isinstance(dates[0], str):
            if self.date_format is None:
                raise AttributeError("Could not parse dates, because of missing date format.")
            # datetime string
            for dt in dates:
                converted_dates.append(datetime.strptime(dt, self.date_format).astimezone(self.time_zone))
        else:
            raise ValueError("Could not parse dates of input data set for type {}".format(type(dates[0])))

        # update existing dates
        if self.type == TimeSeries.TYPE_DICT_OF_LISTS:
            self.data[self.date_time_key] = converted_dates
        else:
            # translate
            output = self.translate_to_dict_of_lists()
            output[self.date_time_key] = converted_dates
            self.data = TimeSeries(output, date_time_key=self.date_time_key,
                                   time_zone=self.time_zone).translate_to_list_of_dicts()
