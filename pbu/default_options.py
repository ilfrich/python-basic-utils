from typing import Any, List


def default_options(default: dict = {}, override: dict = None, allow_unknown_keys: bool = True):
    """
    Combines the dictionaries provided as parameters into one, where keys in override will replace keys in default.
    The inputs are not mutated.
    :param default: the default dictionary containing fall-backs
    :param override: the custom options provided by a user
    :param allow_unknown_keys: flag to determine whether parameters from the override for which there is no default
    should be included as well
    :return: a dictionary containing the combined keys (or just default keys) and values from the override using
    defaults as fall-back.
    """
    if override is None or default is None:
        return default

    result = {}
    for key in default:
        result[key] = default[key]
    for key in override:
        if key in default or allow_unknown_keys:
            result[key] = override[key]

    return result


def default_value(value: Any, fallback: Any, disallowed: List[Any] = [None]) -> Any:
    """
    Checks whether the provided value is (by default) None or matches any other disallowed value, as provided. If the
    value is disallowed, the fallback will be returned.
    :param value: the value to check
    :param fallback: the fallback in case the check fails
    :param disallowed: the list of values to check the value against, if it matches any of them, the fallback will be
    returned
    :return: the value or the fallback, depending on the outcome of the check
    """
    if value in disallowed:
        return fallback

    return value
