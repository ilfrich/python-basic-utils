from typing import List, Union, Optional, Tuple
from statistics import mean


def weighted_mean(values: List[Union[float, int]], weights: List[Union[int, float]] = []) -> Optional[float]:
    """
    This will generate a mean value for the list of provided `values`, where each value is multiplied by the
    corresponding weight in the same position. If there are more `values` than `weights`, remaining values will receive
    weight 1.0. If there's more `weights` than `values`, it will only use the first `n` weights, where `n` is the number
    of values.
    :param values: the numeric values to generated a weighted mean over
    :param weights: the weights for each position of the values
    :return: the weighted average value of the provided values
    """
    if len(values) == 0:
        return None

    if weights is None or len(weights) == 0:
        return mean(values)

    total_weight = 0.0
    total_value = 0.0

    num_weights = len(weights)

    for idx, val in enumerate(values):
        current_weight = weights[-1] if num_weights < idx + 1 else weights[idx]
        total_weight += current_weight
        total_value += val * current_weight

    if total_weight == 0.0:
        return None

    return total_value / total_weight


def normalise(value: Union[float, int], min_val: Union[float, int], max_val: Union[float, int], limit=True,
              mid_point: Optional[Union[float, int]] = None) -> float:
    """
    Normalises the given input `value` between min_val and max_val as number between 0 and 1. If the min_val is provided
    larger than the max_val, the function will automatically invert them and provide the `1 - normalised_value`.
    :param value: the number to normalise
    :param min_val: the lower boundary representing 0.0
    :param max_val: the upper boundary representing 1.0
    :param limit: a boolean flag indicating whether a value between 0 and 1 is returned. Otherwise, values greater than
    1 and lower than 0 can be returned.
    :param mid_point: an optional mid-point to use for the normalisation. If provided, the normalisation will be
    performed between the min_val and the mid_point, and the mid_point and the max_val.
    :return: the normalised value expressed as where the value sits between min_val and max_val
    """
    if value is None or min_val is None or max_val is None:
        return 0.0  # invalid input

    min_value = min_val
    max_value = max_val
    inverted = False
    if max_val < min_val:
        inverted = True
        min_value = max_val
        max_value = min_val

    if value < min_value and limit is True:
        return 0.0 if inverted is False else 1.0

    if value > max_value and limit is True:
        return 1.0 if inverted is False else 0.0

    if max_value == min_value:
        return 0.5

    def _handle_return(norm):
        return norm if inverted is False else 1.0 - norm  # handle inverted flag

    if mid_point is None:
        return _handle_return((float(value) - float(min_value)) / (float(max_value) - float(min_value)))
    else:
        if value <= mid_point:
            # value is below mid-point (return 0 - 0.5)
            return _handle_return(((float(value) - float(min_value)) / (float(mid_point) - float(min_value))) * 0.5)
        else:
            # value is above mid-point (return 0.5 - 1.0)
            return _handle_return(
                (((float(value) - float(mid_point)) / (float(max_value) - float(mid_point))) * 0.5) + 0.5)


def discretise(value: Union[float, int], precision: Union[float, int] = 1, floor=False,
               ceil=False) -> Union[float, int]:
    """
    This function will round the given value to the nearest multiple of the given precision. There are 2 boolean flags
    available that can force the function to return the lower or upper boundary of a precision interval. If neither is
    set, the function will return the mid-point of the interval.
    :param value: the value to discretise
    :param precision: the precision to use for the discretisation
    :param floor: a boolean flag indicating whether the lower boundary of the precision interval should be returned
    :param ceil: a boolean flag indicating whether the upper boundary of the precision interval should be returned
    :return: the discretised value
    """
    if value is None:
        return None
    remainder = value % precision
    if ceil is True:
        return value - remainder + precision
    if floor is True:
        return value - remainder
    # mid point is default fallback
    return (value - remainder) + (precision * 0.5)


def compute_linear_function_parameters(xy_points: List[tuple]) -> Tuple[float, float, float]:
    """
    Computes m and b to minimise the error of all given points to map onto a linear function y = m * x + b.
    :param xy_points: a list of tuples representing the (x, y) points
    :return: a tuple with 3 elements containing the parameters m, b and the total (sum) error of all points when
    comparing against the linear function.
    """
    n = len(xy_points)

    # arrays to store all the elements
    x2 = []  # x squared
    xy = []  # x * y
    x = []  # all x-values
    y = []  # all y-values

    # collect all point data
    for (x_val, y_val) in xy_points:
        x2.append(x_val * x_val)
        xy.append(x_val * y_val)
        x.append(x_val)
        y.append(y_val)

    # determine m and b
    m = ((n * sum(xy)) - (sum(x) * sum(y))) / ((n * sum(x2)) - (sum(x) * sum(x)))
    b = (sum(y) - (m * sum(x))) / n

    # calculate total error
    error = 0.0
    for (x, y) in xy_points:
        error += abs(y - ((m * x) + b))

    return m, b, error
