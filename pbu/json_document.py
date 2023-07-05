import warnings
from datetime import datetime, date, time
from abc import ABC, abstractmethod
from typing import Optional, List, Dict


def _handle_value_to_string(value, custom_mapping=None):
    if value is None or isinstance(value, (str, int, float, bool)):
        # primitive type
        return value
    elif isinstance(value, JsonDocument):
        # value is another json document
        return value.to_json()
    elif isinstance(value, list):
        if len(value) == 0:
            # empty list
            return []
        # can contain any supported value
        return list(map(lambda val: _handle_value_to_string(val, custom_mapping), value))
    elif isinstance(value, dict):
        # handle non-string keys
        result = {}
        for k, v in value.items():
            result[str(k)] = _handle_value_to_string(v)
        return result
    elif isinstance(value, (datetime, date, time)):
        if custom_mapping is not None and isinstance(custom_mapping, str):
            return value.strftime(custom_mapping)
    return str(value)  # attempt to convert value to a string


def _parse_json_value(value, custom_mapping=None):
    if value is None or isinstance(value, (float, bool)):
        # primitive type
        return value
    if isinstance(value, (str, int)):
        # could be datetime
        if custom_mapping is not None:
            if isinstance(custom_mapping, str):
                # simply a datetime string (default behaviour)
                return datetime.strptime(value, custom_mapping)
            if isinstance(custom_mapping, tuple):
                # first token is the type, second token the format
                return custom_mapping[0].strptime(value, custom_mapping[1])
            if callable(custom_mapping):
                # custom mapping is a function
                return custom_mapping(value)
        return value
    elif isinstance(value, list):
        # can contain any supported value
        return list(map(lambda val: _parse_json_value(val, custom_mapping), value))
    elif isinstance(value, dict):
        if isinstance(custom_mapping, type) and issubclass(custom_mapping, JsonDocument):
            # custom mapping is a type, attempt to convert dictionary into instance of that type
            return custom_mapping.from_json(value)
        result = {}
        for k, v in value.items():
            result[k] = _parse_json_value(v, custom_mapping)
        return result
    return value


class JsonDocument(ABC):
    def __init__(self):
        pass

    def extract_system_fields(self, json: dict):
        """
        Extracts the id and version from a JSON object or dictionary and maps them to the current instances attributes.
        :param json: the json object or dictionary from which to extract information.
        """
        # check if the get_attribute_mapping method is overridden
        attr_mapping = self._get_attribute_mapping()
        dt_mapping = self._get_custom_mapping()
        if attr_mapping is None:
            return

        # evaluate attribute mapping
        for key in attr_mapping:
            if attr_mapping[key] in json:
                json_val = json[attr_mapping[key]]
                self.__setattr__(key, _parse_json_value(json_val, dt_mapping.get(key, None)))

    def to_json(self) -> dict:
        """
        Returns a serializable representation of this document as dictionary or JSON object.
        :return: a dictionary or JSON object providing the data contained within this document
        """
        result = {}
        attr_mapping = self._get_attribute_mapping()
        custom_mapping = self._get_custom_mapping()
        if attr_mapping is not None:
            for key in attr_mapping:
                if self.__getattribute__(key) is not None:
                    # jsonify value
                    result[attr_mapping[key]] = _handle_value_to_string(self.__getattribute__(key),
                                                                        custom_mapping.get(key, None))

        return result

    @classmethod
    def from_json(cls, json: dict):
        """
        Receives a dictionary or JSON object and returns an instance of this JsonDocument subclass.
        :param json: a dictionary or JSON object instance
        :return: an instance of a subclass of JsonDocument
        """
        obj = cls()
        obj.extract_system_fields(json)
        return obj

    def get_attribute_mapping(self) -> dict:
        """
        Provides a mapping from internal attribute names to JSON attribute names.
        """
        pass

    def get_custom_mapping(self) -> dict:
        """
        Provides a list of internal attributes that represent datetime attributes or custom JsonDocuments, and the value
        is the datetime type (date, datetime, time) and format string provided as tuple or the type that it should be
        parsed into.
        """
        pass

    def _get_attribute_mapping(self) -> Optional[dict]:
        """
        Internal method used to find out if the subclass defines an attribute mapping. If the subclass defines an
        attribute mapping and returns a dictionary, the attribute mapping will be returned. Otherwise, None will be
        returned, which will be used by the to_json and extract_system_fields method to map all primitive fields from
        the de-serialised class to JSON and back.
        """
        # find out if the subclass defines the method
        defining_class = self.get_attribute_mapping.__func__.__qualname__.split(".")[0]
        if defining_class == "JsonDocument":
            return None

        # check if the subclass method returns a dictionary
        attr_mapping = self.get_attribute_mapping()
        if not isinstance(attr_mapping, dict):
            return None

        # mapping provided by subclass, return it
        return attr_mapping

    def _get_custom_mapping(self) -> Optional[dict]:
        """
        Internal method used to find out if the subclass defines a datetime mapping. If the subclass defines a
        datetime mapping and returns a dictionary, the datetime mapping will be returned. Otherwise, an empty dict will
        be returned. This will be used by the to_json and extract_system_fields method to map fields containing datetime
        objects to string and back.
        """
        # find out if the subclass defines the method
        defining_class = self.get_custom_mapping.__func__.__qualname__.split(".")[0]
        if defining_class == "JsonDocument":
            return {}

        # check if the subclass method returns a dictionary
        attr_mapping = self.get_custom_mapping()
        if not isinstance(attr_mapping, dict):
            return {}

        # mapping provided by subclass, return it
        return attr_mapping

    def apply_updates(self, update, attributes: List[str] = []):
        """
        Applies an update (which has to be of the same type as self) to the current instance. The list of attributes
        past will be checked, if they are available.
        :param update: an instance of the same type as self
        :param attributes: a list of strings representing the attributes to update (see get_attribute_mapping)
        :raises ValueError: in case the provided `update` is an instance of a different class than self.
        """
        if not isinstance(update, type(self)):
            raise ValueError("Provided `update` parameter has a different type than `self`")
        if update is None:
            return
        for attr in attributes:
            if hasattr(self, attr) and hasattr(update, attr):
                self.__setattr__(attr, getattr(update, attr))
            else:
                warnings.warn(f"Trying to update attribute '{attr}' but either the item or the update does not have it")


def list_to_json(item_list: List[JsonDocument]):
    """
    Helper class serialising a list of JsonDocument into a list of dictionaries that can easily be serialised.
    :param item_list: a list of JsonDocument instances
    :return: a list of dictionaries.
    """
    return list(map(lambda item: item.to_json(), item_list))


def list_from_json(json_list: List[dict], deserialize_class: JsonDocument):
    """
    Helper class deserialising a list of dictionaries into a list of JsonDocument instances.
    :param json_list: a list of dictionaries
    :param deserialize_class: the class to use for deserialisation
    :return: a list of JsonDocument instances
    """
    if not issubclass(deserialize_class, JsonDocument):
        raise ValueError("Provided `deserialize_class` is not a subclass of JsonDocument")
    return list(map(lambda json: deserialize_class.from_json(json), json_list))
