from typing import List, Union, Optional
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
        current_weight = 1.0 if num_weights < idx + 1 else weights[idx]
        total_weight += current_weight
        total_value += val * current_weight

    if total_weight == 0.0:
        return None

    return total_value / total_weight
