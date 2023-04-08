from typing import Any, List, Optional, Callable


def default_options(default: dict = {}, override: dict = None, allow_unknown_keys: bool = True) -> dict:
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


def list_find_one(filter_func: Callable, item_list: List[Any]) -> Optional[Any]:
    """
    Finds the first item in the list that matches the filter function.
    :param filter_func: a lambda used to filter items in the item_list
    :param item_list: a list of items to check against
    :return: the first item in the list that matches the filter function or None, if no item matches.
    """
    if item_list is None or not isinstance(item_list, list) or len(item_list) == 0:
        return None

    filtered = list(filter(filter_func, item_list))
    if len(filtered) == 0:
        return None

    return filtered[0]


def list_map_filter(item_list: List[Any], filter_func: Callable, map_func: Callable, filter_first=True) -> List[Any]:
    """
    Shortcut function for mapping and filtering a list of items.
    :param item_list: a list of items to filter and map
    :param filter_func: the filter lambda
    :param map_func: the map lambda
    :param filter_first: a boolean flag whether we call filter first and then map (True) or map first and then filter
    (False)
    :return: the result of the filter + map operation cast to a list
    """
    if item_list is None:
        return None
    if filter_first:
        interm_result = item_list
        if filter_func is not None:
            interm_result = list(filter(filter_func, interm_result))
        if map_func is not None:
            interm_result = list(map(map_func, interm_result))
        return interm_result

    interm_result = item_list
    if map_func is not None:
        interm_result = list(map(map_func, interm_result))
    if filter_func is not None:
        interm_result = list(filter(filter_func, interm_result))

    return interm_result


def list_join(item_list: List[Any], join_token: str = ",") -> str:
    """
    Joins a list of items with the provided join token. The list can contain other types than strings, as they get cast
    to string to avoid any errors.
    :param item_list: a list of items
    :param join_token: a token to join the items by
    :return: a string of the joined list.
    """
    return join_token.join(list(map(lambda x: str(x), item_list)))


def not_none(item_list: List[Any]) -> List[Any]:
    """
    Filters a list of items for items that are not None.
    :param item_list: a list of items
    :return: a list of items that are not None
    """
    if isinstance(item_list, list):
        return list(filter(lambda x: x is not None, item_list))
    raise ValueError(f"You can only pass a list to not_none, not {type(item_list)}")
