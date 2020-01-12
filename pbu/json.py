
class JSON(dict):
    """
    Dictionary extension to allow using the "dot-notation" to traverse and manipulate dictionaries in the same fashion
    as in Javascript, thus avoiding the square brackets and string key handling.

    Usage example:

    >>> from pbu import JSON
    >>> my_obj = JSON({"initial": "content"})
    >>> print(my_obj.initial)
    content

    >>> my_obj.initial = {"a": 5, "b": 3}
    >>> print(my_obj.initial.a + my_obj.initial.b)
    8
    >>> my_obj.initial.b = 13
    >>> print(my_obj.initial.a + my_obj.initial.b)
    18

    >>> my_obj.extension = 10
    >>> print(my_obj.extension)
    10

    """
    def __init__(self, data=None):
        """
        Overrides the constructor to handle input data vs. missing input data. If a dictionary is provided, it will be
        checked for dictionary sub-structures, which will be converted into JSON objects as well.
        :param data: optional initial content for the JSON object, will be provided to the dictionary as initial content
        """
        if data is None:
            # init with empty dictionary content
            super().__init__({})
        else:
            # init with provided data after conversion
            data = JSON._convert_input(data)
            super().__init__(data)

    def __getattr__(self, item):
        """
        Attribute accessor, which first looks up the attribute requested in the dictionary content and then attempts to
        access the native attribute of the dictionary.
        :param item: the attribute to retrieve
        :raise AttributeError in case the attribute does not exist in the dictionary or the native dictionary class.
        :return: If the requested item exists in the dictionary, the dictionary entry will be returned. Otherwise the
        method will attempt to call the native attribute getter, which may lead to an AttributeError.
        """
        if item in self:
            # provided attribute is a key in the dictionary content
            return self[item]

        # use native way (may throw AttributeError)
        super().__getattribute__(item)

    def __setattr__(self, key, value):
        """
        Any update to our dictionary needs to be converted into JSON objects if necessary, while still maintaining
        access to native attributes.
        :param key: the key which the caller wants to manipulate
        :param value: the value that is to be set for the given key. If this is a dictionary update, the input will be
        converted, by checking for dictionary sub-structures and converting them into JSON sub-structures.
        """
        if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict) and not isinstance(value[0], JSON):
            # convert list of dictionaries in list of JSON objects
            value = list(map(lambda x: JSON(x), value))
            self[key] = value
        elif isinstance(value, dict) and not isinstance(value, JSON):
            # convert dictionary into JSON object
            value = JSON(value)
            self[key] = value
        elif key in self:
            self[key] = value
        elif hasattr(self, key):
            # attribute exists, but is not a dictionary key, use native access
            super().__setattr__(key, value)
        else:
            # attribute doesn't exist, update dictionary content by key
            self[key] = value

    def __str__(self):
        return str(self.revert_to_dict())

    __repr__ = __str__

    @staticmethod
    def _convert_input(arg):
        """
        Analyses the provided input for a JSON object (initial dictionary) for any dictionary sub-structures. If it
        detects any those will be converted into JSON objects as well.
        :param arg: the constructor argument provided to the constructor of this class
        :return: the original constructor argument if no dictionary sub-structure could be found or a converted
        sub-structure containing JSON objects instead of dictionaries.
        """
        for key in arg:
            if isinstance(arg[key], list) and len(arg[key]) > 0 and isinstance(arg[key][0], dict) and not isinstance(arg[key][0], JSON):
                # iterate through items
                arg[key] = list(map(lambda x: JSON(x), arg[key]))
            if isinstance(arg[key], dict) and not isinstance(arg[key], JSON):
                # convert into JSON object
                arg[key] = JSON(arg[key])
        return arg

    def revert_to_dict(self):
        result = {}
        for key in self:
            if isinstance(self[key], JSON):
                result[key] = self.__getattr__(key).revert_to_dict()
            else:
                result[key] = self.__getattr__(key)
        return result
