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
