import warnings
from abc import ABC, abstractmethod
from typing import Optional, List


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
        if attr_mapping is None:
            return

        # evaluate attribute mapping
        for key in attr_mapping:
            if attr_mapping[key] in json:
                self.__setattr__(key, json[attr_mapping[key]])

    def to_json(self) -> dict:
        """
        Returns a serializable representation of this document as dictionary or JSON object.
        :return: a dictionary or JSON object providing the data contained within this document
        """
        result = {}
        attr_mapping = self._get_attribute_mapping()
        if attr_mapping is not None:
            for key in attr_mapping:
                if self.__getattribute__(key) is not None:
                    result[attr_mapping[key]] = self.__getattribute__(key)

        return result

    @staticmethod
    @abstractmethod
    def from_json(json: dict):
        """
        Receives a dictionary or JSON object and returns an instance of this JsonDocument subclass.
        :param json: a dictionary or JSON object instance
        :return: an instance of a subclass of JsonDocument
        """
        pass

    def get_attribute_mapping(self) -> dict:
        """
        Provides a mapping from internal attribute names to JSON attribute names.
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
