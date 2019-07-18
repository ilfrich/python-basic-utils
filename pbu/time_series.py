import math
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
                 time_zone=datetime.utcnow().astimezone().tzinfo):
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

    def _check_input_data(self):
        """
        Helper method to determine the type of the input data and the extract the keys.
        :return: a tuple containing (1) the type of the input data and (2) the keys contained in the input data.
        """
        if self.data is None or self.date_time_key is None:
            # no association between input data and date_time
            return None, []

        if type(self.data) == dict and self.date_time_key in self.data:
            # dictionary of data series, including other keys
            result = []
            for key in self.data:
                if key != self.date_time_key:
                    result.append(key)
            return TimeSeries.TYPE_DICT_OF_LISTS, result

        if type(self.data) == list and len(self.data) > 0 and type(self.data[0]) == dict:
            # list of dictionaries
            result = []
            for key in self.data[0]:
                if key != self.date_time_key:
                    result.append(key)
            return TimeSeries.TYPE_LIST_OF_DICTS, result

        raise ValueError("Provided input data structure is not supported. Only a dictionary of lists or a list of "
                         "dictionaries is allowed. Found type of input_data: {}".format(type(self.data)))

    def _parse_dates(self):
        """
        Helper method to parse dates in the date column. If the dates are already dates, no change is performed. It
        can detect unix timestamps (float or int) and string representation of dates (using the date_format provided in
        the constructor).
        The method does not return any result, but rather modifies the data stored in this instance.
        """
        dates = self.get_values(self.date_time_key)
        if type(dates[0]) == datetime:
            # already in correct format
            return

        converted_dates = []
        if type(dates[0]) is float or type(dates[0]) is int:
            # timestamp
            for dt in dates:
                converted_dates.append(datetime.fromtimestamp(dt, tz=self.time_zone))
        elif type(dates[0]) is str:
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
            self.data = TimeSeries(converted_dates, date_time_key=self.date_time_key,
                                   time_zone=self.time_zone).translate_to_list_of_dicts()

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
        dt_series = self.get_values(self.date_time_key)
        for dt in dt_series:
            if type(dt) == str:
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
        if len(new_values) != existing_data_length:
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
            self.data = TimeSeries(output, self.date_time_key).translate_to_list_of_dicts()

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
            self.data = TimeSeries(output, self.date_time_key).translate_to_list_of_dicts()

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

        raise AttributeError("Data series doesn't have a valid type. Extraction of date time series not possible.")

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
        if type(time_series) != TimeSeries:
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

        # first align current data set
        resolution = self.get_resolution()  # resolution of existing series
        self.align_to_resolution(resolution)

        # also align the new time series to the given resolution and time frame
        date_series = self.get_values(self.date_time_key)
        time_series.align_to_resolution(resolution=resolution, start_date=date_series[0], end_date=date_series[-1])

        for key in time_series.keys:
            self.add_values(key, time_series.get_values(key))

    def remove_series(self, keys_to_remove):
        """
        Removes a column from the time series. The method will not return anything, but directly modify the data of this
        instance.
        :param keys_to_remove: the key to remove
        """
        if type(keys_to_remove) == str:
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
            self.data = TimeSeries(output, self.date_time_key).translate_to_list_of_dicts()

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
        current_date = self.get_values(self.date_time_key)[0] - resolution
        if start_date is not None:
            current_date = start_date - resolution
        if end_date is None:
            end_date = self.get_values(self.date_time_key)[-1]

        # standardise initial data
        original_data = self.data
        if self.type == TimeSeries.TYPE_DICT_OF_LISTS:
            original_data = self.translate_to_list_of_dicts()

        # runtime variables for the alignment operation below
        prev_value = None
        current_original_data_index = 0
        result = []

        # as long as we haven't reached the end date, keep adding values
        while current_date < end_date:

            # extract date information and time delta
            current_date = current_date + resolution
            original_date = original_data[current_original_data_index][self.date_time_key]
            diff_seconds = (current_date - original_date).total_seconds()

            # close enough
            if current_date == original_date or abs(diff_seconds) < tolerance.total_seconds():
                prev_value = original_data[current_original_data_index]
                current_original_data_index += 1
                result.append(prev_value)

            # implies the data point is no where close, skip this entry
            elif current_date > original_date:
                prev_value = original_data[current_original_data_index]
                current_original_data_index += 1

            # implies that the next data point is in the future and we need to interpolate missing values
            elif current_date < original_date:

                # compute gaps
                gaps = {}
                next_value = original_data[current_original_data_index]
                if prev_value is None:
                    prev_value = next_value
                for key in self.keys:
                    gaps[key] = next_value[key] - prev_value[key]
                missing_entries = math.floor((original_date - current_date) / resolution)

                # interpolate entries starting from prev_value
                for index in range(0, missing_entries):
                    new_item = {
                        self.date_time_key: prev_value[self.date_time_key] + resolution
                    }
                    for key in self.keys:
                        new_item[key] = prev_value[key] + gaps[key]

                    prev_value = new_item
                    result.append(new_item)

        # store aligned data
        if self.type == TimeSeries.TYPE_DICT_OF_LISTS:
            # convert if necessary
            self.data = TimeSeries(input_data=result, date_time_key=self.date_time_key).translate_to_dict_of_lists()
        else:
            # already in correct format
            self.data = result

    def translate_to_list_of_dicts(self):
        """
        Returns the data of this instance as a list containing dictionary items with all keys and the datetime key
        being contained in each item of the list.
        :return: a list of dictionaries
        """
        if self.type == TimeSeries.TYPE_LIST_OF_DICTS:
            # already in correct format
            return self.data
        else:
            # need translation
            result = []
            # iterate through all values
            for index in range(0, len(self.data[self.date_time_key]), 1):
                # iterate through all keys for current index and add to result
                item = {}
                for key in self.data:
                    # add key to current item
                    item[key] = self.data[key][index]
                # append finished item to list of dicts
                result.append(item)
            # return list of dicts
            return result

    def translate_to_dict_of_lists(self):
        """
        Returns the data of this instance as a dictionary with keys for each data series, including the date time key.
        Underneath each key, all values (sorted by date time) are stored in a simple list containing the values as
        primitive types.
        :return: a dictionary containing lists
        """
        if self.type == TimeSeries.TYPE_DICT_OF_LISTS:
            # already in correct format
            return self.data
        else:
            # need translation
            result = {}
            # init keys
            for key in self.data[0]:
                result[key] = []

            # map to lists
            for item in self.data:
                for key in item:
                    result[key].append(item[key])
            # return dict of lists
            return result

    @staticmethod
    def create_date_range(from_date, to_date=datetime.now(), resolution=timedelta(minutes=5)):
        """
        Creates a list of datetime instances in a given resolution an a given time frame.
        :param from_date: the start date for the time series
        :param to_date: the end date for the time series (default: now)
        :param resolution: the resolution for the time series (default 5 minutes)
        :return: a list of datetime objects matching the provided resolution and from/to date.
        """
        if from_date > to_date:
            return [from_date]

        result = []
        current_date = from_date - resolution
        while current_date < to_date:
            current_date += resolution
            result.append(current_date)

        return result
